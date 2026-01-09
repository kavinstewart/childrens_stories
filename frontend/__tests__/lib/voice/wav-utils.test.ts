/**
 * Tests for WAV utilities
 */

import { createWavFromPcm, uint8ArrayToBase64, base64ToUint8Array } from '../../../lib/voice/wav-utils';

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
});
