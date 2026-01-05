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
    try {
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
    const transformed = cacheFiles.transformStoryUrls(storyId, story);
    await FileSystem.writeAsStringAsync(
      `${dir}metadata.json`,
      JSON.stringify(transformed)
    );
  },

  loadStoryMetadata: async (storyId: string): Promise<Story | null> => {
    const path = `${cacheFiles.getStoryDir(storyId)}metadata.json`;
    try {
      const content = await FileSystem.readAsStringAsync(path);
      return JSON.parse(content);
    } catch {
      return null;
    }
  },

  transformStoryUrls: (storyId: string, story: Story): Story => {
    return {
      ...story,
      spreads: story.spreads?.map(spread => ({
        ...spread,
        illustration_url: cacheFiles.getSpreadPath(storyId, spread.spread_number),
      })),
    };
  },

  deleteStoryDirectory: async (storyId: string): Promise<void> => {
    const dir = cacheFiles.getStoryDir(storyId);
    await FileSystem.deleteAsync(dir, { idempotent: true });
  },

  verifyStoryFiles: async (storyId: string, expectedSpreadCount: number): Promise<boolean> => {
    const dir = cacheFiles.getStoryDir(storyId);
    const dirInfo = await FileSystem.getInfoAsync(dir);
    if (!dirInfo.exists) return false;

    const metaInfo = await FileSystem.getInfoAsync(`${dir}metadata.json`);
    if (!metaInfo.exists) return false;

    for (let i = 1; i <= expectedSpreadCount; i++) {
      const spreadPath = cacheFiles.getSpreadPath(storyId, i);
      const spreadInfo = await FileSystem.getInfoAsync(spreadPath);
      if (!spreadInfo.exists) return false;
    }

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
