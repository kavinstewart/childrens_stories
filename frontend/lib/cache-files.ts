// File system operations layer for offline story caching
// Uses expo-file-system (new API, SDK 54+) to manage downloaded stories and images

import { File, Directory, Paths } from 'expo-file-system';
import { fetch } from 'expo/fetch';
import { Story } from './api';
import { authStorage } from './auth-storage';

// Helper to get the stories cache directory
const getStoriesDir = (): Directory => new Directory(Paths.document, 'stories');

// Sanitize storyId to prevent path traversal attacks
const sanitizeStoryId = (storyId: string): string => {
  // Decode any URL-encoded characters first, then sanitize
  let decoded = storyId;
  try {
    decoded = decodeURIComponent(storyId);
  } catch {
    // If decoding fails, use original
  }
  // Remove path separators, parent directory references, and null bytes
  // Apply multiple passes to catch nested encodings like ....// -> ..
  let sanitized = decoded;
  let prev = '';
  while (sanitized !== prev) {
    prev = sanitized;
    sanitized = sanitized
      .replace(/\.\./g, '')
      .replace(/[/\\]/g, '')
      .replace(/\0/g, '');
  }
  return sanitized || 'invalid';
};

// Helper to get a story's directory
const getStoryDirectory = (storyId: string): Directory =>
  new Directory(getStoriesDir(), sanitizeStoryId(storyId));

// Helper to get the spread filename
const getSpreadFilename = (spreadNumber: number): string =>
  `spread_${spreadNumber.toString().padStart(2, '0')}.png`;

export const cacheFiles = {
  getStoryDir: (storyId: string): string => getStoryDirectory(storyId).uri,

  getSpreadPath: (storyId: string, spreadNumber: number): string => {
    const dir = getStoryDirectory(storyId);
    return new File(dir, getSpreadFilename(spreadNumber)).uri;
  },

  ensureDirectoryExists: async (storyId: string): Promise<void> => {
    const dir = getStoryDirectory(storyId);
    dir.create();
  },

  downloadSpreadImage: async (
    storyId: string,
    spreadNumber: number,
    sourceUrl: string
  ): Promise<{ success: boolean; size: number }> => {
    const dir = getStoryDirectory(storyId);
    const file = new File(dir, getSpreadFilename(spreadNumber));
    try {
      // Check directory exists before download
      if (!dir.exists) {
        return { success: false, size: 0 };
      }

      // Fetch with auth headers (new API uses fetch + write for header support)
      const token = await authStorage.getToken();
      const response = await fetch(sourceUrl, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!response.ok) {
        return { success: false, size: 0 };
      }

      // Write the response bytes to file
      const bytes = await response.bytes();
      file.write(bytes);

      // Validate minimum size (< 1KB is likely an error response)
      const fileSize = bytes.length;
      if (fileSize < 1000) {
        try { file.delete(); } catch { /* ignore */ }
        return { success: false, size: 0 };
      }

      return { success: true, size: fileSize };
    } catch {
      return { success: false, size: 0 };
    }
  },

  saveStoryMetadata: async (storyId: string, story: Story): Promise<void> => {
    const dir = getStoryDirectory(storyId);
    const file = new File(dir, 'metadata.json');
    // Save original story with server URLs - file:// paths are computed at render time
    file.write(JSON.stringify(story));
  },

  loadStoryMetadata: async (storyId: string): Promise<Story | null> => {
    const dir = getStoryDirectory(storyId);
    const file = new File(dir, 'metadata.json');
    try {
      const content = await file.text();
      const story: Story = JSON.parse(content);
      // Return original story with server URLs - file:// paths computed at render time
      return story;
    } catch {
      return null;
    }
  },

  deleteStoryDirectory: async (storyId: string): Promise<void> => {
    const dir = getStoryDirectory(storyId);
    try {
      dir.delete();
    } catch {
      // Idempotent: ignore if directory doesn't exist
    }
  },

  verifyStoryFiles: async (storyId: string): Promise<boolean> => {
    const dir = getStoryDirectory(storyId);
    if (!dir.exists) {
      return false;
    }

    const metaFile = new File(dir, 'metadata.json');
    if (!metaFile.exists) {
      return false;
    }

    // Load metadata to find which spreads should have images
    try {
      const content = await metaFile.text();
      const story: Story = JSON.parse(content);

      // Check that each spread WITH an illustration has a corresponding file
      for (const spread of story.spreads || []) {
        if (spread.illustration_url) {
          const spreadFile = new File(dir, getSpreadFilename(spread.spread_number));
          if (!spreadFile.exists) {
            return false;
          }
        }
      }
    } catch {
      return false;
    }

    return true;
  },
};
