# Afterhours Dropbox-to-AutoClip pack builder

This is **implemented on the afterhours-integration-spike branch**, but not yet tested with a live Dropbox token in the user's Codespace.

The code reads the user's **existing** 916-file `afterhours_index/scene_index.json` through the Dropbox API; it does not re-index video. For this first benchmark it selects a strict skate set from filenames and scene metadata, avoids mixing unrelated cultural worlds, favors previously unused source files, downloads those video files, and rewrites the existing local `public/afterhours/manifest.json` to point to them while keeping the currently selected audio snippet.

**Limitation:** Filename-based skate discovery is a conservative first connectivity test, not a replacement for the semantic scene embeddings. The semantic_v2 NPZ files remain untouched. The next quality step after this works is semantic retrieval with visual screening.

## Set up access
Codespaces **cannot inherit ChatGPT's Dropbox connection**. A Dropbox OAuth access token with `files.content.read` permissions must be set in the Codespace's environment. Do not paste a token into chat, source files, screenshots or terminals that may be shared.

A Codespaces secret named `DROPBOX_ACCESS_TOKEN` is a suitable way to provide the token. Secrets are delivered to newly started Codespaces; restart the Codespace after creating one, and restart the development server. Short-lived Dropbox tokens eventually expire; longer-term automation requires proper OAuth refresh-token handling.

The existing Afterhours Dropbox app folder is the source. The index references Dropbox file IDs (not public links), so this script does not need to create public shared links.

## Run
```sh
git pull
python3 -m py_compile scripts/afterhours-dropbox-pack.py
python3 scripts/afterhours-dropbox-pack.py --count 8 --dry-run
python3 scripts/afterhours-dropbox-pack.py --count 8 --download
```

The first command verifies syntax, the dry run displays chosen source filenames and scores without downloading media, and the final command downloads sources into the Git-ignored `public/afterhours/media/` folder.

Existing short song selection is **preserved** from `public/afterhours/manifest.json`. It is never replaced by the full master. Previously uploaded originals are not touched.

Open the **private** AutoClip dev tab with:
```text
?afterhoursImport=1&afterhoursExport=1
```

AutoClip then uses the original editing engine, 9:16 black-bar framing, and automatic MP4 export.

## Guardrails / limits
- Downloads are from Dropbox by file ID, not filename or shared URL.
- Uses only clearly skate-related filenames to avoid unrelated shots for this first integration test.
- Each source file ID can appear at most once in the prepared pack; candidate history is kept in a Git-ignored local JSON file.
- **AutoClip itself can still repeat moments from a source within the finished edit.** The pack selector's uniqueness does not override AutoClip's shot planner. Judge the actual MP4.
- Live content quality, OAuth access, and Codespaces compatibility are not yet validated.
- `DROPBOX_ACCESS_TOKEN` is deliberately never written into the Git repository.
- Local media in the Codespaces Vite `public/` directory is web-accessible to people with access to the forwarded port. Keep that port private.

## Go/no-go
Only progress to larger packs or batch jobs after (1) Dropbox dry-run works, (2) source downloads work, (3) AutoClip produces a full edit, (4) the resulting imagery is cohesive. This integration spike does not solve semantic ranking or eliminate bad footage by itself.
