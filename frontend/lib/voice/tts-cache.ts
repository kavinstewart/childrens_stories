/**
 * TTS Cache - Caches generated audio and timestamps per spread.
 *
 * Stores audio data keyed by text hash to avoid regenerating TTS
 * for the same text content.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { File, Directory, Paths } from 'expo-file-system';
import { WordTimestamp } from './use-karaoke';

// Cache directory for TTS audio files
const getTTSCacheDir = (): Directory => new Directory(Paths.cache, 'tts');

const TTS_INDEX_KEY = '@tts_cache_index';

// 7 days cache expiry
const CACHE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000;

// Max cache entries to prevent unbounded growth
const MAX_CACHE_ENTRIES = 100;

export interface TTSCacheEntry {
  textHash: string;
  audioPath: string;
  timestamps: WordTimestamp[];
  cachedAt: number;
  durationMs: number;
}

interface TTSCacheIndex {
  entries: Record<string, TTSCacheEntry>;
}

/**
 * Hash function for text content.
 * Includes text length and first/last chars to reduce collision risk.
 */
function hashText(text: string): string {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    const char = text.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32-bit integer
  }
  // Include length and boundary chars to reduce collisions
  const len = text.length;
  const prefix = text.slice(0, 8);
  const suffix = text.slice(-8);
  return `${Math.abs(hash).toString(36)}_${len}_${prefix.replace(/\W/g, '')}_${suffix.replace(/\W/g, '')}`;
}

/**
 * Decode a base64 string to Uint8Array.
 */
