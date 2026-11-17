# Afterhours package import — development proof of concept

The first integration step **does not alter AutoClip's editing algorithms**. It reuses `addFiles` from `src/state/actions.ts`, so AutoClip still analyzes the full song, analyzes the videos and creates its regular edit.

## Usage in Codespaces (development only)

1. Keep the Codespaces forwarded port **Private**. All imported media is served by the development web server and must not be exposed through a public port.
2. In your Codespace, put the song and a small curated set of video files inside `public/afterhours/media/`. This folder is ignored by Git and **must never be committed**.
3. Create `public/afterhours/manifest.json` with local paths. Example:

```json
{
  "song": { "path": "/afterhours/media/song.mp3" },
  "clips": [
    { "path": "/afterhours/media/skate-01.mp4" },
    { "path": "/afterhours/media/skate-02.mp4" }
  ]
}
```

4. With `pnpm dev --host 0.0.0.0` running, open the app in a new tab and add `?afterhoursImport=1` to its URL.
5. AutoClip will import the files automatically, analyze them and generate an edit using its existing application logic.

This is intentionally **a limited integration spike**. It does not download from Dropbox, automate MP4 export or batch multiple edits. It is not a network API. The eventual Afterhours package builder will place curated files here (or provide them through an authenticated local service).

## Guardrails

- Import only runs in Vite's development mode, when explicitly enabled by the query parameter.
- The manifest can reference **only** same-origin paths under `/afterhours/media/`.
- Never place tokens, signed Dropbox URLs, credentials or secrets in the manifest or repository.
- The package directory is Git-ignored but remains accessible to anyone who can visit the development server's URL while it is running. Keep the forwarded port private.
- Imported media is consumed by AutoClip's original analysis and planning code.
- Export automation is not implemented or verified.

## Immediate acceptance test

Using a short audio file and two local clips, verify:
- The files appear in AutoClip without selecting them individually.
- AutoClip analyzes the song and footage and generates a take.
- A manual MP4 export works as usual.

Only after those checks pass should we automate the export action.
