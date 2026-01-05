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
    console.log(`[Cache] ensureDirectoryExists: creating ${dir}`);
    try {
      await FileSystem.makeDirectoryAsync(dir, { intermediates: true });
      const info = await FileSystem.getInfoAsync(dir);
      console.log(`[Cache] ensureDirectoryExists: created ${dir}, exists=${info.exists}, isDirectory=${info.isDirectory}`);
    } catch (error) {
      console.error(`[Cache] ensureDirectoryExists: failed to create ${dir}:`, error);
      throw error;
    }
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
      console.log(`[Cache] Downloading spread ${spreadNumber}: dir=${dir}, dirExists=${dirInfo.exists}, destPath=${destPath}`);
      if (!dirInfo.exists) {
        console.error(`[Cache] Directory does not exist for spread ${spreadNumber}: ${dir}`);
        return { success: false, size: 0 };
      }
      console.log(`[Cache] Downloading spread ${spreadNumber} from: ${sourceUrl}`);
      const token = await authStorage.getToken();
      const result = await FileSystem.downloadAsync(sourceUrl, destPath, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (result.status !== 200) {
        console.error(`[Cache] Download failed for spread ${spreadNumber}: HTTP ${result.status}`);
        return { success: false, size: 0 };
      }
      const info = await FileSystem.getInfoAsync(destPath);
      // Validate minimum size (< 1KB is likely an error response)
      const fileSize = info.exists && 'size' in info ? info.size : 0;
      if (info.exists && fileSize < 1000) {
        console.error(`[Cache] Download too small for spread ${spreadNumber}: ${fileSize} bytes (likely error response)`);
        await FileSystem.deleteAsync(destPath, { idempotent: true });
        return { success: false, size: 0 };
      }
      console.log(`[Cache] Downloaded spread ${spreadNumber}: ${fileSize} bytes`);
      return { success: true, size: fileSize };
    } catch (error) {
      console.error(`[Cache] Exception downloading spread ${spreadNumber}:`, error);
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

      // Transform spread illustration_url to file:// paths for offline display
      if (story.spreads) {
        story.spreads = story.spreads.map(spread => ({
          ...spread,
          illustration_url: spread.illustration_url
            ? cacheFiles.getSpreadPath(storyId, spread.spread_number)
            : spread.illustration_url,
        }));
      }

      return story;
    } catch {
      return null;
    }
  },

  deleteStoryDirectory: async (storyId: string): Promise<void> => {
    const dir = cacheFiles.getStoryDir(storyId);
    await FileSystem.deleteAsync(dir, { idempotent: true });
  },

  verifyStoryFiles: async (storyId: string, _expectedSpreadCount: number): Promise<boolean> => {
    const dir = cacheFiles.getStoryDir(storyId);
    const dirInfo = await FileSystem.getInfoAsync(dir);
    if (!dirInfo.exists) {
      console.log(`[Cache] Verification failed: directory missing for story ${storyId}`);
      return false;
    }

    const metaPath = `${dir}metadata.json`;
    const metaInfo = await FileSystem.getInfoAsync(metaPath);
    if (!metaInfo.exists) {
      console.log(`[Cache] Verification failed: metadata.json missing for story ${storyId}`);
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
            console.log(`[Cache] Verification failed: missing spread ${spread.spread_number} for story ${storyId}`);
            return false;
          }
        }
      }
    } catch (error) {
      console.error(`[Cache] Verification failed: could not read metadata for story ${storyId}`, error);
      return false;
    }

    console.log(`[Cache] Verification passed for story ${storyId}`);
    return true;
  },

  getDirectorySize: async (storyId: string): Promise<number> => {
    const dir = cacheFiles.getStoryDir(storyId);
    const dirInfo = await FileSystem.getInfoAsync(dir);
    if (!dirInfo.exists) return 0;

    const files = await FileSystem.readDirectoryAsync(dir);
    let total = 0;
    for (const file of files) {
      const info = await FileSystem.getInfoAsync(`${dir}${file}`);
      if (info.exists && !info.isDirectory && 'size' in info) {
        total += info.size || 0;
      }
    }
    return total;
  },
};
