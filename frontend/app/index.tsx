import { View, Text, Pressable, ScrollView, ActivityIndicator, Image, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useStories } from '@/features/stories/hooks';
import { Story, api } from '@/lib/api';

// Grid configuration
const GRID_PADDING = 24; // matches contentContainerStyle padding
const GRID_GAP = 16;     // gap between cards
const COLUMNS = 4;       // number of columns

// Color gradients for story cards based on index
const cardColors: readonly [string, string][] = [
  ['#FCD34D', '#F97316'], // amber/orange
  ['#A78BFA', '#7C3AED'], // purple
  ['#F472B6', '#EC4899'], // pink
  ['#22D3EE', '#3B82F6'], // cyan/blue
  ['#34D399', '#10B981'], // green
  ['#FB923C', '#EA580C'], // orange
];

// Icons based on theme or goal keywords
function getStoryIcon(story: Story): string {
  const goal = story.goal?.toLowerCase() || '';
  const title = story.title?.toLowerCase() || '';
  const text = goal + ' ' + title;

  if (text.includes('bear')) return '🐻';
  if (text.includes('space') || text.includes('rocket')) return '🚀';
  if (text.includes('ocean') || text.includes('fish') || text.includes('sea')) return '🐠';
  if (text.includes('garden') || text.includes('flower')) return '🌻';
  if (text.includes('friend')) return '👫';
  if (text.includes('brave') || text.includes('courage')) return '🦸';
  if (text.includes('kind')) return '💝';
  if (text.includes('share') || text.includes('sharing')) return '🤝';
  if (text.includes('color')) return '🌈';
  if (text.includes('count')) return '🔢';
  if (text.includes('mouse') || text.includes('mice')) return '🐭';
  if (text.includes('cat')) return '🐱';
  if (text.includes('dog')) return '🐶';
  if (text.includes('bird')) return '🐦';
  if (text.includes('magic') || text.includes('wizard')) return '🧙‍♂️';
  return '📖'; // default book icon
}

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
  const illustrationHeight = cardHeight * 0.70; // 70% for illustration
  const infoHeight = cardHeight * 0.30; // 30% for title

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
                // Use first spread illustration if available
                const coverImageUrl = story.is_illustrated ? api.getSpreadImageUrl(story.id, 1) : null;
                const gradientColors = cardColors[index % cardColors.length];

                // Margin logic: right margin for all except last in row
                const columnIndex = index % COLUMNS;
                const hasRightMargin = columnIndex < COLUMNS - 1;

                return (
                  <View
                    key={story.id}
                    style={{
                      width: cardWidth,
                      height: cardHeight,
                      marginRight: hasRightMargin ? GRID_GAP : 0,
                      marginBottom: GRID_GAP,
                    }}
                  >
                    <Pressable
                      onPress={() => {
                        if (story.status === 'completed') {
                          router.push(`/read/${story.id}`);
                        } else if (story.status === 'pending' || story.status === 'running') {
                          router.push(`/creating/${story.id}`);
                        }
                      }}
                      style={({ pressed }) => ({
                        flex: 1,
                        borderRadius: 16,
                        overflow: 'hidden',
                        opacity: pressed ? 0.9 : 1,
                        transform: [{ scale: pressed ? 0.98 : 1 }],
                        // Add shadow for depth
                        shadowColor: '#000',
                        shadowOffset: { width: 0, height: 2 },
                        shadowOpacity: 0.1,
                        shadowRadius: 4,
                        elevation: 3,
                      })}
                    >
                      {/* Illustration area - 70% height */}
                      <View style={{
                        height: illustrationHeight,
                        borderTopLeftRadius: 16,
                        borderTopRightRadius: 16,
                        overflow: 'hidden',
                      }}>
                        {coverImageUrl ? (
                          <Image
                            source={{ uri: coverImageUrl }}
                            style={{ width: '100%', height: '100%' }}
                            resizeMode="cover"
                          />
                        ) : (
                          <LinearGradient
                            colors={gradientColors}
                            style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
                          >
                            <Text style={{ fontSize: 48 }}>{getStoryIcon(story)}</Text>
                          </LinearGradient>
                        )}

                        {/* Status badge */}
                        {(story.status === 'pending' || story.status === 'running') && (
                          <View style={{ position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(255,255,255,0.9)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
                            <Text style={{ fontSize: 12 }}>⏳</Text>
                          </View>
                        )}
                        {story.status === 'failed' && (
                          <View style={{ position: 'absolute', top: 8, right: 8, backgroundColor: '#EF4444', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
                            <Text style={{ fontSize: 12 }}>❌</Text>
                          </View>
                        )}
                        {story.status === 'completed' && (
                          <View style={{ position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(34,197,94,0.9)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 12 }}>
                            <Text style={{ fontSize: 12, color: 'white' }}>✓</Text>
                          </View>
                        )}
                      </View>

                      {/* Info section - 30% height, title only */}
                      <View style={{
                        height: infoHeight,
                        backgroundColor: '#FEF3C7',
                        paddingHorizontal: 12,
                        paddingVertical: 10,
                        justifyContent: 'center',
                        borderBottomLeftRadius: 16,
                        borderBottomRightRadius: 16,
                      }}>
                        <Text
                          style={{ color: '#1F2937', fontWeight: 'bold', fontSize: 18, lineHeight: 22 }}
                          numberOfLines={2}
                        >
                          {story.title || story.goal || 'Untitled Story'}
                        </Text>
                      </View>
                    </Pressable>
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
