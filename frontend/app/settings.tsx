import { useState, useEffect, useCallback } from 'react';
import { View, Text, Alert, ActivityIndicator, Switch, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { StoryCacheManager } from '@/lib/story-cache';
import { fontFamily } from '@/lib/fonts';
import { getSyncSettings, setSyncSettings, SyncSettings, DEFAULT_SYNC_SETTINGS } from '@/lib/network-aware';
import { WordTTSCache } from '@/lib/voice';

// Format bytes to human readable
const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export default function Settings() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [cacheSize, setCacheSize] = useState<number | null>(null);
  const [storyCount, setStoryCount] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isClearing, setIsClearing] = useState(false);
  const [syncSettings, setSyncSettingsState] = useState<SyncSettings>(DEFAULT_SYNC_SETTINGS);

  const loadCacheInfo = useCallback(async () => {
    setIsLoading(true);
    try {
      const [size, ids, settings] = await Promise.all([
        StoryCacheManager.getCacheSize(),
        StoryCacheManager.getCachedStoryIds(),
        getSyncSettings(),
      ]);
      setCacheSize(size);
      setStoryCount(ids.length);
      setSyncSettingsState(settings);
    } catch (error) {
      console.error('Failed to load cache info:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleAutoDownloadToggle = async (value: boolean) => {
    const previousSettings = syncSettings;
    const newSettings = { ...syncSettings, autoDownloadEnabled: value };
    setSyncSettingsState(newSettings);
    try {
      await setSyncSettings(newSettings);
    } catch (error) {
      console.error('Failed to save auto-download setting:', error);
      setSyncSettingsState(previousSettings);
      Alert.alert('Error', 'Failed to save setting. Please try again.');
    }
  };

  const handleCellularToggle = async (value: boolean) => {
    const previousSettings = syncSettings;
    const newSettings = { ...syncSettings, allowCellular: value };
    setSyncSettingsState(newSettings);
    try {
      await setSyncSettings(newSettings);
    } catch (error) {
      console.error('Failed to save cellular setting:', error);
      setSyncSettingsState(previousSettings);
      Alert.alert('Error', 'Failed to save setting. Please try again.');
    }
  };

  useEffect(() => {
    loadCacheInfo();
  }, [loadCacheInfo]);

  const handleClearCache = () => {
    Alert.alert(
      'Clear Cache',
      'Are you sure you want to clear all cached stories? This will remove all offline data.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            setIsClearing(true);
            try {
              // Clear story cache and word TTS cache in parallel
              await Promise.all([
                StoryCacheManager.clearAllCache(),
                WordTTSCache.clearAll(),
              ]);
              await loadCacheInfo();
            } catch (error) {
              console.error('Failed to clear cache:', error);
              Alert.alert('Error', 'Failed to clear cache. Please try again.');
            } finally {
              setIsClearing(false);
            }
          },
        },
      ]
    );
  };

  return (
    <View style={{ flex: 1, backgroundColor: '#1a1a2e', paddingTop: insets.top, paddingLeft: insets.left, paddingRight: insets.right }}>
      {/* Header */}
      <View style={{
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 24,
        paddingVertical: 16,
      }}>
        {/* Back Button */}
        <Pressable
          onPress={() => router.back()}
          style={{
            backgroundColor: '#FAF7F2',
            paddingVertical: 12,
            paddingHorizontal: 18,
            borderRadius: 18,
            borderWidth: 2,
            borderColor: '#EDE8E0',
            shadowColor: '#000',
            shadowOffset: { width: 0, height: 2 },
            shadowOpacity: 0.15,
            shadowRadius: 6,
            elevation: 4,
          }}
        >
          <Text style={{ fontSize: 24 }}>{'<-'}</Text>
        </Pressable>

        {/* Title */}
        <Text style={{
          fontSize: 28,
          color: 'white',
          fontFamily: fontFamily.nunitoBold,
          marginLeft: 20,
        }}>
          Settings
        </Text>
      </View>

      {/* Content */}
      <View style={{ flex: 1, paddingHorizontal: 24, paddingTop: 32 }}>
        {/* Cache Section */}
        <View style={{
          backgroundColor: 'rgba(255, 255, 255, 0.1)',
          borderRadius: 20,
          padding: 24,
        }}>
          <Text style={{
            fontSize: 20,
            color: 'white',
            fontFamily: fontFamily.nunitoBold,
            marginBottom: 20,
          }}>
            Offline Cache
          </Text>

          {isLoading ? (
            <View style={{ alignItems: 'center', paddingVertical: 20 }}>
              <ActivityIndicator size="large" color="#FBBF24" />
            </View>
          ) : (
            <>
              {/* Sync Settings */}
              <View style={{ marginBottom: 24 }}>
                {/* Auto-download toggle */}
                <View style={{
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 16,
                }}>
                  <View style={{ flex: 1, marginRight: 16 }}>
                    <Text style={{
                      fontSize: 16,
                      color: 'white',
                      fontFamily: fontFamily.nunitoSemiBold,
                    }}>
                      Auto-download stories
                    </Text>
                    <Text style={{
                      fontSize: 13,
                      color: 'rgba(255, 255, 255, 0.5)',
                      fontFamily: fontFamily.nunito,
                      marginTop: 2,
                    }}>
                      Automatically save stories for offline reading
                    </Text>
                  </View>
                  <Switch
                    value={syncSettings.autoDownloadEnabled}
                    onValueChange={handleAutoDownloadToggle}
                    trackColor={{ false: '#444', true: '#22C55E' }}
                    thumbColor="white"
                  />
                </View>

                {/* Cellular toggle */}
                <View style={{
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  opacity: syncSettings.autoDownloadEnabled ? 1 : 0.5,
                }}>
                  <View style={{ flex: 1, marginRight: 16 }}>
                    <Text style={{
                      fontSize: 16,
                      color: 'white',
                      fontFamily: fontFamily.nunitoSemiBold,
                    }}>
                      Use cellular data
                    </Text>
                    <Text style={{
                      fontSize: 13,
                      color: 'rgba(255, 255, 255, 0.5)',
                      fontFamily: fontFamily.nunito,
                      marginTop: 2,
                    }}>
                      Download only on WiFi when off
                    </Text>
                  </View>
                  <Switch
                    value={syncSettings.allowCellular}
                    onValueChange={handleCellularToggle}
                    disabled={!syncSettings.autoDownloadEnabled}
                    trackColor={{ false: '#444', true: '#22C55E' }}
                    thumbColor="white"
                  />
                </View>
              </View>

              {/* Divider */}
              <View style={{
                height: 1,
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                marginBottom: 24,
              }} />

              {/* Cache Stats */}
              <View style={{ marginBottom: 24 }}>
                <View style={{
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                  marginBottom: 12,
                }}>
                  <Text style={{
                    fontSize: 16,
                    color: 'rgba(255, 255, 255, 0.7)',
                    fontFamily: fontFamily.nunito,
                  }}>
                    Cached Stories
                  </Text>
                  <Text style={{
                    fontSize: 16,
                    color: 'white',
                    fontFamily: fontFamily.nunitoSemiBold,
                  }}>
                    {storyCount ?? 0}
                  </Text>
                </View>

                <View style={{
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                }}>
                  <Text style={{
                    fontSize: 16,
                    color: 'rgba(255, 255, 255, 0.7)',
                    fontFamily: fontFamily.nunito,
                  }}>
                    Total Size
                  </Text>
                  <Text style={{
                    fontSize: 16,
                    color: 'white',
                    fontFamily: fontFamily.nunitoSemiBold,
                  }}>
                    {formatSize(cacheSize ?? 0)}
                  </Text>
                </View>
              </View>

              {/* Clear Cache Button */}
              <Pressable
                onPress={handleClearCache}
                disabled={isClearing || storyCount === 0}
                style={({ pressed }) => ({
                  backgroundColor: storyCount === 0 ? '#666' : '#DC2626',
                  paddingVertical: 16,
                  paddingHorizontal: 24,
                  borderRadius: 16,
                  alignItems: 'center',
                  opacity: pressed ? 0.8 : 1,
                })}
              >
                {isClearing ? (
                  <ActivityIndicator size="small" color="white" />
                ) : (
                  <Text style={{
                    fontSize: 16,
                    color: 'white',
                    fontFamily: fontFamily.nunitoBold,
                  }}>
                    Clear Cache
                  </Text>
                )}
              </Pressable>

              {storyCount === 0 && (
                <Text style={{
                  fontSize: 14,
                  color: 'rgba(255, 255, 255, 0.5)',
                  fontFamily: fontFamily.nunito,
                  textAlign: 'center',
                  marginTop: 12,
                }}>
                  No cached stories to clear
                </Text>
              )}
            </>
          )}
        </View>
      </View>
    </View>
  );
}
