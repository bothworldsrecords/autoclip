// Development-only import bridge for Afterhours-prepared local media.
// Preserves AutoClip's own decode, analysis and planning pipeline.
import { addFiles } from '../state/actions'
import { toast } from '../state/store'

interface MediaItem { path: string; name?: string }
interface PackageManifest { song: MediaItem; clips: MediaItem[] }

let started = false

function localMediaUrl(path: string): string {
  // Only import files the user deliberately placed in the Codespace's
  // ignored development media directory; never fetch arbitrary URLs.
  if (!/^\/afterhours\/media\/[a-zA-Z0-9_.\/-]+$/.test(path) || path.includes('..') || path.includes('//')) {
    throw new Error('Invalid media path. Use /afterhours/media/<filename>.')
  }
  const url = new URL(path, window.location.origin)
  if (url.origin !== window.location.origin) throw new Error('Media must be served locally.')
  return url.toString()
}

async function asFile(item: MediaItem): Promise<File> {
  const response = await fetch(localMediaUrl(item.path), { cache: 'no-store' })
  if (!response.ok) throw new Error(`Cannot load ${item.path}: HTTP ${response.status}`)
  const filename = item.name ?? item.path.split('/').pop()!
  return new File([await response.blob()], filename, {
    type: response.headers.get('content-type') ?? 'application/octet-stream',
  })
}

export async function importAfterhoursPackage(): Promise<void> {
  if (started || !import.meta.env.DEV) return
  started = true
  try {
    const response = await fetch('/afterhours/manifest.json', { cache: 'no-store' })
    if (!response.ok) throw new Error('No package found at /afterhours/manifest.json')
    const manifest = (await response.json()) as PackageManifest
    if (!manifest.song?.path || !Array.isArray(manifest.clips) || manifest.clips.length < 1 || manifest.clips.length > 40)
      throw new Error('Manifest requires one song and 1–40 clips.')
    const items = [manifest.song, ...manifest.clips]
    const files = await Promise.all(items.map(asFile))
    // Runs the original AutoClip import, beat-analysis, scene-analysis and auto-edit paths.
    await addFiles(files)
    toast(`Afterhours imported song and ${manifest.clips.length} clips; AutoClip is analyzing them.`, 'success')
  } catch (error) {
    started = false
    toast(`Afterhours import failed: ${error instanceof Error ? error.message : String(error)}`, 'error')
    throw error
  }
}
