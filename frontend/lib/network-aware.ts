/**
 * Network awareness utilities for automatic cache sync
 *
 * Provides WiFi detection, network state monitoring, and user preference
 * management for controlling when automatic story downloads should occur.
 */

import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';

const SYNC_SETTINGS_KEY = 'sync_settings';

export interface SyncSettings {
  /** Whether automatic story downloads are enabled */
  autoDownloadEnabled: boolean;
  /** Whether to allow downloads on cellular data */
  allowCellular: boolean;
}

export const DEFAULT_SYNC_SETTINGS: SyncSettings = {
  autoDownloadEnabled: true,
  allowCellular: false,
};

/**
 * Get current network state from NetInfo.
 * Returns a disconnected state if fetch fails.
 */
export async function getNetworkState(): Promise<NetInfoState> {
  try {
    return await NetInfo.fetch();
  } catch {
    // Return a disconnected state on error
    return {
      type: 'unknown',
      isConnected: false,
      isInternetReachable: false,
      details: null,
    } as NetInfoState;
  }
}

/**
 * Get user's sync settings from storage.
 * Returns defaults if none are stored.
 */
export async function getSyncSettings(): Promise<SyncSettings> {
  try {
    const stored = await AsyncStorage.getItem(SYNC_SETTINGS_KEY);
    if (stored) {
      return JSON.parse(stored) as SyncSettings;
    }
  } catch {
    // Ignore parse errors, return defaults
  }
  return DEFAULT_SYNC_SETTINGS;
}

/**
 * Save user's sync settings to storage.
 */
export async function setSyncSettings(settings: SyncSettings): Promise<void> {
  await AsyncStorage.setItem(SYNC_SETTINGS_KEY, JSON.stringify(settings));
}

/**
 * Determine if automatic sync should proceed based on network state and user settings.
 *
 * Returns true if:
 * - Auto-download is enabled AND
 * - Device is connected AND
 * - Either on WiFi/ethernet OR cellular is allowed
 */
export async function shouldSync(): Promise<boolean> {
  const settings = await getSyncSettings();

  // Check if auto-download is enabled
  if (!settings.autoDownloadEnabled) {
    return false;
  }

  const state = await getNetworkState();

  // Must be connected
  if (!state.isConnected) {
    return false;
  }

  // WiFi and ethernet are always allowed
  if (state.type === 'wifi' || state.type === 'ethernet') {
    return true;
  }

  // Cellular requires explicit permission
  if (state.type === 'cellular') {
    return settings.allowCellular;
  }

  // Unknown network types - don't sync
  return false;
}

/**
 * Subscribe to network state changes.
 * Returns an unsubscribe function.
 */
export function subscribeToNetworkChanges(
  callback: (state: NetInfoState) => void
): () => void {
  return NetInfo.addEventListener(callback);
}
