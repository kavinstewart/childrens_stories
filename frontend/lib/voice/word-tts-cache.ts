/**
 * Word-level TTS cache with context-aware keys.
 *
 * Caches individual word audio using keys that include prosodic context:
 * - word position (start/mid/end of sentence)
 * - punctuation following the word
 * - sentence type (statement/question/exclamation)
 *
 * This allows the same word to have different cached pronunciations
 * based on context, enabling natural-sounding cross-story sharing.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { File, Directory, Paths } from 'expo-file-system/next';

const CACHE_INDEX_KEY = 'word-tts-cache-index';
const CACHE_DIR_NAME = 'tts-words';
const CACHE_EXPIRY_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

/**
 * Context information used to build cache keys.
 */
export interface WordCacheKey {
  word: string;
  position: 'start' | 'mid' | 'end';
  punctuation: string;
  sentenceType: 'statement' | 'question' | 'exclamation';
  /** For homographs: which pronunciation variant (0 or 1) */
  pronunciationIndex?: number;
}

/**
 * Cached entry metadata stored in the index.
 */
export interface WordCacheEntry {
  cacheKey: string;
  audioPath: string;
  cachedAt: number;
  durationMs: number;
}

/**
 * Index structure stored in AsyncStorage.
 */
interface CacheIndex {
  entries: Record<string, WordCacheEntry>;
}

/**
 * Normalize a word for cache key generation.
 * - Converts to lowercase
 * - Strips punctuation from start/end
 * - Preserves contractions (apostrophes) and hyphens
 */
export function normalizeWord(word: string): string {
  return word
    .toLowerCase()
    .replace(/^[^a-z'-]+/, '')  // Strip leading non-word chars
    .replace(/[^a-z'-]+$/, ''); // Strip trailing non-word chars
}

/**
 * Build a cache key string from word context.
 * Format: "normalizedWord|position|punctuation|sentenceType" or
 *         "normalizedWord|position|punctuation|sentenceType|pN" for homographs
 */
export function buildCacheKey(key: WordCacheKey): string {
  const normalized = normalizeWord(key.word);
  let cacheKey = `${normalized}|${key.position}|${key.punctuation}|${key.sentenceType}`;
  if (key.pronunciationIndex !== undefined) {
    cacheKey += `|p${key.pronunciationIndex}`;
  }
  return cacheKey;
}

/**
 * Get the cache directory, creating it if needed.
 */
async function getCacheDirectory(): Promise<Directory> {
  const cacheDir = new Directory(Paths.cache, CACHE_DIR_NAME);
  if (!cacheDir.exists) {
    await cacheDir.create();
  }
  return cacheDir;
}

/**
 * Load the cache index from AsyncStorage.
 */
async function loadIndex(): Promise<CacheIndex> {
  try {
    const data = await AsyncStorage.getItem(CACHE_INDEX_KEY);
    if (data) {
      return JSON.parse(data);
    }
  } catch (error) {
    console.warn('[WordTTSCache] Failed to load index:', error);
  }
  return { entries: {} };
}

/**
 * Save the cache index to AsyncStorage.
 */
async function saveIndex(index: CacheIndex): Promise<void> {
  try {
    await AsyncStorage.setItem(CACHE_INDEX_KEY, JSON.stringify(index));
  } catch (error) {
    console.warn('[WordTTSCache] Failed to save index:', error);
  }
}

/**
 * Generate a filename for a cache entry.
 */
function generateFilename(cacheKey: string): string {
  // Replace pipe separators with underscores for filesystem-safe name
  const safeName = cacheKey.replace(/\|/g, '_').replace(/[^a-z0-9_-]/g, '');
  return `${safeName}.pcm`;
}

/**
 * Check if a cache entry has expired.
 */
function isExpired(entry: WordCacheEntry): boolean {
  return Date.now() - entry.cachedAt > CACHE_EXPIRY_MS;
}

/**
 * Word-level TTS cache for storing and retrieving word audio.
 */
export const WordTTSCache = {
  /**
   * Get a cached word entry if it exists and is not expired.
   */
  async get(key: WordCacheKey): Promise<WordCacheEntry | null> {
    const cacheKey = buildCacheKey(key);
    const index = await loadIndex();
    const entry = index.entries[cacheKey];

    if (!entry) {
      return null;
    }

    // Check expiration
    if (isExpired(entry)) {
      // Entry expired, remove it
      delete index.entries[cacheKey];
      await saveIndex(index);
      return null;
    }

    return entry;
  },

  /**
   * Get audio data for a cached word.
   */
  async getAudioData(entry: WordCacheEntry): Promise<Uint8Array | null> {
    try {
      const file = new File(entry.audioPath);
      if (!file.exists) {
        return null;
      }
      return await file.bytes();
    } catch (error) {
      console.warn('[WordTTSCache] Failed to read audio:', error);
      return null;
    }
  },

  /**
   * Store a word's audio in the cache.
   */
  async set(
    key: WordCacheKey,
    audioData: Uint8Array,
    durationMs: number
  ): Promise<WordCacheEntry> {
    const cacheKey = buildCacheKey(key);
    const index = await loadIndex();
    const cacheDir = await getCacheDirectory();

    // Generate file path
    const filename = generateFilename(cacheKey);
    const file = new File(cacheDir, filename);

    // Write audio data
    await file.write(audioData);

    // Create entry
    const entry: WordCacheEntry = {
      cacheKey,
      audioPath: file.uri,
      cachedAt: Date.now(),
      durationMs,
    };

    // Update index
    index.entries[cacheKey] = entry;
    await saveIndex(index);

    return entry;
  },

  /**
   * Clear all cached word audio.
   */
  async clearAll(): Promise<void> {
    try {
      // Remove the index
      await AsyncStorage.removeItem(CACHE_INDEX_KEY);

      // Remove the cache directory
      const cacheDir = new Directory(Paths.cache, CACHE_DIR_NAME);
      if (cacheDir.exists) {
        await cacheDir.delete();
      }
    } catch (error) {
      console.warn('[WordTTSCache] Failed to clear cache:', error);
    }
  },

  /**
   * Get cache statistics.
   */
  async getStats(): Promise<{ entryCount: number; totalSizeEstimate: number }> {
    const index = await loadIndex();
    const entryCount = Object.keys(index.entries).length;

    // Estimate size (we don't have actual file sizes in index)
    // Average word audio ~5KB for 300ms at 24kHz 16-bit
    const avgEntrySize = 5000;
    const totalSizeEstimate = entryCount * avgEntrySize;

    return { entryCount, totalSizeEstimate };
  },

  /**
   * Prune expired entries from the cache.
   */
  async pruneExpired(): Promise<number> {
    const index = await loadIndex();
    let prunedCount = 0;

    for (const [key, entry] of Object.entries(index.entries)) {
      if (isExpired(entry)) {
        // Try to delete the audio file
        try {
          const file = new File(entry.audioPath);
          if (file.exists) {
            await file.delete();
          }
        } catch {
          // Ignore file deletion errors
        }

        delete index.entries[key];
        prunedCount++;
      }
    }

    if (prunedCount > 0) {
      await saveIndex(index);
    }

    return prunedCount;
  },
};
