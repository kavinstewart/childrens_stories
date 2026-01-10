/**
 * Tests for WAV utilities
 */

import {
  createWavFromPcm,
  uint8ArrayToBase64,
  base64ToUint8Array,
  extractAudioSlice,
} from '../../../lib/voice/wav-utils';

describe('wav-utils', () => {
  describe('createWavFromPcm', () => {
    it('creates WAV with correct header size (44 bytes)', () => {
      const pcmData = new Uint8Array([0, 0, 0, 0]); // 4 bytes of silence
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // WAV should be 44 bytes header + 4 bytes data = 48 bytes
      expect(wav.length).toBe(48);
    });

    it('starts with RIFF header', () => {
      const pcmData = new Uint8Array([0, 0]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // Check "RIFF" magic bytes
      const riff = String.fromCharCode(wav[0], wav[1], wav[2], wav[3]);
      expect(riff).toBe('RIFF');
    });

    it('contains WAVE format identifier', () => {
      const pcmData = new Uint8Array([0, 0]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // "WAVE" at offset 8
      const wave = String.fromCharCode(wav[8], wav[9], wav[10], wav[11]);
      expect(wave).toBe('WAVE');
    });

    it('contains fmt subchunk', () => {
      const pcmData = new Uint8Array([0, 0]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // "fmt " at offset 12
      const fmt = String.fromCharCode(wav[12], wav[13], wav[14], wav[15]);
      expect(fmt).toBe('fmt ');
    });

    it('contains data subchunk', () => {
      const pcmData = new Uint8Array([0, 0]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // "data" at offset 36
      const data = String.fromCharCode(wav[36], wav[37], wav[38], wav[39]);
      expect(data).toBe('data');
    });

    it('stores correct sample rate', () => {
      const pcmData = new Uint8Array([0, 0]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // Sample rate at offset 24 (little-endian)
      const view = new DataView(wav.buffer);
      const sampleRate = view.getUint32(24, true);
      expect(sampleRate).toBe(24000);
    });

    it('stores correct number of channels', () => {
      const pcmData = new Uint8Array([0, 0]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // Channels at offset 22 (little-endian)
      const view = new DataView(wav.buffer);
      const channels = view.getUint16(22, true);
      expect(channels).toBe(1);
    });

    it('stores correct bit depth', () => {
      const pcmData = new Uint8Array([0, 0]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // Bit depth at offset 34 (little-endian)
      const view = new DataView(wav.buffer);
      const bitDepth = view.getUint16(34, true);
      expect(bitDepth).toBe(16);
    });

    it('stores correct data size', () => {
      const pcmData = new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]); // 8 bytes
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // Data size at offset 40 (little-endian)
      const view = new DataView(wav.buffer);
      const dataSize = view.getUint32(40, true);
      expect(dataSize).toBe(8);
    });

    it('preserves original PCM data after header', () => {
      const pcmData = new Uint8Array([0x12, 0x34, 0x56, 0x78]);
      const wav = createWavFromPcm(pcmData, 24000, 16, 1);

      // PCM data starts at offset 44
      expect(wav[44]).toBe(0x12);
      expect(wav[45]).toBe(0x34);
      expect(wav[46]).toBe(0x56);
      expect(wav[47]).toBe(0x78);
    });

    it('works with stereo audio', () => {
      const pcmData = new Uint8Array([0, 0, 0, 0]); // 2 samples * 2 channels
      const wav = createWavFromPcm(pcmData, 44100, 16, 2);

      const view = new DataView(wav.buffer);
      expect(view.getUint16(22, true)).toBe(2); // 2 channels
      expect(view.getUint32(28, true)).toBe(44100 * 2 * 2); // byte rate
    });
  });

  describe('base64 encoding', () => {
    it('roundtrips correctly', () => {
      const original = new Uint8Array([1, 2, 3, 4, 5, 255, 0, 128]);
      const encoded = uint8ArrayToBase64(original);
      const decoded = base64ToUint8Array(encoded);

      expect(decoded).toEqual(original);
    });

    it('encodes to valid base64 string', () => {
      const data = new Uint8Array([72, 101, 108, 108, 111]); // "Hello"
      const encoded = uint8ArrayToBase64(data);

      expect(encoded).toBe('SGVsbG8=');
    });
  });

  describe('extractAudioSlice', () => {
    // Cartesia TTS format: 24kHz, 16-bit, mono
    const SAMPLE_RATE = 24000;
    const BIT_DEPTH = 16;
    const BYTES_PER_SAMPLE = BIT_DEPTH / 8; // 2 bytes

    // Create test PCM data with recognizable pattern
    function createTestPcmData(durationSeconds: number): Uint8Array {
      const numSamples = Math.floor(durationSeconds * SAMPLE_RATE);
      const numBytes = numSamples * BYTES_PER_SAMPLE;
      const data = new Uint8Array(numBytes);

      // Fill with pattern: each sample's bytes encode its index
      for (let i = 0; i < numSamples; i++) {
        const byteIndex = i * BYTES_PER_SAMPLE;
        data[byteIndex] = i % 256; // Low byte
        data[byteIndex + 1] = Math.floor(i / 256) % 256; // High byte
      }

      return data;
    }

    it('extracts a slice from the middle of audio', () => {
      const pcmData = createTestPcmData(2); // 2 seconds of audio
      const slice = extractAudioSlice(pcmData, 0.5, 1.0, SAMPLE_RATE, BIT_DEPTH);

      // 0.5 seconds of duration = 12000 samples = 24000 bytes
      expect(slice.length).toBe(24000);
    });

    it('extracts from the beginning of audio', () => {
      const pcmData = createTestPcmData(1); // 1 second
      const slice = extractAudioSlice(pcmData, 0, 0.25, SAMPLE_RATE, BIT_DEPTH);

      // 0.25 seconds = 6000 samples = 12000 bytes
      expect(slice.length).toBe(12000);

      // First byte should match original
      expect(slice[0]).toBe(pcmData[0]);
    });

    it('extracts to the end of audio', () => {
      const pcmData = createTestPcmData(1); // 1 second = 48000 bytes
      const slice = extractAudioSlice(pcmData, 0.75, 1.0, SAMPLE_RATE, BIT_DEPTH);

      // 0.25 seconds = 6000 samples = 12000 bytes
      expect(slice.length).toBe(12000);

      // Last bytes should match original
      expect(slice[slice.length - 1]).toBe(pcmData[pcmData.length - 1]);
    });

    it('handles very short slices (single word)', () => {
      const pcmData = createTestPcmData(1);
      // A typical short word might be 0.1 seconds
      const slice = extractAudioSlice(pcmData, 0.2, 0.3, SAMPLE_RATE, BIT_DEPTH);

      // 0.1 seconds = 2400 samples = 4800 bytes
      expect(slice.length).toBe(4800);
    });

    it('clamps end time to audio length', () => {
      const pcmData = createTestPcmData(0.5); // 0.5 seconds = 24000 bytes
      // Request beyond the audio length
      const slice = extractAudioSlice(pcmData, 0.3, 1.0, SAMPLE_RATE, BIT_DEPTH);

      // Should clamp to actual end: 0.3s to 0.5s = 0.2s = 4800 samples = 9600 bytes
      expect(slice.length).toBe(9600);
    });

    it('returns empty array if start >= end', () => {
      const pcmData = createTestPcmData(1);
      const slice = extractAudioSlice(pcmData, 0.5, 0.5, SAMPLE_RATE, BIT_DEPTH);
      expect(slice.length).toBe(0);
    });

    it('returns empty array if start is beyond audio length', () => {
      const pcmData = createTestPcmData(0.5);
      const slice = extractAudioSlice(pcmData, 1.0, 1.5, SAMPLE_RATE, BIT_DEPTH);
      expect(slice.length).toBe(0);
    });

    it('aligns to sample boundaries', () => {
      const pcmData = createTestPcmData(1);
      // Use a time that doesn't align perfectly to sample boundaries
      const slice = extractAudioSlice(pcmData, 0.0001, 0.1001, SAMPLE_RATE, BIT_DEPTH);

      // Should align to sample boundaries (multiple of 2 bytes for 16-bit)
      expect(slice.length % BYTES_PER_SAMPLE).toBe(0);
    });

    it('preserves audio data correctly', () => {
      const pcmData = createTestPcmData(1);
      const startTime = 0.1; // 2400 samples in
      const slice = extractAudioSlice(pcmData, startTime, 0.2, SAMPLE_RATE, BIT_DEPTH);

      // The first sample in the slice should match the original at the start offset
      const startByte = Math.floor(startTime * SAMPLE_RATE) * BYTES_PER_SAMPLE;
      expect(slice[0]).toBe(pcmData[startByte]);
      expect(slice[1]).toBe(pcmData[startByte + 1]);
    });
  });
});
