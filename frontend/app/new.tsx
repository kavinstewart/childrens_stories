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
import { fontFamily } from '@/lib/fonts';
import { FloatingElement } from '@/components/animations';

// Inspiration prompts - shown as tappable pills, randomized on mount
const inspirationPrompts = [
  // Historical events
  { pill: "Napoleon's Return", prompt: "Napoleon escapes from Elba and marches back to Paris" },
  { pill: 'French Revolution', prompt: 'The people of France rise up against their king' },
  { pill: 'Fall of Constantinople', prompt: 'The last day of the great Byzantine city' },
  { pill: 'Boston Tea Party', prompt: 'Colonists dump tea into the harbor to protest unfair taxes' },
  { pill: 'Moon Landing', prompt: "Astronauts take humanity's first steps on the moon" },
  { pill: 'Berlin Wall Falls', prompt: 'The night the wall came down and families reunited' },
  { pill: 'Silk Road Journey', prompt: 'A merchant travels the ancient trade route between East and West' },
  // Human body & diseases
  { pill: 'How Arteries Clog', prompt: 'A journey through blood vessels learning about atherosclerosis' },
  { pill: "Parkinson's Disease", prompt: "Understanding why grandpa's hands shake" },
  { pill: 'How Livers Work', prompt: "The body's amazing cleaning factory" },
  { pill: 'Fighting Cancer', prompt: "How the body's defenders battle rogue cells" },
  { pill: 'Diabetes Explained', prompt: 'Why some bodies need help with sugar' },
  { pill: 'How Vaccines Work', prompt: 'Training tiny soldiers to protect the body' },
  { pill: 'The Beating Heart', prompt: "A day in the life of the body's hardest-working muscle" },
  // Religious & philosophical
  { pill: "Arjuna's Dilemma", prompt: "The warrior who didn't want to fight (from the Bhagavad Gita)" },
  { pill: 'Buddha Under Tree', prompt: 'A prince who gave up everything to find peace' },
  { pill: 'David vs Goliath', prompt: 'A shepherd boy faces a giant warrior' },
  { pill: "Noah's Great Boat", prompt: 'Building an ark to save all the animals' },
  { pill: 'The Good Samaritan', prompt: 'A stranger helps someone everyone else ignored' },
  { pill: "Muhammad's Journey", prompt: 'The night journey to the heavens' },
  // Science & nature
  { pill: 'How Stars Die', prompt: "The spectacular end of a star's life" },
  { pill: 'Dinosaur Extinction', prompt: 'The day the asteroid changed everything' },
  { pill: 'How Bees Dance', prompt: 'The secret language of the hive' },
  { pill: 'Volcano Erupts', prompt: 'What happens deep inside an erupting mountain' },
  { pill: 'Ice Age Begins', prompt: 'When the world froze over' },
  // Philosophy & ideas
  { pill: 'Socrates Questions', prompt: 'The man who asked too many questions' },
  { pill: "Plato's Cave", prompt: 'Prisoners who only saw shadows' },
  { pill: 'Golden Rule', prompt: 'The idea that connects all cultures' },
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

// Helper to shuffle and pick N items from an array
function pickRandom<T>(arr: T[], count: number): T[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

export default function NewStory() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  // Pick 4 random inspiration prompts on mount
  const [visiblePrompts] = useState(() => pickRandom(inspirationPrompts, 4));

  const createStory = useCreateStory();

  const canCreate = prompt.trim().length > 0;

  const handleCreate = async () => {
    const goal = prompt.trim();

    try {
      const result = await createStory.mutateAsync({ goal });

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
      {/* Floating decorations */}
      <FloatingElement delay={0} duration={4} style={{ top: 80, left: 24 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>✨</Text>
      </FloatingElement>
      <FloatingElement delay={1} duration={5} style={{ top: 128, right: 32 }}>
        <Text style={{ fontSize: 20, opacity: 0.25 }}>📝</Text>
      </FloatingElement>
      <FloatingElement delay={2} duration={4.5} style={{ bottom: 128, right: 48 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>🌈</Text>
      </FloatingElement>
      <FloatingElement delay={0.5} duration={5} style={{ bottom: 96, left: 40 }}>
        <Text style={{ fontSize: 20, opacity: 0.25 }}>💫</Text>
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
              <Text style={{ fontSize: 20 }}>←</Text>
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
              <Text style={{ fontSize: 24, marginRight: 8 }}>✨</Text>
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
              placeholder="A story about..."
              placeholderTextColor="#9CA3AF"
              multiline
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 16,
                color: '#374151',
                backgroundColor: '#F9FAFB',
                borderRadius: 16,
                padding: 16,
                minHeight: 100,
                textAlignVertical: 'top',
              }}
            />
          </View>

          {/* Inspiration Pills */}
          <View
            style={{
              backgroundColor: 'rgba(255,255,255,0.8)',
              borderRadius: 24,
              padding: 20,
              marginBottom: 20,
            }}
          >
            <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 12 }}>
              <Text style={{ fontSize: 20, marginRight: 8 }}>💡</Text>
              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  fontSize: 18,
                  color: '#374151',
                }}
              >
                Quick ideas
              </Text>
            </View>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {visiblePrompts.map((item) => (
                <Pressable
                  key={item.pill}
                  onPress={() => setPrompt(item.prompt)}
                  style={({ pressed }) => ({
                    flexShrink: 0,
                    backgroundColor: prompt === item.prompt ? '#FEF3C7' : '#F3F4F6',
                    paddingHorizontal: 16,
                    paddingVertical: 10,
                    borderRadius: 16,
                    borderWidth: 1,
                    borderColor: prompt === item.prompt ? '#FBBF24' : 'transparent',
                    transform: [{ scale: pressed ? 0.95 : 1 }],
                  })}
                >
                  <Text
                    style={{
                      fontFamily: fontFamily.nunitoSemiBold,
                      fontSize: 14,
                      color: prompt === item.prompt ? '#B45309' : '#4B5563',
                    }}
                  >
                    {item.pill}
                  </Text>
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
                  <Text style={{ fontSize: 20 }}>🪄</Text>
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
              Tell me about your story or tap an idea above
            </Text>
          )}
        </ScrollView>
      </SafeAreaView>
    </LinearGradient>
  );
}
