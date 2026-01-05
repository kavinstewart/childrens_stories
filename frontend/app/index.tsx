import { View, Text, Pressable, ScrollView, ActivityIndicator, useWindowDimensions, RefreshControl, TouchableOpacity } from 'react-native';
import { Pressable as GHPressable } from 'react-native-gesture-handler';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useState, useEffect } from 'react';
import { useStories } from '@/features/stories/hooks';
import { Story } from '@/lib/api';
import { StoryCard } from '@/components/StoryCard';
import { StoryCacheManager } from '@/lib/story-cache';

// Debug logging
const DEBUG = true;
const log = (...args: unknown[]) => DEBUG && console.log('[StoryLibrary]', ...args);

// Grid configuration
const GRID_PADDING = 24; // matches contentContainerStyle padding
const GRID_GAP = 16;     // gap between cards
const COLUMNS = 4;       // number of columns

export default function StoryLibrary() {
  const router = useRouter();

  // Log mount
  useEffect(() => {
    log('Component mounted');
    return () => log('Component unmounted');
  }, []);
  const { data: networkStories, isLoading, isFetching, error, refetch } = useStories();
  const { width: screenWidth } = useWindowDimensions();
  const [cachedStories, setCachedStories] = useState<Story[]>([]);
  const [isLoadingCache, setIsLoadingCache] = useState(true); // Start true - always load cache on mount

  // Always load cached stories on mount (for offline support, stories marked isCached=true)
  useEffect(() => {
    log('Loading cached stories...');
    StoryCacheManager.loadAllCachedStories()
      .then((stories) => {
        log('Cached stories loaded:', stories.length);
        setCachedStories(stories);
      })
      .catch((err) => {
        log('ERROR loading cached stories:', err);
      })
      .finally(() => setIsLoadingCache(false));
  }, []);

  // Log data state changes
  useEffect(() => {
    log('Data state:', {
      networkStories: networkStories?.length ?? 'undefined',
      cachedStories: cachedStories.length,
      isLoading,
      isLoadingCache,
      error: error ? String(error) : null,
    });
  }, [networkStories, cachedStories, isLoading, isLoadingCache, error]);

  // Determine if we're in offline mode
  const isOffline = !!error && !isLoading;

  // Merge stories: use network list but overlay cached versions (which have file:// URLs)
  // When offline, use only cached stories
  const stories = (() => {
    if (isOffline) {
      return cachedStories.length > 0 ? cachedStories : undefined;
    }
    if (!networkStories) return undefined;

    // Overlay cached stories onto network stories (cached have isCached=true for render-time file:// computation)
    return networkStories.map(networkStory => {
      const cachedVersion = cachedStories.find(s => s.id === networkStory.id);
      if (cachedVersion) {
        // Use cached version - it has isCached=true for offline image display
        return cachedVersion;
      }
      return networkStory;
    });
  })();

  // Calculate card dimensions (matching HTML mockup)
  // Available width = screen - left padding - right padding
  // Card width = (available - gaps between cards) / number of columns
  const availableWidth = screenWidth - (GRID_PADDING * 2);
  const totalGapWidth = GRID_GAP * (COLUMNS - 1);
  const cardWidth = (availableWidth - totalGapWidth) / COLUMNS;
  const cardHeight = cardWidth * 1.1; // Shorter aspect ratio (~1:1.1)

  return (
    <LinearGradient
      colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']}
      style={{ flex: 1 }}
    >
      {/* DEBUG: Button completely outside ScrollView */}
      <GHPressable
        onPress={() => {
          log('OUTSIDE SCROLLVIEW pressed!');
          // Also try an alert to be really sure
          alert('Button pressed!');
        }}
        style={{ backgroundColor: 'orange', padding: 20, margin: 10, borderRadius: 12 }}
      >
        <Text style={{ color: 'white', fontWeight: 'bold', fontSize: 18, textAlign: 'center' }}>
          OUTSIDE SCROLLVIEW - TAP ME
        </Text>
      </GHPressable>

      <SafeAreaView className="flex-1" edges={['top', 'left', 'right']}>
        <ScrollView
          className="flex-1"
          contentContainerStyle={{ padding: 24, flexGrow: 1 }}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="always"
          refreshControl={
            <RefreshControl
              refreshing={isFetching && !isLoading}
              onRefresh={refetch}
              tintColor="#7C3AED"
              colors={['#7C3AED']}
            />
          }
        >
          {/* Header */}
          <View className="flex-row items-center justify-between mb-6">
            <View>
              <Text className="text-4xl font-bold text-purple-800">
                My Story Library
              </Text>
              <Text className="text-lg text-gray-600">
                {stories?.length ?? 0} magical adventures
              </Text>
            </View>

            {/* Header Buttons */}
            <View className="flex-row items-center gap-3">
              {/* Settings Button */}
              <Pressable
                onPressIn={() => log('Settings onPressIn')}
                onPressOut={() => log('Settings onPressOut')}
                onPress={() => {
                  log('Settings button pressed');
                  router.push('/settings');
                }}
                className="bg-gray-200 py-4 px-4 rounded-2xl"
                style={({ pressed }) => ({
                  opacity: pressed ? 0.8 : 1,
                  transform: [{ scale: pressed ? 0.95 : 1 }],
                })}
              >
                <Text className="text-2xl">{'⚙️'}</Text>
              </Pressable>

              {/* New Story Button */}
              <Pressable
                onPress={() => {
                  log('New Story button pressed');
                  router.push('/new');
                }}
                className="bg-purple-600 py-4 px-6 rounded-2xl"
                style={({ pressed }) => ({
                  opacity: pressed ? 0.8 : 1,
                  transform: [{ scale: pressed ? 0.95 : 1 }],
                })}
              >
                <Text className="text-lg font-bold text-white">
                  + New Story
                </Text>
              </Pressable>

              {/* DEBUG: TouchableOpacity test */}
              <TouchableOpacity
                onPress={() => log('TouchableOpacity pressed!')}
                style={{ backgroundColor: 'red', padding: 16, borderRadius: 12 }}
              >
                <Text style={{ color: 'white', fontWeight: 'bold' }}>TAP TEST</Text>
              </TouchableOpacity>

              {/* DEBUG: Raw View touch test */}
              <View
                onTouchStart={() => log('RAW onTouchStart!')}
                onTouchEnd={() => log('RAW onTouchEnd!')}
                style={{ backgroundColor: 'blue', padding: 16, borderRadius: 12 }}
              >
                <Text style={{ color: 'white', fontWeight: 'bold' }}>RAW TOUCH</Text>
              </View>

              {/* DEBUG: Gesture Handler Pressable test */}
              <GHPressable
                onPress={() => log('GH Pressable pressed!')}
                style={{ backgroundColor: 'green', padding: 16, borderRadius: 12 }}
              >
                <Text style={{ color: 'white', fontWeight: 'bold' }}>GH PRESS</Text>
              </GHPressable>
            </View>
          </View>

          {/* Offline Mode Banner */}
          {isOffline && (
            <View className="bg-amber-100 rounded-2xl px-4 py-3 mb-4 flex-row items-center">
              <Text className="text-lg mr-2">📴</Text>
              <Text className="text-amber-800 font-semibold flex-1">
                Offline Mode - Showing {stories?.length} cached {stories?.length === 1 ? 'story' : 'stories'}
              </Text>
              <Pressable onPress={() => refetch()} className="bg-amber-200 px-3 py-1 rounded-lg">
                <Text className="text-amber-800 font-semibold">Retry</Text>
              </Pressable>
            </View>
          )}

          {/* Loading State - only show if we have no stories to display yet */}
          {(isLoadingCache || (isLoading && cachedStories.length === 0)) && !stories && (
            <View className="items-center justify-center py-20">
              <ActivityIndicator size="large" color="#7C3AED" />
              <Text className="text-gray-600 mt-4">
                Loading stories...
              </Text>
            </View>
          )}

          {/* Error State - only show if no cached stories available */}
          {error && !isOffline && !isLoadingCache && (
            <View className="items-center justify-center py-20 bg-red-50 rounded-3xl">
              <Text className="text-4xl mb-4">😕</Text>
              <Text className="text-red-800 font-bold text-xl mb-2">
                Couldn't load stories
              </Text>
              <Text className="text-red-600 mb-4">
                No cached stories available for offline reading
              </Text>
              <Pressable
                onPress={() => refetch()}
                className="bg-red-600 px-6 py-3 rounded-xl"
              >
                <Text className="text-white font-bold">Try Again</Text>
              </Pressable>
            </View>
          )}

          {/* Empty State */}
          {!isLoading && !error && stories?.length === 0 && (
            <View className="items-center justify-center py-20">
              <Text className="text-6xl mb-4">📚</Text>
              <Text className="text-gray-800 font-bold text-xl mb-2">
                No stories yet!
              </Text>
              <Text className="text-gray-600 mb-6">
                Create your first magical adventure
              </Text>
              <Pressable
                onPress={() => router.push('/new')}
                className="bg-purple-600 px-8 py-4 rounded-2xl"
              >
                <Text className="text-white font-bold text-lg">
                  Create a Story
                </Text>
              </Pressable>
            </View>
          )}

          {/* Story Cards Grid */}
          {stories && stories.length > 0 && (
            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
              {log('Rendering', stories.length, 'stories')}
              {stories.map((story, index) => {
                // Margin logic: right margin for all except last in row
                const columnIndex = index % COLUMNS;
                const hasRightMargin = columnIndex < COLUMNS - 1;

                return (
                  <View
                    key={story.id}
                    style={{
                      marginRight: hasRightMargin ? GRID_GAP : 0,
                      marginBottom: GRID_GAP,
                    }}
                  >
                    <StoryCard
                      story={story}
                      width={cardWidth}
                      height={cardHeight}
                      colorIndex={index}
                      showStatusBadge={true}
                      onPress={() => {
                        log('StoryCard pressed:', story.id, story.status);
                        if (story.status === 'completed') {
                          router.push(`/read/${story.id}`);
                        } else if (story.status === 'pending' || story.status === 'running') {
                          router.push(`/creating/${story.id}`);
                        }
                      }}
                    />
                  </View>
                );
              })}
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}
