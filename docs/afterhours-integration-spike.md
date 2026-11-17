# Afterhours + AutoClip integration spike

Status: **integration research; automated render not yet verified**.

## Goal
Keep the AutoClip v1.9.0 audio analysis, cut planning, transitions, and WebCodecs/Mediabunny encoder intact. Allow Afterhours to provide its own song and a curated group of source files, then export one MP4 without selecting individual files in the normal AutoClip UI. Only after a successful single-job test, expand to multiple jobs, Dropbox retrieval and usage-history tracking.

## Verified code seams on main
- `src/state/actions.ts`: `addFiles(files)` routes media; `setSongFile(file)` decodes/analyzes audio; `addClips(files)` queues visual analysis.
- `src/lib/edit/plan.ts`: `makePlan(song, clips, opts)` creates the AutoClip timeline.
- `src/lib/audio/analyze.ts`: `analyzeSong` analyzes beats/drops. **Do not replace**.
- `src/lib/render/export.ts`: `exportEdit(options)` returns the encoded MP4 as a Blob; browser APIs `OffscreenCanvas`, WebCodecs and WebGL are involved.
- `src/components/ExportDialog.tsx`: builds the soundtrack, loads analyzed clips, invokes `exportEdit`; its UI-only path is not currently a headless API.
- `src/lib/types.ts`: `FitMode = 'fill' | 'blur' | 'bars'`; Afterhours prefers `bars`.

## First engineering experiment
1. Run the forked web/Electron application in a supported Chromium environment.
2. Add a *development-only* batch-ingestion bridge accepting an authorized local song and a short list of video files. Do not expose a network endpoint that fetches arbitrary URLs.
3. Reuse AutoClip media analysis and edit generation without altering its algorithms.
4. Invoke its existing export path to produce one 9:16 MP4, with black bars rather than blurred filling.
5. Record explicit success/failure logs and preserve the output. Compare visually and audibly with a normal AutoClip edit using the same files.

## Go / no-go
- GO only after one end-to-end export completes without manual per-clip import and retains AutoClip's editing quality.
- NO-GO if automation requires substantial reimplementation of AutoClip's editing/rendering algorithms, breaks media codecs or cannot run reliably without GUI intervention.
- Do not connect all Dropbox footage or develop a 20-edit queue before the above proof succeeds.

## Security and privacy
- Keep Dropbox tokens out of the repository and browser bundles.
- Avoid exposing private signed Dropbox URLs in logs or commits.
- Do not automatically publish private source videos or user audio to public GitHub.
- Work on this branch; keep `main` clean until the experiment is proven.
