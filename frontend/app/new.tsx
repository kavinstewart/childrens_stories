import { View, Text, TextInput, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { useCreateStory } from '@/features/stories/hooks';
import { GenerationType } from '@/lib/api';

const themes = [
  { id: 'sharing', label: 'Sharing', icon: '🤝', hint: 'learning to share with others' },
  { id: 'kindness', label: 'Kindness', icon: '💝', hint: 'being kind and helpful' },
  { id: 'bravery', label: 'Bravery', icon: '🦸', hint: 'overcoming fears' },
  { id: 'friendship', label: 'Friendship', icon: '👫', hint: 'making and keeping friends' },
  { id: 'counting', label: 'Counting', icon: '🔢', hint: 'learning numbers' },
  { id: 'colors', label: 'Colors', icon: '🌈', hint: 'exploring colors' },
];

const generationTypes: { id: GenerationType; label: string; description: string }[] = [
  { id: 'simple', label: 'Quick', description: 'Fast generation, ~1 min' },
  { id: 'standard', label: 'Standard', description: 'Quality checked, ~3 min' },
  { id: 'illustrated', label: 'Illustrated', description: 'With pictures, ~10 min' },
];

export default function NewStory() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [generationType, setGenerationType] = useState<GenerationType>('illustrated');

  const createStory = useCreateStory();

  const handleCreate = async () => {
    // Build the goal from prompt and theme
    let goal = prompt.trim();
    if (selectedTheme) {
      const theme = themes.find(t => t.id === selectedTheme);
      if (theme && !goal.toLowerCase().includes(selectedTheme)) {
        goal = `${goal} (theme: ${theme.hint})`;
      }
    }

    try {
      const result = await createStory.mutateAsync({
        goal,
        generation_type: generationType,
        target_age_range: '4-7',
      });

      // Navigate to the creating screen to show progress
      router.replace(`/creating/${result.id}`);
    } catch (error) {
      console.error('Failed to create story:', error);
    }
  };

  return (
    <LinearGradient
      colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']}
      style={{ flex: 1 }}
    >
      <SafeAreaView className="flex-1" edges={['top', 'left', 'right']}>
        <ScrollView className="flex-1" contentContainerStyle={{ padding: 24 }}>
          {/* Header */}
          <View className="flex-row items-center mb-8">
            <Pressable
              onPress={() => router.back()}
              className="bg-white/80 p-3 rounded-full mr-4"
            >
              <Text className="text-xl">←</Text>
            </Pressable>
            <Text className="text-3xl font-bold text-purple-800">
              Create New Story
            </Text>
          </View>

          {/* Prompt Input */}
          <View className="bg-white rounded-3xl p-6 mb-6">
            <Text className="text-lg font-bold text-gray-800 mb-3">
              What should this story be about?
            </Text>
            <TextInput
              className="bg-gray-50 rounded-2xl p-4 text-lg"
              style={{ minHeight: 120, textAlignVertical: 'top' }}
              placeholder="A brave little mouse who learns to share..."
              placeholderTextColor="#9CA3AF"
              multiline
              value={prompt}
              onChangeText={setPrompt}
            />
          </View>

          {/* Theme Selection */}
          <View className="bg-white rounded-3xl p-6 mb-6">
            <Text className="text-lg font-bold text-gray-800 mb-4">
              Pick a theme (optional)
            </Text>
            <View className="flex-row flex-wrap gap-3">
              {themes.map((theme) => (
                <Pressable
                  key={theme.id}
                  onPress={() => setSelectedTheme(
                    selectedTheme === theme.id ? null : theme.id
                  )}
                  className={`px-4 py-3 rounded-full flex-row items-center gap-2 ${
                    selectedTheme === theme.id
                      ? 'bg-purple-600'
                      : 'bg-gray-100'
                  }`}
                >
                  <Text className="text-xl">{theme.icon}</Text>
                  <Text className={`font-bold ${
                    selectedTheme === theme.id ? 'text-white' : 'text-gray-700'
                  }`}>
                    {theme.label}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>

          {/* Generation Type */}
          <View className="bg-white rounded-3xl p-6 mb-6">
            <Text className="text-lg font-bold text-gray-800 mb-4">
              Generation mode
            </Text>
            <View className="gap-3">
              {generationTypes.map((type) => (
                <Pressable
                  key={type.id}
                  onPress={() => setGenerationType(type.id)}
                  className={`p-4 rounded-2xl flex-row items-center justify-between ${
                    generationType === type.id
                      ? 'bg-purple-100 border-2 border-purple-600'
                      : 'bg-gray-50 border-2 border-transparent'
                  }`}
                >
                  <View>
                    <Text className={`font-bold text-lg ${
                      generationType === type.id ? 'text-purple-800' : 'text-gray-800'
                    }`}>
                      {type.label}
                    </Text>
                    <Text className="text-gray-500">{type.description}</Text>
                  </View>
                  {generationType === type.id && (
                    <Text className="text-2xl">✓</Text>
                  )}
                </Pressable>
              ))}
            </View>
          </View>

          {/* Error Message */}
          {createStory.error && (
            <View className="bg-red-100 rounded-2xl p-4 mb-6">
              <Text className="text-red-800 font-bold">Failed to create story</Text>
              <Text className="text-red-600">
                {createStory.error instanceof Error
                  ? createStory.error.message
                  : 'Unknown error'}
              </Text>
            </View>
          )}

          {/* Create Button */}
          <Pressable
            onPress={handleCreate}
            disabled={!prompt.trim() || createStory.isPending}
            className={`py-5 rounded-2xl items-center flex-row justify-center gap-3 ${
              prompt.trim() && !createStory.isPending ? 'bg-purple-600' : 'bg-gray-300'
            }`}
            style={({ pressed }) => ({
              opacity: pressed && prompt.trim() ? 0.8 : 1,
            })}
          >
            {createStory.isPending && (
              <ActivityIndicator color="white" />
            )}
            <Text className="text-xl font-bold text-white">
              {createStory.isPending ? 'Creating...' : 'Create My Story'}
            </Text>
          </Pressable>
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}
