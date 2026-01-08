/**
 * Unit tests for network awareness utilities
 */
import NetInfo, { NetInfoState, NetInfoStateType } from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {
  shouldSync,
  shouldSyncWithSettings,
  getNetworkState,
  getSyncSettings,
  setSyncSettings,
  SyncSettings,
  DEFAULT_SYNC_SETTINGS,
} from '../../lib/network-aware';

// Mock NetInfo
jest.mock('@react-native-community/netinfo', () => ({
  fetch: jest.fn(),
}));

const mockNetInfo = NetInfo as jest.Mocked<typeof NetInfo>;

// Helper to create mock network state
const createNetworkState = (
  type: NetInfoStateType,
  isConnected: boolean
): NetInfoState => ({
  type,
  isConnected,
  isInternetReachable: isConnected,
  details: null,
});

describe('network-aware', () => {
  beforeEach(async () => {
    jest.clearAllMocks();
    await AsyncStorage.clear();
  });

  describe('getNetworkState', () => {
    it('returns current network state from NetInfo', async () => {
      const mockState = createNetworkState('wifi' as NetInfoStateType, true);
      mockNetInfo.fetch.mockResolvedValue(mockState);

      const state = await getNetworkState();

      expect(mockNetInfo.fetch).toHaveBeenCalled();
      expect(state).toEqual(mockState);
    });

    it('returns disconnected state when fetch fails', async () => {
      mockNetInfo.fetch.mockRejectedValue(new Error('Network error'));

      const state = await getNetworkState();

      expect(state.isConnected).toBe(false);
    });
  });

  describe('getSyncSettings / setSyncSettings', () => {
    it('returns default settings when none are stored', async () => {
      const settings = await getSyncSettings();
      expect(settings).toEqual(DEFAULT_SYNC_SETTINGS);
    });

    it('persists and retrieves settings', async () => {
      const newSettings: SyncSettings = {
        autoDownloadEnabled: false,
        allowCellular: true,
      };

      await setSyncSettings(newSettings);
      const retrieved = await getSyncSettings();

      expect(retrieved).toEqual(newSettings);
    });

    it('handles partial settings update', async () => {
      await setSyncSettings({ autoDownloadEnabled: false, allowCellular: false });
      await setSyncSettings({ autoDownloadEnabled: true, allowCellular: false });

      const settings = await getSyncSettings();
      expect(settings.autoDownloadEnabled).toBe(true);
      expect(settings.allowCellular).toBe(false);
    });

    it('throws when AsyncStorage fails to persist', async () => {
      // This tests proves callers need error handling for setSyncSettings
      // Save original implementation
      const originalSetItem = AsyncStorage.setItem;

      // Mock to throw once
      AsyncStorage.setItem = jest.fn().mockRejectedValueOnce(new Error('Storage full'));

      await expect(setSyncSettings({
        autoDownloadEnabled: true,
        allowCellular: true,
      })).rejects.toThrow('Storage full');

      // Restore original - important for test isolation
      AsyncStorage.setItem = originalSetItem;
    });
  });

  describe('shouldSync', () => {
    describe('when auto-download is disabled', () => {
      beforeEach(async () => {
        await setSyncSettings({ autoDownloadEnabled: false, allowCellular: false });
      });

      it('returns false even on WiFi', async () => {
        mockNetInfo.fetch.mockResolvedValue(
          createNetworkState('wifi' as NetInfoStateType, true)
        );

        const result = await shouldSync();
        expect(result).toBe(false);
      });
    });

    describe('when auto-download is enabled (default)', () => {
      beforeEach(async () => {
        await setSyncSettings({ autoDownloadEnabled: true, allowCellular: false });
      });

      it('returns true on WiFi', async () => {
        mockNetInfo.fetch.mockResolvedValue(
          createNetworkState('wifi' as NetInfoStateType, true)
        );

        const result = await shouldSync();
        expect(result).toBe(true);
      });

      it('returns false when disconnected', async () => {
        mockNetInfo.fetch.mockResolvedValue(
          createNetworkState('none' as NetInfoStateType, false)
        );

        const result = await shouldSync();
        expect(result).toBe(false);
      });

      it('returns false on cellular when allowCellular is false', async () => {
        mockNetInfo.fetch.mockResolvedValue(
          createNetworkState('cellular' as NetInfoStateType, true)
        );

        const result = await shouldSync();
        expect(result).toBe(false);
      });

      it('returns true on cellular when allowCellular is true', async () => {
        await setSyncSettings({ autoDownloadEnabled: true, allowCellular: true });
        mockNetInfo.fetch.mockResolvedValue(
          createNetworkState('cellular' as NetInfoStateType, true)
        );

        const result = await shouldSync();
        expect(result).toBe(true);
      });

      it('returns false on ethernet when not connected', async () => {
        mockNetInfo.fetch.mockResolvedValue(
          createNetworkState('ethernet' as NetInfoStateType, false)
        );

        const result = await shouldSync();
        expect(result).toBe(false);
      });

      it('returns true on ethernet when connected', async () => {
        mockNetInfo.fetch.mockResolvedValue(
          createNetworkState('ethernet' as NetInfoStateType, true)
        );

        const result = await shouldSync();
        expect(result).toBe(true);
      });
    });
  });

  describe('DEFAULT_SYNC_SETTINGS', () => {
    it('has auto-download enabled by default', () => {
      expect(DEFAULT_SYNC_SETTINGS.autoDownloadEnabled).toBe(true);
    });

    it('has cellular disabled by default', () => {
      expect(DEFAULT_SYNC_SETTINGS.allowCellular).toBe(false);
    });
  });

  describe('shouldSyncWithSettings', () => {
    it('uses provided settings instead of fetching from AsyncStorage', async () => {
      // Set up stored settings as disabled
      await setSyncSettings({ autoDownloadEnabled: false, allowCellular: false });

      // But pass enabled settings directly
      const cachedSettings: SyncSettings = { autoDownloadEnabled: true, allowCellular: false };
      mockNetInfo.fetch.mockResolvedValue(
        createNetworkState('wifi' as NetInfoStateType, true)
      );

      // shouldSync would return false (reads disabled settings from storage)
      const resultWithoutCache = await shouldSync();
      expect(resultWithoutCache).toBe(false);

      // shouldSyncWithSettings uses the provided settings (enabled)
      const resultWithCache = await shouldSyncWithSettings(cachedSettings);
      expect(resultWithCache).toBe(true);
    });

    it('respects allowCellular from cached settings', async () => {
      mockNetInfo.fetch.mockResolvedValue(
        createNetworkState('cellular' as NetInfoStateType, true)
      );

      // Cached settings with cellular allowed
      const withCellular = await shouldSyncWithSettings({
        autoDownloadEnabled: true,
        allowCellular: true,
      });
      expect(withCellular).toBe(true);

      // Cached settings without cellular
      const withoutCellular = await shouldSyncWithSettings({
        autoDownloadEnabled: true,
        allowCellular: false,
      });
      expect(withoutCellular).toBe(false);
    });
  });
});
