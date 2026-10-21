import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createVoiceRecorder, recordingFilename, recordingTime } from '@/utils/voiceRecorder'
import { VOICE_RECORDER as config } from '@/config/voiceRecorder'

let recorders, track, stream, getUserMedia, callbacks, capture
class TestRecorder {
  static isTypeSupported(type) { return type.startsWith('audio/webm') }
  constructor(value, options) { this.state = 'inactive'; this.mimeType = options.mimeType; recorders.push(this) }
  start() { this.state = 'recording' }
  stop() {
    this.state = 'inactive'
    queueMicrotask(() => {
      this.ondataavailable?.({ data: new Blob(['final audio chunk'], { type: this.mimeType }) })
      this.onstop?.()
    })
  }
}
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'setTimeout', 'clearTimeout', 'performance'] })
  recorders = []
  track = { stop: vi.fn() }
  stream = { getTracks: () => [track], getAudioTracks: () => [track] }
  getUserMedia = vi.fn().mockResolvedValue(stream)
  vi.stubGlobal('isSecureContext', true)
  vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } })
  vi.stubGlobal('MediaRecorder', TestRecorder)
  callbacks = { onState: vi.fn(), onElapsed: vi.fn(), onComplete: vi.fn(), onError: vi.fn() }
  capture = createVoiceRecorder(callbacks)
})
afterEach(() => { capture.dispose(); vi.useRealTimers(); vi.unstubAllGlobals() })

describe('voice recording lifecycle', () => {
  it('keeps the final audio chunk and releases the microphone on stop', async () => {
    await capture.start()
    vi.advanceTimersByTime(1200)
    capture.stop()
    await Promise.resolve()
    expect(callbacks.onComplete).toHaveBeenCalledOnce()
    const clip = callbacks.onComplete.mock.calls[0][0]
    expect(clip.blob.size).toBeGreaterThan(0)
    expect(clip.blob.type).toBe('audio/webm;codecs=opus')
    expect(clip.durationMs).toBe(1200)
    expect(track.stop).toHaveBeenCalled()
    expect(callbacks.onState).toHaveBeenLastCalledWith('idle')
  })
  it('cancels an unresolved permission request and releases a late stream', async () => {
    let resolve
    getUserMedia.mockImplementation(() => new Promise(done => { resolve = done }))
    const starting = capture.start()
    capture.cancel()
    resolve(stream)
    await starting
    expect(track.stop).toHaveBeenCalledOnce()
    expect(recorders).toHaveLength(0)
    expect(callbacks.onComplete).not.toHaveBeenCalled()
  })
  it('disposes active capture without emitting a stale recording', async () => {
    await capture.start()
    capture.dispose()
    await Promise.resolve()
    expect(track.stop).toHaveBeenCalled()
    expect(callbacks.onComplete).not.toHaveBeenCalled()
  })
  it.each(['NotAllowedError', 'NotFoundError', 'NotReadableError'])('reports %s with a recovery path', async name => {
    getUserMedia.mockRejectedValue(new DOMException('capture failed', name))
    await capture.start()
    expect(callbacks.onError).toHaveBeenCalledWith(config.errors[name])
    expect(callbacks.onState).toHaveBeenLastCalledWith('idle')
  })
  it('stops automatically at the duration limit', async () => {
    await capture.start()
    await vi.advanceTimersByTimeAsync(config.maxDurationMs)
    expect(callbacks.onComplete).toHaveBeenCalledOnce()
    expect(track.stop).toHaveBeenCalled()
    expect(callbacks.onComplete.mock.calls[0][0].durationMs).toBe(config.maxDurationMs)
  })
  it('rejects clips too short to be useful', async () => {
    await capture.start()
    capture.stop()
    await Promise.resolve()
    expect(callbacks.onError).toHaveBeenCalledWith(config.errors.empty)
    expect(callbacks.onComplete).not.toHaveBeenCalled()
  })
  it('rejects oversized recordings and releases capture', async () => {
    await capture.start()
    recorders[0].ondataavailable({ data: new Blob([new Uint8Array(config.maxBytes + 1)]) })
    expect(callbacks.onError).toHaveBeenCalledWith(config.errors.tooLarge)
    expect(track.stop).toHaveBeenCalled()
    expect(callbacks.onComplete).not.toHaveBeenCalled()
  })
  it('recovers if a device never delivers the final stop event', async () => {
    await capture.start()
    recorders[0].stop = () => { recorders[0].state = 'inactive' }
    capture.stop()
    vi.advanceTimersByTime(config.stopTimeoutMs)
    expect(callbacks.onError).toHaveBeenCalledWith(config.errors.timeout)
    expect(track.stop).toHaveBeenCalled()
  })
  it('rejects insecure and unsupported browsers before requesting a microphone', async () => {
    vi.stubGlobal('isSecureContext', false)
    await capture.start()
    expect(callbacks.onError).toHaveBeenLastCalledWith(config.errors.insecure)
    vi.stubGlobal('isSecureContext', true)
    vi.stubGlobal('MediaRecorder', undefined)
    await capture.start()
    expect(callbacks.onError).toHaveBeenLastCalledWith(config.errors.unsupported)
    expect(getUserMedia).not.toHaveBeenCalled()
  })
  it('formats durations and uses the actual container in download filenames', () => {
    expect(recordingTime(61000)).toBe('01:01')
    expect(recordingTime(-1000)).toBe('00:00')
    expect(recordingFilename({ blob: new Blob([], {type:'audio/mp4'}), createdAt: 0 })).toMatch(/\.m4a$/)
  })
})
