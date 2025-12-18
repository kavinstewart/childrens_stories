import { View, Text, Pressable, Image, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { useStory } from '@/features/stories/hooks';
import { api } from '@/lib/api';

export default function StoryReader() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: story, isLoading, error } = useStory(id);
  const [currentSpread, setCurrentSpread] = useState(0);

  if (isLoading) {
    return (
      <LinearGradient
        colors={['#FEF3C7', '#FDE68A']}
        style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
      >
        <ActivityIndicator size="large" color="#92400E" />
        <Text className="text-amber-800 mt-4">Loading story...</Text>
      </LinearGradient>
    );
  }

  if (error || !story) {
    return (
      <LinearGradient
        colors={['#FEF3C7', '#FDE68A']}
        style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
      >
        <Text className="text-6xl mb-4">😕</Text>
        <Text className="text-amber-800 text-xl font-bold mb-4">
          Couldn't load story
        </Text>
        <Pressable
          onPress={() => router.back()}
          className="bg-amber-600 px-6 py-3 rounded-xl"
        >
          <Text className="text-white font-bold">Go Back</Text>
        </Pressable>
      </LinearGradient>
    );
  }

  // Use spreads (new format) or fall back to pages (backwards compatibility)
  const spreads = story.spreads || story.pages || [];
  const totalSpreads = spreads.length;
  const currentSpreadData = spreads[currentSpread];

  // Get image URL for current spread if it has an illustration
  const imageUrl = story.is_illustrated && currentSpreadData
    ? api.getSpreadImageUrl(story.id, currentSpreadData.spread_number)
    : null;

  return (
    <LinearGradient
      colors={['#FEF3C7', '#FDE68A']}
      style={{ flex: 1 }}
    >
      <SafeAreaView className="flex-1" edges={['top', 'left', 'right']}>
        {/* Top Bar */}
        <View className="flex-row items-center justify-between px-6 py-4">
          <Pressable
            onPress={() => router.back()}
            className="bg-white/80 p-3 rounded-full"
          >
            <Text className="text-xl">←</Text>
          </Pressable>

          <View className="items-center">
            <Text className="text-lg font-bold text-amber-800">
              {story.title || 'Untitled Story'}
            </Text>
            <Text className="text-amber-600">
              Spread {currentSpread + 1} of {totalSpreads}
            </Text>
          </View>

          <Pressable className="bg-white/80 p-3 rounded-full">
            <Text className="text-xl">⚙️</Text>
          </Pressable>
        </View>

        {/* Story Content */}
        <View className="flex-1 flex-row px-6 gap-6">
          {/* Illustration Side */}
          <View className="flex-1 bg-white rounded-3xl overflow-hidden shadow-lg">
            {imageUrl ? (
              <Image
                source={{ uri: imageUrl }}
                className="flex-1"
                resizeMode="contain"
                style={{ backgroundColor: '#FEF3C7' }}
              />
            ) : (
              <View className="flex-1 items-center justify-center bg-amber-50">
                <Text className="text-8xl">📖</Text>
                <Text className="text-amber-600 mt-4 text-center px-4">
                  {story.is_illustrated
                    ? 'Illustration loading...'
                    : 'Text-only story'}
                </Text>
              </View>
            )}
          </View>

          {/* Text Side */}
          <View className="flex-1 bg-white rounded-3xl p-8 shadow-lg justify-center">
            {currentSpreadData ? (
              <Text className="text-2xl leading-relaxed text-gray-800">
                {currentSpreadData.text}
              </Text>
            ) : (
              <Text className="text-xl text-gray-500 italic">
                No content for this spread
              </Text>
            )}
          </View>
        </View>

        {/* Navigation */}
        <View className="flex-row items-center justify-between px-6 py-6">
          <Pressable
            onPress={() => setCurrentSpread(Math.max(0, currentSpread - 1))}
            disabled={currentSpread === 0}
            className="bg-white px-8 py-4 rounded-2xl"
            style={{ opacity: currentSpread === 0 ? 0.5 : 1 }}
          >
            <Text className="text-lg font-bold text-amber-800">← Back</Text>
          </Pressable>

          {/* Progress dots - typically 12 spreads, so show all */}
          <View className="flex-row gap-2">
            {[...Array(totalSpreads)].map((_, i) => {
              const isCurrentSpread = i === currentSpread;

              return (
                <Pressable
                  key={i}
                  onPress={() => setCurrentSpread(i)}
                  className={`w-3 h-3 rounded-full ${
                    isCurrentSpread
                      ? 'bg-amber-600'
                      : 'bg-amber-200'
                  }`}
                />
              );
            })}
          </View>

          <Pressable
            onPress={() => setCurrentSpread(Math.min(totalSpreads - 1, currentSpread + 1))}
            disabled={currentSpread >= totalSpreads - 1}
            className="bg-amber-600 px-8 py-4 rounded-2xl"
            style={{ opacity: currentSpread >= totalSpreads - 1 ? 0.5 : 1 }}
          >
            <Text className="text-lg font-bold text-white">Next →</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}
