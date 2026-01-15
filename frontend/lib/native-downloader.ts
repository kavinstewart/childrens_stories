/**
 * NativeDownloader - Wrapper around react-native-background-downloader
 *
 * Provides a clean interface for downloading files on native iOS/Android threads,
 * completely separate from the JS thread. This prevents downloads from blocking
 * touch events and other UI interactions.
 *
 * Key features:
 * - Downloads run on native threads (not JS thread)
 * - Progress and completion callbacks
 * - Reattach to existing downloads after app restart
 * - Cancel downloads in progress
 */

import {
  createDownloadTask,
  getExistingDownloadTasks,
  completeHandler,
  directories,
  DownloadTask,
} from '@kesha-antonov/react-native-background-downloader';

export interface DownloadOptions {
  /** Unique identifier for this download */
  id: string;
  /** URL to download from */
  url: string;
  /** Local file path to save to */
  destination: string;
  /** Optional HTTP headers (e.g., Authorization) */
  headers?: Record<string, string>;
  /** Called periodically with download progress */
  onProgress?: (progress: DownloadProgress) => void;
  /** Called when download completes successfully */
  onComplete?: (result: DownloadComplete) => void;
  /** Called if download fails */
  onError?: (error: DownloadError) => void;
}

export interface DownloadProgress {
  id: string;
  bytesDownloaded: number;
  bytesTotal: number;
  percent: number;
}

export interface DownloadComplete {
  id: string;
  bytesDownloaded: number;
  bytesTotal: number;
}

export interface DownloadError {
  id: string;
  error: string;
  errorCode?: number;
}

export interface ReattachCallbacks {
  onProgress?: (progress: DownloadProgress) => void;
  onComplete?: (result: DownloadComplete) => void;
  onError?: (error: DownloadError) => void;
}

// Track active downloads
const activeDownloads = new Map<string, DownloadTask>();

export const NativeDownloader = {
  /**
   * Start downloading a file. The download runs on a native thread,
   * so it won't block the JS thread or touch events.
   */
  downloadFile(options: DownloadOptions): void {
    const { id, url, destination, headers, onProgress, onComplete, onError } = options;

    const task = createDownloadTask({
      id,
      url,
      destination,
      headers,
    });

    // Set up progress callback
    task.progress(({ bytesDownloaded, bytesTotal }) => {
      const percent = bytesTotal > 0 ? Math.round((bytesDownloaded / bytesTotal) * 100) : 0;
      onProgress?.({
        id,
        bytesDownloaded,
        bytesTotal,
        percent,
      });
    });

    // Set up completion callback
    task.done(({ bytesDownloaded, bytesTotal }) => {
      activeDownloads.delete(id);
      onComplete?.({
        id,
        bytesDownloaded,
        bytesTotal,
      });
      // Signal to native layer that we've handled the completion
      completeHandler(id);
    });

    // Set up error callback
    task.error(({ error, errorCode }) => {
      activeDownloads.delete(id);
      onError?.({
        id,
        error,
        errorCode,
      });
    });

    // Track and start the download
    activeDownloads.set(id, task);
    task.start();
  },

  /**
   * Cancel a download in progress.
   */
  cancelDownload(id: string): void {
    const task = activeDownloads.get(id);
    if (task) {
      task.stop();
      activeDownloads.delete(id);
    }
  },

  /**
   * Check if a download is currently in progress.
   */
  isDownloading(id: string): boolean {
    return activeDownloads.has(id);
  },

  /**
   * Get list of all active download IDs.
   */
  getActiveDownloadIds(): string[] {
    return Array.from(activeDownloads.keys());
  },

  /**
   * Reattach callbacks to downloads that were in progress when the app was terminated.
   * Call this on app startup to resume tracking existing downloads.
   *
   * @returns List of reattached download IDs
   */
  async reattachExistingDownloads(callbacks: ReattachCallbacks): Promise<string[]> {
    const { onProgress, onComplete, onError } = callbacks;
    const existingTasks = await getExistingDownloadTasks();
    const reattachedIds: string[] = [];

    for (const task of existingTasks) {
      const id = task.id;
      reattachedIds.push(id);
      activeDownloads.set(id, task);

      // Reattach progress callback
      task.progress(({ bytesDownloaded, bytesTotal }) => {
        const percent = bytesTotal > 0 ? Math.round((bytesDownloaded / bytesTotal) * 100) : 0;
        onProgress?.({
          id,
          bytesDownloaded,
          bytesTotal,
          percent,
        });
      });

      // Reattach completion callback
      task.done(({ bytesDownloaded, bytesTotal }) => {
        activeDownloads.delete(id);
        onComplete?.({
          id,
          bytesDownloaded,
          bytesTotal,
        });
        completeHandler(id);
      });

      // Reattach error callback
      task.error(({ error, errorCode }) => {
        activeDownloads.delete(id);
        onError?.({
          id,
          error,
          errorCode,
        });
      });
    }

    return reattachedIds;
  },

  /**
   * Get the documents directory path for storing downloaded files.
   */
  getDocumentsDirectory(): string {
    return directories.documents;
  },

  /**
   * Reset state (for testing).
   */
  reset(): void {
    activeDownloads.clear();
  },
};
