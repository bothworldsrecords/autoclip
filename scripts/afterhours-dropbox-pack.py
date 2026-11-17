#!/usr/bin/env python3
"""Afterhours -> AutoClip: choose and download a cohesive Dropbox footage pack.

Uses the EXISTING Dropbox scene index. Runs locally in Codespaces with Dropbox OAuth refresh credentials stored in
Codespaces secrets (never commit credentials).
Does not change AutoClip music analysis or edit planning.

Usage:
  DROPBOX_ACCESS_TOKEN=... python3 scripts/afterhours-dropbox-pack.py --dry-run
  DROPBOX_ACCESS_TOKEN=... python3 scripts/afterhours-dropbox-pack.py --download
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "public" / "afterhours" / "media"
MANIFEST = MEDIA.parent / "manifest.json"
# Dropbox-issued file IDs, not credentials; these resolve the existing index.
SCENE_INDEX_ID = "id:h1OBeQCaHWgAAAAAAAAAGA"
USED_FILE = MEDIA.parent / "dropbox-pack-history.json"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
# Strict FIRST benchmark: no generalized "nostalgia" fallback.
SKATE = re.compile(r"skateboard|skateboarding|skatelife|skaterboy|sk8|tony.?hawk|kader.?sylla|paul.?rodriguez|\bskate\b", re.I)
EXCLUDE = re.compile(r"basketball|nba|football|fifa|soccer|beach|surf|summer.?night|nightclub|fashion.?show|warehouse.sale|streetwear", re.I)
TEXT_RISK = re.compile(r"\bpov\b|lyrics|caption|text.?overlay", re.I)


def get_access_token() -> str:
    """Get a fresh temporary Dropbox token using the existing Colab refresh credentials."""
    refresh = os.environ.get("AFTERHOURS_DROPBOX_REFRESH_TOKEN", "").strip()
    app_key = os.environ.get("AFTERHOURS_DROPBOX_APP_KEY", "").strip()
    if refresh and app_key:
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": app_key,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.dropboxapi.com/oauth2/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                token = json.load(response)["access_token"]
            print("AUTH: Obtained fresh Dropbox access token.")
            return token
        except urllib.error.HTTPError as error:
            raise RuntimeError(
                f"Dropbox refresh token exchange failed (HTTP {error.code}). "
                "Verify Codespaces secrets match the original Dropbox app."
            ) from None
    if refresh or app_key:
        raise RuntimeError(
            "Set BOTH AFTERHOURS_DROPBOX_APP_KEY and AFTERHOURS_DROPBOX_REFRESH_TOKEN "
            "as Codespaces secrets, then restart the Codespace."
        )
    token = os.environ.get("DROPBOX_ACCESS_TOKEN", "").strip()
    if token:
        print("AUTH: Using temporary access token, which may expire.")
        return token
    raise RuntimeError(
        "Missing Dropbox credentials: add AFTERHOURS_DROPBOX_APP_KEY and "
        "AFTERHOURS_DROPBOX_REFRESH_TOKEN as Codespaces secrets."
    )


def dropbox_download(file_id: str, dest: Path, token: str) -> None:
    req = urllib.request.Request(
        "https://content.dropboxapi.com/2/files/download",
        headers={
            "Authorization": "Bearer " + token,
            "Dropbox-API-Arg": json.dumps({"path": file_id}, separators=(",", ":")),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response, dest.open("wb") as f:
            shutil.copyfileobj(response, f)
    except urllib.error.HTTPError as e:
        details = e.read(600).decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Dropbox download failed ({e.code}): {details}. "
            "Check your token's files.content.read permission and account."
        ) from None


def rank(file: dict) -> int:
    name = file["name"]
    if not SKATE.search(name) or EXCLUDE.search(name):
        return -1
    n = name.lower()
    score = 2
    score += 8 if any(w in n for w in ("skateboarding", "skateboard", "skatelife", "sk8")) else 0
    score += 5 if any(w in n for w in ("tonyhawk", "kadersylla", "paulrodriguez")) else 0
    score -= 4 if TEXT_RISK.search(name) else 0
    # Prefer enough footage for natural scene selection.
    score += 2 if 8 <= file.get("duration", 0) <= 40 else 0
    score += 1 if len(file.get("scenes", [])) > 1 else 0
    return score


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=8, help="Sources per edit (3-12)")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Show picks without downloading videos")
    mode.add_argument("--download", action="store_true", help="Download picks and update AutoClip manifest")
    args = ap.parse_args()
    if not 3 <= args.count <= 12:
        ap.error("--count must be between 3 and 12")
    try:
        token = get_access_token()
    except RuntimeError as error:
        sys.exit(str(error))
    MEDIA.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        local_index = Path(tmp) / "scene_index.json"
        dropbox_download(SCENE_INDEX_ID, local_index, token)
        index = json.loads(local_index.read_text(encoding="utf-8"))
        candidates = []
        for file_id, info in index["files"].items():
            file = dict(info)
            file["id"] = file_id
            file["score"] = rank(file)
            if file["score"] >= 0:
                candidates.append(file)

        used = []
        if USED_FILE.exists():
            used = json.loads(USED_FILE.read_text(encoding="utf-8")).get("source_ids", [])
        # Select previously unused sources first; no repeated source IDs in an edit.
        candidates.sort(key=lambda f: (f["id"] in used, -f["score"], f["name"].lower()))
        chosen = candidates[:args.count]
        print(f"INDEX: {len(index['files'])} source files; {len(candidates)} strict skate candidates.")
        for i, item in enumerate(chosen, 1):
            print(f"  {i:02d}. [score {item['score']}] {item['name'][:100]}")
        if len(chosen) < args.count:
            sys.exit(f"NOT ENOUGH: only {len(chosen)} suitable candidates; no unrelated content will be substituted.")
        if args.dry_run:
            print("DRY RUN: No video downloaded or existing AutoClip manifest changed.")
            return

        # Keep the exact selected song snippet from the existing package.
        if not MANIFEST.exists():
            sys.exit("MISSING: public/afterhours/manifest.json. Run the existing song manifest generator first.")
        current = json.loads(MANIFEST.read_text(encoding="utf-8"))
        song_path = current.get("song", {}).get("path", "")
        if not song_path.startswith("/afterhours/media/"):
            sys.exit("MISSING: a valid Afterhours song in existing manifest.")
        song_file = MEDIA / song_path.rsplit("/", 1)[-1]
        if not song_file.is_file() or song_file.suffix.lower() not in AUDIO_EXTENSIONS:
            sys.exit("MISSING: selected song file. Generate the song manifest first.")

        staged = []
        try:
            for i, item in enumerate(chosen, 1):
                ext = Path(item["name"]).suffix.lower()
                if ext not in VIDEO_EXTENSIONS:
                    raise RuntimeError(f"Unsupported video extension: {item['name']}")
                dest = MEDIA / f"dropbox-clip-{i:02d}{ext}"
                temporary = MEDIA / f".afterhours-stage-{i:02d}{ext}"
                print(f"Downloading {i}/{len(chosen)}: {item['name'][:65]}", flush=True)
                dropbox_download(item["id"], temporary, token)
                if temporary.stat().st_size == 0:
                    raise RuntimeError(f"Downloaded an empty file: {item['name']}")
                staged.append((temporary, dest))
        except Exception:
            for tmp_file, _ in staged:
                tmp_file.unlink(missing_ok=True)
            for tmp_file in MEDIA.glob(".afterhours-stage-*"):
                tmp_file.unlink(missing_ok=True)
            raise

        # All downloads succeeded. Replace only our previous generated Dropbox pack.
        for previous in MEDIA.glob("dropbox-clip-*"):
            previous.unlink()
        for source, dest in staged:
            source.replace(dest)
        next_manifest = {
            "song": current["song"],
            "clips": [{"path": f"/afterhours/media/{dest.name}"} for _, dest in staged],
        }
        MANIFEST.write_text(json.dumps(next_manifest, indent=2) + "\n", encoding="utf-8")
        history = {"source_ids": list(dict.fromkeys(used + [x["id"] for x in chosen]))}
        USED_FILE.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
        print(f"PASS: Downloaded {len(staged)} distinct Dropbox sources. Manifest points to song {song_file.name}.")
        print("Open the private AutoClip URL with ?afterhoursImport=1&afterhoursExport=1")


if __name__ == "__main__":
    main()
