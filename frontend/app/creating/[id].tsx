import { View, Text, Pressable } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useEffect } from 'react';
import { useStoryPolling } from '@/features/stories/hooks';

const stages = [
  { status: 'pending', label: 'Getting ready...', icon: '🌟' },
  { status: 'running', label: 'Creating your story...', icon: '✍️' },
  { status: 'completed', label: 'All done!', icon: '🎉' },
  { status: 'failed', label: 'Oops, something went wrong', icon: '😢' },
];

export default function CreatingStory() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: story, isLoading, error } = useStoryPolling(id);

  // Navigate to reader when story is completed
  useEffect(() => {
    if (story?.status === 'completed') {
      const timer = setTimeout(() => {
        router.replace(`/read/${id}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [story?.status, id, router]);

  const currentStage = stages.find(s => s.status === story?.status) || stages[0];
  const progress = story?.status === 'completed' ? 100
    : story?.status === 'running' ? 50
    : story?.status === 'failed' ? 100
    : 10;

  return (
    <LinearGradient
      colors={story?.status === 'failed'
        ? ['#FCA5A5', '#EF4444', '#DC2626']
        : ['#8B5CF6', '#6366F1', '#4F46E5']
      }
      style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
    >
      {/* Wizard Character */}
      <View className="mb-8">
        <Text className="text-[120px]">🧙‍♂️</Text>
      </View>

      {/* Progress Stage */}
      <View className="items-center mb-12">
        <Text className="text-6xl mb-4">{currentStage.icon}</Text>
        <Text className="text-3xl font-bold text-white text-center">
          {currentStage.label}
        </Text>
        {story?.title && story.status === 'running' && (
          <Text className="text-xl text-white/80 mt-2 text-center">
            "{story.title}"
          </Text>
        )}
        {story?.status === 'completed' && story?.title && (
          <Text className="text-xl text-white/80 mt-2 text-center">
            "{story.title}" is ready!
          </Text>
        )}
        {story?.status === 'failed' && story?.error_message && (
          <Text className="text-lg text-white/80 mt-4 text-center px-8">
            {story.error_message}
          </Text>
        )}
      </View>

      {/* Progress Bar */}
      <View className="w-80 h-4 bg-white/30 rounded-full overflow-hidden">
        <View
          className="h-full bg-white rounded-full"
          style={{ width: `${progress}%` }}
        />
      </View>

      {/* Story info */}
      {story && (
        <View className="mt-6 items-center">
          {story.page_count && (
            <Text className="text-white/80">
              {story.page_count} pages • {story.word_count} words
            </Text>
          )}
        </View>
      )}

      {/* Action buttons for failed state */}
      {story?.status === 'failed' && (
        <View className="flex-row gap-4 mt-8">
          <Pressable
            onPress={() => router.replace('/')}
            className="bg-white/20 px-6 py-3 rounded-xl"
          >
            <Text className="text-white font-bold">Go Home</Text>
          </Pressable>
          <Pressable
            onPress={() => router.replace('/new')}
            className="bg-white px-6 py-3 rounded-xl"
          >
            <Text className="text-purple-600 font-bold">Try Again</Text>
          </Pressable>
        </View>
      )}

      {/* Loading indicator */}
      {(isLoading || !story) && (
        <Text className="text-white/60 mt-8">Loading...</Text>
      )}

      {/* Error from API */}
      {error && (
        <View className="mt-8 items-center">
          <Text className="text-white/80 mb-4">
            Couldn't connect to server
          </Text>
          <Pressable
            onPress={() => router.replace('/')}
            className="bg-white px-6 py-3 rounded-xl"
          >
            <Text className="text-purple-600 font-bold">Go Home</Text>
          </Pressable>
        </View>
      )}
    </LinearGradient>
  );
}
