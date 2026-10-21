import { VOICE_RECORDER as config } from '@/config/voiceRecorder'

export function recordingTime(durationMs) {
  const seconds = Math.max(0, Math.floor(durationMs / 1000))
  return `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toString().padStart(2, '0')}`
}

export function recordingFilename(clip) {
  const mime = clip.blob.type.split(';')[0]
  const extension = { 'audio/mp4': 'm4a', 'audio/ogg': 'ogg', 'audio/webm': 'webm' }[mime] || 'audio'
  return `Flowly-voice-${new Date(clip.createdAt).toISOString().replace(/[:.]/g, '-')}.${extension}`
}

// Own the capture lifecycle so cancellation during a permission prompt cannot leak a microphone.
export function createVoiceRecorder({ onState, onElapsed, onComplete, onError }) {
  let generation = 0
  let disposed = false
  let status = 'idle'
  let stream = null
  let recorder = null
  let chunks = []
  let bytes = 0
  let startedAt = 0
  let durationMs = 0
  let timer = null
  let stopTimer = null

  function setState(next) { status = next; onState(next) }
  function stopTracks(value) { value?.getTracks().forEach(track => track.stop()) }
  function cleanup() {
    clearInterval(timer)
    clearTimeout(stopTimer)
    timer = stopTimer = null
    if (recorder) {
      recorder.ondataavailable = recorder.onstop = recorder.onerror = null
      if (recorder.state !== 'inactive') {
        try { recorder.stop() } catch { /* Tracks are still released below. */ }
      }
    }
    stopTracks(stream)
    recorder = stream = null
    chunks = []
    bytes = 0
  }
  function fail(message) {
    generation++
    cleanup()
    setState('idle')
    onError(message)
  }
  function stop() {
    if (status !== 'recording') return
    durationMs = performance.now() - startedAt
    onElapsed(durationMs)
    clearInterval(timer)
    setState('stopping')
    stopTimer = setTimeout(() => fail(config.errors.timeout), config.stopTimeoutMs)
    try {
      recorder.stop()
      stopTracks(stream)
    } catch { fail(config.errors.unknown) }
  }
  async function start() {
    if (disposed || status !== 'idle') return
    if (!window.isSecureContext) { onError(config.errors.insecure); return }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      onError(config.errors.unsupported)
      return
    }
    const request = ++generation
    setState('requesting')
    try {
      const captured = await navigator.mediaDevices.getUserMedia(config.constraints)
      if (disposed || request !== generation) { stopTracks(captured); return }
      stream = captured
      if (!stream.getAudioTracks().length) { fail(config.errors.NotFoundError); return }
      const mimeType = config.mimeTypes.find(type => MediaRecorder.isTypeSupported(type))
      recorder = new MediaRecorder(stream, { audioBitsPerSecond: config.audioBitsPerSecond, ...(mimeType ? { mimeType } : {}) })
      chunks = []
      bytes = 0
      recorder.ondataavailable = event => {
        if (event.data.size && request === generation) {
          chunks.push(event.data)
          bytes += event.data.size
          if (bytes > config.maxBytes) fail(config.errors.tooLarge)
        }
      }
      recorder.onerror = event => fail(config.errors[event.error?.name] || config.errors.unknown)
      recorder.onstop = () => {
        if (disposed || request !== generation) return
        if (status === 'recording') durationMs = performance.now() - startedAt
        const blob = new Blob(chunks, { type: recorder.mimeType || chunks[0]?.type })
        cleanup()
        setState('idle')
        if (!blob.size || durationMs < config.minDurationMs) { onError(config.errors.empty); return }
        onElapsed(durationMs)
        onComplete({ blob, durationMs, createdAt: Date.now(), downloaded: false })
      }
      startedAt = performance.now()
      durationMs = 0
      recorder.start(config.chunkIntervalMs)
      setState('recording')
      onElapsed(0)
      timer = setInterval(() => {
        durationMs = performance.now() - startedAt
        onElapsed(durationMs)
        if (durationMs >= config.maxDurationMs) stop()
      }, config.timerIntervalMs)
    } catch (error) {
      if (!disposed && request === generation) fail(config.errors[error.name] || config.errors.unknown)
    }
  }
  function cancel() {
    generation++
    cleanup()
    setState('idle')
  }
  function dispose() { disposed = true; cancel() }
  return { start, stop, cancel, dispose }
}
