// Development-only automatic export spike. Reuses the normal AutoClip renderer.
// This is a browser-run export, not a server-side API or unattended cloud job.
import { DEFAULT_MIX, renderMix } from '../lib/audio/mix'
import { decodeAudioFile } from '../lib/audio/decode'
import { exportEdit } from '../lib/render/export'
import { captionOptionsFor, lookFor, renderPlan, voiceoverAt } from '../state/derive'
import { castFramed } from '../state/people'
import { getState, subscribe } from '../state/store'

let installed = false

function statusPanel() {
  const panel = document.createElement('div')
  panel.style.cssText =
    'position:fixed;right:14px;bottom:14px;z-index:99999;max-width:330px;padding:16px;' +
    'background:#151515;color:white;border:1px solid #55cc8e;border-radius:10px;' +
    'font:14px/1.4 system-ui,sans-serif;box-shadow:0 5px 24px #0008;'
  const title = document.createElement('div')
  title.textContent = 'Afterhours automatic export'
  title.style.cssText = 'font-weight:700;margin-bottom:7px;'
  const status = document.createElement('div')
  status.textContent = 'Waiting for AutoClip to finish analyzing media...'
  const button = document.createElement('button')
  button.textContent = 'Download finished MP4'
  button.disabled = true
  button.style.cssText = 'display:none;margin-top:10px;padding:9px 12px;border-radius:6px;background:#55cc8e;color:#111;font-weight:700;cursor:pointer'
  panel.append(title, status, button)
  document.body.append(panel)
  return { status, button }
}

export function armAfterhoursAutoExport(): void {
  if (!import.meta.env.DEV || installed) return
  installed = true
  const ui = statusPanel()
  let started = false
  let unsubscribe = () => {}
  let objectUrl: string | null = null

  async function run() {
    const state = getState()
    const draft = state.drafts.find((d) => d.id === state.activeDraftId)
    if (!draft || !state.song?.buffer) throw new Error('No ready AutoClip draft or soundtrack.')
    const plan = renderPlan(draft, state)
    const look = lookFor(draft.style, state.settings)
    // The browser renderer is the original AutoClip implementation.
    // Keep the requested black-bar framing even if a saved style says "fill".
    look.fit = 'bars'
    const captions = captionOptionsFor(draft.style, state.settings)
    const used = new Set(plan.shots.map((s) => s.clipId))
    const clipBuffers = new Map<string, AudioBuffer>()
    if (state.settings.clipAudio !== 'off') {
      for (const clip of state.clips.filter((c) => used.has(c.id) && c.kind === 'video')) {
        const decoded = await decodeAudioFile(clip.file).catch(() => null)
        if (decoded) clipBuffers.set(clip.id, decoded)
      }
    }
    const voice = state.settings.voiceover
    const voiceovers = voice.enabled && state.voice
      ? [{ buffer: state.voice.buffer, at: voiceoverAt(plan, voice.placement, state.voice.buffer.duration) }]
      : []
    ui.status.textContent = 'Mixing original AutoClip soundtrack...'
    const audio = await renderMix(state.song.buffer, plan, {
      ...DEFAULT_MIX,
      musicVolume: state.settings.musicVolume,
      sfx: state.settings.sfx,
      sfxVolume: state.settings.sfxVolume,
      clipAudio: state.settings.clipAudio,
      clipBuffers,
      voiceovers,
    })
    const clips = state.clips.filter((c) => c.analysis).map((c) => ({
      id: c.id,
      kind: c.kind,
      file: c.file,
      analysis: castFramed({ id: c.id, analysis: c.analysis! }),
      offset: c.offset,
    }))
    const file = await exportEdit({
      plan,
      clips,
      look,
      captions,
      width: 720,
      height: 1280,
      fps: 30,
      bitrate: 6,
      audioBitrate: 192,
      audio,
      onProgress: (fraction, stage) => {
        ui.status.textContent = `Rendering: ${stage} — ${Math.round(fraction * 100)}%`
      },
    })
    if (!file.size) throw new Error('AutoClip produced an empty video.')
    objectUrl = URL.createObjectURL(file)
    const name = 'afterhours-autoclip-test.mp4'
    const save = () => {
      const anchor = document.createElement('a')
      anchor.href = objectUrl!
      anchor.download = name
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
    }
    ui.button.onclick = save
    ui.button.disabled = false
    ui.button.style.display = 'block'
    ui.status.textContent = `MP4 rendered: ${(file.size / 1e6).toFixed(1)} MB. Saving to browser downloads...`
    // Some browsers block automatic downloads without a user gesture.
    // The persistent button always provides an explicit, reliable fallback.
    save()
  }

  const check = () => {
    if (started) return
    const state = getState()
    if (state.song?.status === 'error' || state.clips.some((c) => c.status === 'error')) {
      ui.status.textContent = 'Media analysis failed. Check AutoClip for details.'
      unsubscribe()
      return
    }
    const ready = state.song?.status === 'ready' && state.clips.length > 0 &&
      state.clips.every((c) => c.status === 'ready') && state.drafts.length > 0 &&
      state.drafts.some((d) => d.id === state.activeDraftId)
    if (!ready) return
    started = true
    unsubscribe()
    void run().catch((error: unknown) => {
      ui.status.textContent = `Export failed: ${error instanceof Error ? error.message : String(error)}`
      console.error('[Afterhours] Automatic export failed:', error)
    })
  }
  unsubscribe = subscribe(check)
  check()
  // Retain the object URL until the page is closed, so the download button stays usable.
  window.addEventListener('pagehide', () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }, { once: true })
}
