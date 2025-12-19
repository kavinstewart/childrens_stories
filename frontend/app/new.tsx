import { View, Text, TextInput, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { useCreateStory } from '@/features/stories/hooks';
import { GenerationType } from '@/lib/api';
import { fontFamily } from '@/lib/fonts';
import { FloatingElement } from '@/components/animations';

// Themes with gradient colors for selected state
const themes = [
  { id: 'kindness', label: 'Kindness', icon: '\u{1F495}', hint: 'being kind and helpful', colors: ['#F472B6', '#E11D48'] },
  { id: 'bravery', label: 'Bravery', icon: '\u{1F981}', hint: 'overcoming fears', colors: ['#FBBF24', '#F97316'] },
  { id: 'sharing', label: 'Sharing', icon: '\u{1F91D}', hint: 'learning to share with others', colors: ['#34D399', '#14B8A6'] },
  { id: 'creativity', label: 'Creativity', icon: '\u{1F3A8}', hint: 'using imagination', colors: ['#A78BFA', '#8B5CF6'] },
  { id: 'friendship', label: 'Friendship', icon: '\u{1F31F}', hint: 'making and keeping friends', colors: ['#38BDF8', '#3B82F6'] },
  { id: 'patience', label: 'Patience', icon: '\u{1F422}', hint: 'learning to wait', colors: ['#A3E635', '#22C55E'] },
];

const generationTypes: { id: GenerationType; label: string; description: string }[] = [
  { id: 'simple', label: 'Quick', description: 'Fast generation, ~1 min' },
  { id: 'standard', label: 'Standard', description: 'Quality checked, ~3 min' },
  { id: 'illustrated', label: 'Illustrated', description: 'With pictures, ~10 min' },
];

// Wiggle animation for the create button
function WiggleButton({ children, enabled, onPress, style }: {
  children: React.ReactNode;
  enabled: boolean;
  onPress: () => void;
  style?: any;
}) {
  const rotation = useSharedValue(0);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }));

  const handlePressIn = () => {
    if (enabled) {
      rotation.value = withRepeat(
        withSequence(
          withTiming(-3, { duration: 100, easing: Easing.inOut(Easing.ease) }),
          withTiming(3, { duration: 100, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      );
    }
  };

  const handlePressOut = () => {
    rotation.value = withTiming(0, { duration: 100 });
  };

  return (
    <Pressable
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      disabled={!enabled}
    >
      <Animated.View style={[style, animatedStyle]}>
        {children}
      </Animated.View>
    </Pressable>
  );
}

export default function NewStory() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [generationType, setGenerationType] = useState<GenerationType>('illustrated');

  const createStory = useCreateStory();

  const canCreate = prompt.trim().length > 0 || selectedTheme;

  const handleCreate = async () => {
    // Build the goal from prompt and theme
    let goal = prompt.trim();
    if (selectedTheme) {
      const theme = themes.find(t => t.id === selectedTheme);
      if (theme && !goal.toLowerCase().includes(selectedTheme)) {
        goal = goal ? `${goal} (theme: ${theme.hint})` : `A story about ${theme.hint}`;
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

  const selectedThemeData = themes.find(t => t.id === selectedTheme);

  return (
    <LinearGradient
      colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']}
      style={{ flex: 1 }}
    >
      {/* Floating decorations */}
      <FloatingElement delay={0} duration={4} style={{ top: 80, left: 24 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>{'\u2728'}</Text>
      </FloatingElement>
      <FloatingElement delay={1} duration={5} style={{ top: 128, right: 32 }}>
        <Text style={{ fontSize: 20, opacity: 0.25 }}>{'\u{1F4DD}'}</Text>
      </FloatingElement>
      <FloatingElement delay={2} duration={4.5} style={{ bottom: 128, right: 48 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>{'\u{1F308}'}</Text>
      </FloatingElement>
      <FloatingElement delay={0.5} duration={5} style={{ bottom: 96, left: 40 }}>
        <Text style={{ fontSize: 20, opacity: 0.25 }}>{'\u{1F4AB}'}</Text>
      </FloatingElement>

      <SafeAreaView style={{ flex: 1 }} edges={['top', 'left', 'right']}>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 24 }}>
          {/* Header */}
          <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 24 }}>
            <Pressable
              onPress={() => router.back()}
              style={{
                backgroundColor: 'rgba(255,255,255,0.7)',
                padding: 12,
                borderRadius: 12,
                marginRight: 16,
              }}
            >
              <Text style={{ fontSize: 20 }}>{'\u2190'}</Text>
            </Pressable>
            <Text
              style={{
                fontFamily: fontFamily.baloo,
                fontSize: 28,
                color: 'transparent',
              }}
            >
              {/* Gradient text workaround - we'll use a solid color with emoji */}
            </Text>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Text style={{ fontSize: 24, marginRight: 8 }}>{'\u2728'}</Text>
              <Text
                style={{
                  fontFamily: fontFamily.baloo,
                  fontSize: 28,
                  color: '#7C3AED',
                }}
              >
                New Story
              </Text>
            </View>
          </View>

          {/* Prompt Input */}
          <View
            style={{
              backgroundColor: 'rgba(255,255,255,0.8)',
              borderRadius: 24,
              padding: 20,
              marginBottom: 20,
            }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunitoBold,
                fontSize: 18,
                color: '#374151',
                marginBottom: 12,
              }}
            >
              What should your story be about?
            </Text>
            <TextInput
              value={prompt}
              onChangeText={setPrompt}
              placeholder="A brave little mouse who dreams of becoming a chef..."
              placeholderTextColor="#9CA3AF"
              multiline
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 16,
                color: '#374151',
                backgroundColor: '#F9FAFB',
                borderRadius: 16,
                padding: 16,
                minHeight: 120,
                textAlignVertical: 'top',
              }}
            />
          </View>

          {/* Theme Selection */}
          <View
            style={{
              backgroundColor: 'rgba(255,255,255,0.8)',
              borderRadius: 24,
              padding: 20,
              marginBottom: 20,
            }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunitoBold,
                fontSize: 18,
                color: '#374151',
                marginBottom: 12,
              }}
            >
              Pick a lesson to learn{' '}
              <Text style={{ fontFamily: fontFamily.nunito, color: '#9CA3AF' }}>(optional)</Text>
            </Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {themes.map((theme) => {
                const isSelected = selectedTheme === theme.id;
                return (
                  <Pressable
                    key={theme.id}
                    onPress={() => setSelectedTheme(isSelected ? null : theme.id)}
                    style={({ pressed }) => ({
                      transform: [{ scale: pressed ? 0.95 : 1 }],
                    })}
                  >
                    {isSelected ? (
                      <LinearGradient
                        colors={theme.colors as [string, string]}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 0 }}
                        style={{
                          flexDirection: 'row',
                          alignItems: 'center',
                          gap: 8,
                          paddingHorizontal: 16,
                          paddingVertical: 10,
                          borderRadius: 20,
                          shadowColor: theme.colors[1],
                          shadowOffset: { width: 0, height: 2 },
                          shadowOpacity: 0.3,
                          shadowRadius: 4,
                          elevation: 4,
                        }}
                      >
                        <Text style={{ fontSize: 16 }}>{theme.icon}</Text>
                        <Text
                          style={{
                            fontFamily: fontFamily.nunitoSemiBold,
                            color: 'white',
                          }}
                        >
                          {theme.label}
                        </Text>
                      </LinearGradient>
                    ) : (
                      <View
                        style={{
                          flexDirection: 'row',
                          alignItems: 'center',
                          gap: 8,
                          paddingHorizontal: 16,
                          paddingVertical: 10,
                          borderRadius: 20,
                          backgroundColor: '#F3F4F6',
                        }}
                      >
                        <Text style={{ fontSize: 16 }}>{theme.icon}</Text>
                        <Text
                          style={{
                            fontFamily: fontFamily.nunitoSemiBold,
                            color: '#4B5563',
                          }}
                        >
                          {theme.label}
                        </Text>
                      </View>
                    )}
                  </Pressable>
                );
              })}
            </View>
          </View>

          {/* Inspiration tip */}
          <View
            style={{
              backgroundColor: 'rgba(251, 191, 36, 0.15)',
              borderRadius: 16,
              padding: 16,
              marginBottom: 20,
              borderWidth: 1,
              borderColor: 'rgba(251, 191, 36, 0.3)',
            }}
          >
            <View style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 12 }}>
              <Text style={{ fontSize: 24 }}>{'\u{1F4A1}'}</Text>
              <View style={{ flex: 1 }}>
                <Text
                  style={{
                    fontFamily: fontFamily.nunitoSemiBold,
                    color: '#B45309',
                    marginBottom: 4,
                  }}
                >
                  Need inspiration?
                </Text>
                <Text
                  style={{
                    fontFamily: fontFamily.nunito,
                    color: '#D97706',
                    fontSize: 14,
                  }}
                >
                  Try: "A penguin who's afraid of water" or "Two best friends on a treasure hunt"
                </Text>
              </View>
            </View>
          </View>

          {/* Generation Type */}
          <View
            style={{
              backgroundColor: 'rgba(255,255,255,0.8)',
              borderRadius: 24,
              padding: 20,
              marginBottom: 20,
            }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunitoBold,
                fontSize: 18,
                color: '#374151',
                marginBottom: 12,
              }}
            >
              Generation mode
            </Text>
            <View style={{ gap: 12 }}>
              {generationTypes.map((type) => (
                <Pressable
                  key={type.id}
                  onPress={() => setGenerationType(type.id)}
                  style={{
                    padding: 16,
                    borderRadius: 16,
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    backgroundColor: generationType === type.id ? '#EDE9FE' : '#F9FAFB',
                    borderWidth: 2,
                    borderColor: generationType === type.id ? '#8B5CF6' : 'transparent',
                  }}
                >
                  <View>
                    <Text
                      style={{
                        fontFamily: fontFamily.nunitoBold,
                        fontSize: 16,
                        color: generationType === type.id ? '#6D28D9' : '#374151',
                      }}
                    >
                      {type.label}
                    </Text>
                    <Text
                      style={{
                        fontFamily: fontFamily.nunito,
                        color: '#6B7280',
                      }}
                    >
                      {type.description}
                    </Text>
                  </View>
                  {generationType === type.id && (
                    <Text style={{ fontSize: 20 }}>{'\u2713'}</Text>
                  )}
                </Pressable>
              ))}
            </View>
          </View>

          {/* Error Message */}
          {createStory.error && (
            <View
              style={{
                backgroundColor: '#FEE2E2',
                borderRadius: 16,
                padding: 16,
                marginBottom: 20,
              }}
            >
              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  color: '#991B1B',
                }}
              >
                Failed to create story
              </Text>
              <Text
                style={{
                  fontFamily: fontFamily.nunito,
                  color: '#DC2626',
                }}
              >
                {createStory.error instanceof Error
                  ? createStory.error.message
                  : 'Unknown error'}
              </Text>
            </View>
          )}

          {/* Create Button */}
          <WiggleButton
            enabled={!!canCreate && !createStory.isPending}
            onPress={handleCreate}
            style={{
              marginBottom: 16,
            }}
          >
            <LinearGradient
              colors={
                canCreate && !createStory.isPending
                  ? ['#EC4899', '#8B5CF6', '#6366F1']
                  : ['#D1D5DB', '#9CA3AF', '#9CA3AF']
              }
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={{
                paddingVertical: 16,
                borderRadius: 16,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                shadowColor: canCreate ? '#8B5CF6' : '#9CA3AF',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.3,
                shadowRadius: 8,
                elevation: 8,
              }}
            >
              {createStory.isPending ? (
                <>
                  <ActivityIndicator color="white" />
                  <Text
                    style={{
                      fontFamily: fontFamily.nunitoBold,
                      fontSize: 18,
                      color: 'white',
                    }}
                  >
                    Creating...
                  </Text>
                </>
              ) : (
                <>
                  <Text style={{ fontSize: 20 }}>{'\u{1FA84}'}</Text>
                  <Text
                    style={{
                      fontFamily: fontFamily.nunitoBold,
                      fontSize: 18,
                      color: 'white',
                    }}
                  >
                    Create My Story
                  </Text>
                </>
              )}
            </LinearGradient>
          </WiggleButton>

          {/* Helper text when button is disabled */}
          {!canCreate && (
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 14,
                color: '#9CA3AF',
                textAlign: 'center',
              }}
            >
              Tell me about your story or pick a theme to get started
            </Text>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}
