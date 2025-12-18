import { View, Text, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useStories } from '@/features/stories/hooks';
import { Story } from '@/lib/api';

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
            <View className="flex-row flex-wrap gap-4">
              {stories.map((story, index) => (
                <Pressable
                  key={story.id}
                  onPress={() => {
                    if (story.status === 'completed') {
                      router.push(`/read/${story.id}`);
                    } else if (story.status === 'pending' || story.status === 'running') {
                      router.push(`/creating/${story.id}`);
                    }
                  }}
                  style={({ pressed }) => ({
                    width: '23%',
                    aspectRatio: 3/4,
                    borderRadius: 16,
                    overflow: 'hidden',
                    opacity: pressed ? 0.9 : 1,
                    transform: [{ scale: pressed ? 0.98 : 1 }],
                  })}
                >
                  <LinearGradient
                    colors={cardColors[index % cardColors.length]}
                    style={{ flex: 1, alignItems: 'center', justifyContent: 'center', padding: 16 }}
                  >
                    {/* Status indicator for in-progress stories */}
                    {(story.status === 'pending' || story.status === 'running') && (
                      <View className="absolute top-2 right-2 bg-white/80 px-2 py-1 rounded-full">
                        <Text className="text-xs">⏳</Text>
                      </View>
                    )}
                    {story.status === 'failed' && (
                      <View className="absolute top-2 right-2 bg-red-500 px-2 py-1 rounded-full">
                        <Text className="text-xs">❌</Text>
                      </View>
                    )}

                    <Text className="text-5xl mb-2">{getStoryIcon(story)}</Text>
                    <Text className="text-white font-bold text-center text-sm" numberOfLines={2}>
                      {story.title || story.goal || 'Untitled Story'}
                    </Text>
                    {story.page_count && (
                      <Text className="text-white/80 text-xs mt-1">
                        {story.page_count} pages
                      </Text>
                    )}
                  </LinearGradient>
                </Pressable>
              ))}
            </View>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}
