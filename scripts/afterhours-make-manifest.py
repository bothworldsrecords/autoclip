#!/usr/bin/env python3
"""Prepare a local Afterhours import manifest from Codespaces uploaded media.

Only intended for the development import bridge. Does not commit media.
"""
from pathlib import Path
import json
import shutil

directory = Path(__file__).resolve().parents[1] / "public" / "afterhours" / "media"
if not directory.is_dir():
    raise SystemExit(f"ERROR: Upload your song and videos to {directory}")

audio_exts = {".mp3", ".wav", ".m4a", ".flac", ".aac"}
video_exts = {".mp4", ".mov", ".webm", ".m4v"}
files = sorted((p for p in directory.iterdir() if p.is_file()), key=lambda p: p.name)
audios = [p for p in files if p.suffix.lower() in audio_exts and not p.stem == "afterhours-song"]
videos = [p for p in files if p.suffix.lower() in video_exts and not p.stem.startswith("afterhours-clip-")]

if not audios:
    # Allow rerunning after originals have been deleted, though originals are not deleted by this script.
    audios = [p for p in files if p.stem == "afterhours-song" and p.suffix.lower() in audio_exts]
if not videos:
    videos = [p for p in files if p.stem.startswith("afterhours-clip-") and p.suffix.lower() in video_exts]
if not audios or not videos:
    raise SystemExit(
        f"ERROR: Found {len(audios)} song(s) and {len(videos)} videos. "
        "Add at least one audio file and one video in public/afterhours/media."
    )
if len(videos) > 40:
    raise SystemExit(f"ERROR: {len(videos)} videos found, but the development importer permits at most 40.")

def clean_copy(source: Path, stem: str) -> Path:
    target = directory / f"{stem}{source.suffix.lower()}"
    if source != target:
        shutil.copy2(source, target)
    return target

song = clean_copy(audios[0], "afterhours-song")
clips = [clean_copy(video, f"afterhours-clip-{i:02d}") for i, video in enumerate(videos, 1)]
manifest = {
    "song": {"path": f"/afterhours/media/{song.name}"},
    "clips": [{"path": f"/afterhours/media/{clip.name}"} for clip in clips],
}
destination = directory.parent / "manifest.json"
destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"PASS: Created {destination.relative_to(directory.parents[2])} for one song and {len(clips)} videos.")
print("NEXT: Open the private AutoClip dev URL with ?afterhoursImport=1")