function base64ToUint8Array(base64: string): Uint8Array {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

/**
 * Encode Uint8Array to base64 string.
 */
function uint8ArrayToBase64(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

/**
 * Concatenate multiple Uint8Arrays into one.
 */
function concatUint8Arrays(arrays: Uint8Array[]): Uint8Array {
  const totalLength = arrays.reduce((sum, arr) => sum + arr.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const arr of arrays) {
    result.set(arr, offset);
    offset += arr.length;
  }
  return result;
}

/**
 * TTS Cache Manager - handles caching of TTS audio and timestamps.
 */
export const TTSCache = {
  /**
   * Initialize the cache directory and clean up expired/excess entries.
   */
  async init(): Promise<void> {
    const dir = getTTSCacheDir();
    if (!dir.exists) {
      dir.create();
    }
    // Clean up expired entries on init
    await this.clearExpired();
    // Enforce max entries limit
    await this.enforceMaxEntries();
  },

  /**
   * Get cached TTS data for text, if available and not expired.
   */
  async get(text: string): Promise<TTSCacheEntry | null> {
    const textHash = hashText(text);
    const index = await this.loadIndex();

    const entry = index.entries[textHash];
    if (!entry) {
      return null;
    }

    // Check expiry
    if (Date.now() - entry.cachedAt > CACHE_EXPIRY_MS) {
      await this.remove(textHash);
      return null;
    }

    // Verify audio file exists
    const file = new File(entry.audioPath);
    if (!file.exists) {
      await this.remove(textHash);
      return null;
    }

    return entry;
  },

  /**
   * Cache TTS audio and timestamps for text.
   * @param text - The text that was synthesized
   * @param audioChunks - Array of base64-encoded audio chunks from TTS
   * @param timestamps - Word timing data
   * @param durationMs - Total audio duration in milliseconds
   */
  async set(
    text: string,
    audioChunks: string[],
    timestamps: WordTimestamp[],
    durationMs: number
  ): Promise<TTSCacheEntry> {
    await this.init();

    const textHash = hashText(text);
    const dir = getTTSCacheDir();
    const audioFile = new File(dir, `${textHash}.pcm`);

    // Decode each base64 chunk to binary and concatenate
    const binaryChunks = audioChunks.map(base64ToUint8Array);
    const combinedBinary = concatUint8Arrays(binaryChunks);

    console.log('[TTSCache] Storing audio:', {
      numChunks: audioChunks.length,
      totalBytes: combinedBinary.length,
      first20Bytes: Array.from(combinedBinary.slice(0, 20)),
    });

    // Write binary audio data directly to file
    audioFile.write(combinedBinary);

    const entry: TTSCacheEntry = {
      textHash,
      audioPath: audioFile.uri,
      timestamps,
      cachedAt: Date.now(),
      durationMs,
    };

    // Update index
    const index = await this.loadIndex();
    index.entries[textHash] = entry;
    await this.saveIndex(index);

    return entry;
  },

  /**
   * Remove a cache entry.
   */
  async remove(textHash: string): Promise<void> {
    const index = await this.loadIndex();
    const entry = index.entries[textHash];

    if (entry) {
      // Delete audio file
      try {
        const file = new File(entry.audioPath);
        if (file.exists) {
          file.delete();
        }
      } catch {
        // Ignore file deletion errors
      }

      // Remove from index
      delete index.entries[textHash];
      await this.saveIndex(index);
    }
  },

  /**
   * Read cached audio data as base64.
   * Reads binary PCM data from file and encodes to base64 for playback.
   */
  async readAudio(entry: TTSCacheEntry): Promise<string> {
    const file = new File(entry.audioPath);
    const binaryData = await file.bytes();
    console.log('[TTSCache] Reading audio:', {
      path: entry.audioPath,
      bytesRead: binaryData.length,
      first20Bytes: Array.from(binaryData.slice(0, 20)),
    });
    return uint8ArrayToBase64(binaryData);
  },

  /**
   * Clear all cached TTS data.
   */
  async clearAll(): Promise<void> {
    try {
      const dir = getTTSCacheDir();
      if (dir.exists) {
        dir.delete();
      }
      await AsyncStorage.removeItem(TTS_INDEX_KEY);
    } catch {
      // Ignore errors
    }
  },

  /**
   * Clear expired entries.
   */
  async clearExpired(): Promise<number> {
    const index = await this.loadIndex();
    const now = Date.now();
    let cleared = 0;

    for (const [hash, entry] of Object.entries(index.entries)) {
      if (now - entry.cachedAt > CACHE_EXPIRY_MS) {
        await this.remove(hash);
        cleared++;
      }
    }

    return cleared;
  },

  /**
   * Enforce max entries limit by removing oldest entries.
   */
  async enforceMaxEntries(): Promise<number> {
    const index = await this.loadIndex();
    const entries = Object.entries(index.entries);

    if (entries.length <= MAX_CACHE_ENTRIES) {
      return 0;
    }

    // Sort by cachedAt (oldest first)
    entries.sort((a, b) => a[1].cachedAt - b[1].cachedAt);

    // Remove oldest entries until we're under the limit
    const toRemove = entries.length - MAX_CACHE_ENTRIES;
    for (let i = 0; i < toRemove; i++) {
      await this.remove(entries[i][0]);
    }

    return toRemove;
  },

  /**
   * Get cache statistics.
   */
  async getStats(): Promise<{ count: number; totalSizeBytes: number }> {
    const index = await this.loadIndex();
    let totalSize = 0;

    for (const entry of Object.values(index.entries)) {
      try {
        const file = new File(entry.audioPath);
        if (file.exists && file.size) {
          totalSize += file.size;
        }
      } catch {
        // Skip if file check fails
      }
    }

    return {
      count: Object.keys(index.entries).length,
      totalSizeBytes: totalSize,
    };
  },

  // Private helpers
  async loadIndex(): Promise<TTSCacheIndex> {
    try {
      const json = await AsyncStorage.getItem(TTS_INDEX_KEY);
      if (json) {
        return JSON.parse(json);
      }
    } catch {
      // Return empty index on error
    }
    return { entries: {} };
  },

  async saveIndex(index: TTSCacheIndex): Promise<void> {
    await AsyncStorage.setItem(TTS_INDEX_KEY, JSON.stringify(index));
  },
};
