/**
 * WAV utilities for wrapping raw PCM data with WAV headers.
 *
 * Used for cached TTS playback via playWav() which requires WAV format.
 */

/**
 * Create a WAV file from raw PCM audio data.
 *
 * @param pcmData - Raw PCM audio samples
 * @param sampleRate - Sample rate in Hz (e.g., 24000)
 * @param bitDepth - Bits per sample (e.g., 16)
 * @param numChannels - Number of audio channels (e.g., 1 for mono)
 * @returns WAV file data including 44-byte header + PCM data
 */
export function createWavFromPcm(
  pcmData: Uint8Array,
  sampleRate: number,
  bitDepth: number,
  numChannels: number
): Uint8Array {
  const byteRate = sampleRate * numChannels * (bitDepth / 8);
  const blockAlign = numChannels * (bitDepth / 8);
  const dataSize = pcmData.length;
  const headerSize = 44;
  const fileSize = headerSize + dataSize;

  const buffer = new ArrayBuffer(fileSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, fileSize - 8, true); // File size minus RIFF header
  writeString(view, 8, 'WAVE');

  // fmt subchunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true); // Subchunk1 size (16 for PCM)
  view.setUint16(20, 1, true); // Audio format (1 = PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitDepth, true);

  // data subchunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataSize, true);

  // Copy PCM data after header
  const wavData = new Uint8Array(buffer);
  wavData.set(pcmData, headerSize);

  return wavData;
}

/**
 * Helper to write a string to a DataView at a specific offset.
 */
function writeString(view: DataView, offset: number, str: string): void {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

/**
 * Encode Uint8Array to base64 string.
 */
export function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Decode base64 string to Uint8Array.
 */
export function base64ToUint8Array(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

/**
 * Extract a slice of audio from PCM data based on time offsets.
 *
 * This is used to extract individual word audio from full sentence synthesis.
 * The timestamps from TTS provide word boundaries in seconds.
 *
 * @param pcmData - Raw PCM audio data
 * @param startTimeSec - Start time in seconds
 * @param endTimeSec - End time in seconds
 * @param sampleRate - Sample rate in Hz (e.g., 24000 for Cartesia)
 * @param bitDepth - Bits per sample (e.g., 16)
 * @returns Extracted PCM audio slice
 */
export function extractAudioSlice(
  pcmData: Uint8Array,
  startTimeSec: number,
  endTimeSec: number,
  sampleRate: number,
  bitDepth: number
): Uint8Array {
  const bytesPerSample = bitDepth / 8;

  // Convert time to sample index, then to byte offset
  const startSample = Math.floor(startTimeSec * sampleRate);
  const endSample = Math.floor(endTimeSec * sampleRate);

  // Calculate byte offsets (aligned to sample boundaries)
  const startByte = startSample * bytesPerSample;
  const maxBytes = pcmData.length;

  // Clamp end to actual data length
  const endByte = Math.min(endSample * bytesPerSample, maxBytes);

  // Handle edge cases
  if (startByte >= maxBytes || startByte >= endByte) {
    return new Uint8Array(0);
  }

  // Extract the slice
  return pcmData.slice(startByte, endByte);
}
