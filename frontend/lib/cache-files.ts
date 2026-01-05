// File system operations layer for offline story caching
// Uses expo-file-system to manage downloaded stories and images

import * as FileSystem from 'expo-file-system/legacy';
import { Story } from './api';
import { authStorage } from './auth-storage';

const CACHE_DIR = `${FileSystem.documentDirectory}stories/`;

export const cacheFiles = {
  getStoryDir: (storyId: string): string => `${CACHE_DIR}${storyId}/`,

  getSpreadPath: (storyId: string, spreadNumber: number): string => {
    const dir = cacheFiles.getStoryDir(storyId);
    return `${dir}spread_${spreadNumber.toString().padStart(2, '0')}.png`;
  },

  ensureDirectoryExists: async (storyId: string): Promise<void> => {
    const dir = cacheFiles.getStoryDir(storyId);
    await FileSystem.makeDirectoryAsync(dir, { intermediates: true });
  },

  downloadSpreadImage: async (
    storyId: string,
    spreadNumber: number,
    sourceUrl: string
  ): Promise<{ success: boolean; size: number }> => {
    const destPath = cacheFiles.getSpreadPath(storyId, spreadNumber);
    const dir = cacheFiles.getStoryDir(storyId);
    try {
      // Check directory exists before download
      const dirInfo = await FileSystem.getInfoAsync(dir);
      if (!dirInfo.exists) {
        return { success: false, size: 0 };
      }
      const token = await authStorage.getToken();
      const result = await FileSystem.downloadAsync(sourceUrl, destPath, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (result.status !== 200) {
        return { success: false, size: 0 };
      }
      const info = await FileSystem.getInfoAsync(destPath);
      // Validate minimum size (< 1KB is likely an error response)
      const fileSize = info.exists && 'size' in info ? info.size : 0;
      if (info.exists && fileSize < 1000) {
        await FileSystem.deleteAsync(destPath, { idempotent: true });
        return { success: false, size: 0 };
      }
      return { success: true, size: fileSize };
    } catch {
      return { success: false, size: 0 };
    }
  },

  saveStoryMetadata: async (storyId: string, story: Story): Promise<void> => {
    const dir = cacheFiles.getStoryDir(storyId);
    // Save original story with server URLs - file:// paths are computed at render time
    await FileSystem.writeAsStringAsync(
      `${dir}metadata.json`,
      JSON.stringify(story)
    );
  },

  loadStoryMetadata: async (storyId: string): Promise<Story | null> => {
    const path = `${cacheFiles.getStoryDir(storyId)}metadata.json`;
    try {
      const content = await FileSystem.readAsStringAsync(path);
      const story: Story = JSON.parse(content);
      // Return original story with server URLs - file:// paths computed at render time
      return story;
    } catch {
      return null;
    }
  },

  deleteStoryDirectory: async (storyId: string): Promise<void> => {
    const dir = cacheFiles.getStoryDir(storyId);
    await FileSystem.deleteAsync(dir, { idempotent: true });
  },

  verifyStoryFiles: async (storyId: string): Promise<boolean> => {
    const dir = cacheFiles.getStoryDir(storyId);
    const dirInfo = await FileSystem.getInfoAsync(dir);
    if (!dirInfo.exists) {
      return false;
    }

    const metaPath = `${dir}metadata.json`;
    const metaInfo = await FileSystem.getInfoAsync(metaPath);
    if (!metaInfo.exists) {
      return false;
    }

    // Load metadata to find which spreads should have images
    try {
      const content = await FileSystem.readAsStringAsync(metaPath);
      const story: Story = JSON.parse(content);

      // Check that each spread WITH an illustration has a corresponding file
      for (const spread of story.spreads || []) {
        if (spread.illustration_url) {
          const spreadPath = cacheFiles.getSpreadPath(storyId, spread.spread_number);
          const spreadInfo = await FileSystem.getInfoAsync(spreadPath);
          if (!spreadInfo.exists) {
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
