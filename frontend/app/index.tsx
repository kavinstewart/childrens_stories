import { View, Text, Pressable, ScrollView, ActivityIndicator, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useStories } from '@/features/stories/hooks';
import { Story } from '@/lib/api';
import { StoryCard } from '@/components/StoryCard';

// Grid configuration
const GRID_PADDING = 24; // matches contentContainerStyle padding
const GRID_GAP = 16;     // gap between cards
const COLUMNS = 4;       // number of columns

export default function StoryLibrary() {
  const router = useRouter();
  const { data: stories, isLoading, error, refetch } = useStories();
  const { width: screenWidth } = useWindowDimensions();

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
      <SafeAreaView className="flex-1" edges={['top', 'left', 'right']}>
        <ScrollView
          className="flex-1"
          contentContainerStyle={{ padding: 24 }}
          showsVerticalScrollIndicator={false}
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

            {/* New Story Button */}
            <Pressable
              onPress={() => router.push('/new')}
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
          </View>

          {/* Loading State */}
          {isLoading && (
            <View className="items-center justify-center py-20">
              <ActivityIndicator size="large" color="#7C3AED" />
              <Text className="text-gray-600 mt-4">Loading stories...</Text>
            </View>
          )}

          {/* Error State */}
          {error && (
            <View className="items-center justify-center py-20 bg-red-50 rounded-3xl">
              <Text className="text-4xl mb-4">😕</Text>
              <Text className="text-red-800 font-bold text-xl mb-2">
                Couldn't load stories
              </Text>
              <Text className="text-red-600 mb-4">
                Is the backend running on port 8000?
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
