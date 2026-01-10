/**
 * Voice module exports for STT and TTS functionality.
 */

export { useSTT } from './use-stt';
export type { UseSTTOptions, UseSTTResult, STTTranscript, STTStatus } from './use-stt';

export { useTTS } from './use-tts';
export type { UseTTSOptions, UseTTSResult, TTSStatus } from './use-tts';

export { useWordTTS } from './use-word-tts';
export type { UseWordTTSResult } from './use-word-tts';

export { WordTTSCache, buildCacheKey, normalizeWord } from './word-tts-cache';
export type { WordCacheKey, WordCacheEntry } from './word-tts-cache';

export {
  createWavFromPcm,
  uint8ArrayToBase64,
  base64ToUint8Array,
  extractAudioSlice,
} from './wav-utils';
