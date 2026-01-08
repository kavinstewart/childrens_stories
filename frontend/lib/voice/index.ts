/**
 * Voice module exports for STT and TTS functionality.
 */

export { useSTT } from './use-stt';
export type { UseSTTOptions, UseSTTResult, STTTranscript, STTStatus } from './use-stt';

export { useTTS } from './use-tts';
export type { UseTTSOptions, UseTTSResult, TTSStatus } from './use-tts';

export { useCachedTTS } from './use-cached-tts';
export type { UseCachedTTSOptions, UseCachedTTSResult } from './use-cached-tts';

export { useKaraoke } from './use-karaoke';
export type { UseKaraokeOptions, UseKaraokeResult, WordTimestamp } from './use-karaoke';

export { TTSCache } from './tts-cache';
export type { TTSCacheEntry } from './tts-cache';
