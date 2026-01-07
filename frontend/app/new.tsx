import { View, Text, TextInput, ScrollView, ActivityIndicator, StyleProp, ViewStyle, Pressable } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useState, useEffect } from 'react';
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
import { pillColors, inspirationPrompts } from '@/lib/story-prompts';

// Wiggle animation for the create button
function WiggleButton({ children, enabled, onPress, style }: {
  children: React.ReactNode;
  enabled: boolean;
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
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

// Helper to shuffle and pick N items from an array, assigning colors
function pickRandomWithColors<T>(arr: readonly T[], colors: typeof pillColors, count: number): (T & { color: (typeof pillColors)[number] })[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count).map((item, index) => ({
    ...item,
    color: colors[index % colors.length],
  }));
}

// Valid fallback messages (whitelist for security)
const VALID_FALLBACK_MESSAGES = new Set([
  'Voice unavailable - microphone permission denied',
  'Voice unavailable - connection failed',
  'Voice unavailable - connection timeout',
]);

export default function NewStory() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { fallback } = useLocalSearchParams<{ fallback?: string }>();
  const [prompt, setPrompt] = useState('');

  // Only show banner if fallback is a valid whitelisted message
  const validFallbackMessage = fallback && VALID_FALLBACK_MESSAGES.has(fallback) ? fallback : null;
  const [showFallbackBanner, setShowFallbackBanner] = useState(!!validFallbackMessage);
  // Pick 4 random inspiration prompts on mount with colors
  const [visiblePrompts] = useState(() => pickRandomWithColors(inspirationPrompts, pillColors, 4));

  const createStory = useCreateStory();

  // Auto-dismiss fallback banner after 5 seconds
  useEffect(() => {
    if (showFallbackBanner) {
      const timer = setTimeout(() => setShowFallbackBanner(false), 5000);
      return () => clearTimeout(timer);
    }
  }, [showFallbackBanner]);

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

      <View style={{ flex: 1, paddingTop: insets.top, paddingLeft: insets.left, paddingRight: insets.right }}>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 24 }}>
          {/* Voice Fallback Banner */}
          {showFallbackBanner && validFallbackMessage && (
            <Pressable
              onPress={() => setShowFallbackBanner(false)}
              style={{
                backgroundColor: 'rgba(124, 58, 237, 0.1)',
                borderRadius: 12,
                paddingHorizontal: 16,
                paddingVertical: 12,
                marginBottom: 16,
                flexDirection: 'row',
                alignItems: 'center',
              }}
            >
              <Text style={{ fontSize: 18, marginRight: 8 }}>🎤</Text>
              <Text
                style={{
                  fontFamily: fontFamily.nunito,
                  fontSize: 14,
                  color: '#6B7280',
                  flex: 1,
                }}
              >
                {validFallbackMessage}
              </Text>
              <Text style={{ fontSize: 14, color: '#9CA3AF' }}>✕</Text>
            </Pressable>
          )}

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

          {/* Inspiration Pills - colorful, directly under input */}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 20 }}>
            {visiblePrompts.map((item) => {
              const isSelected = prompt === item.prompt;
              return (
                <Pressable
                  key={item.pill}
                  onPress={() => setPrompt(item.prompt)}
                >
                  {({ pressed }) => (
                    <View
                      style={{
                        backgroundColor: isSelected ? item.color.selectedBg : item.color.bg,
                        paddingHorizontal: 18,
                        paddingVertical: 12,
                        borderRadius: 20,
                        borderWidth: 2,
                        borderColor: isSelected ? item.color.text : item.color.border,
                        transform: [{ scale: pressed ? 0.95 : 1 }],
                        shadowColor: item.color.text,
                        shadowOffset: { width: 0, height: 2 },
                        shadowOpacity: isSelected ? 0.3 : 0.15,
                        shadowRadius: 4,
                        elevation: isSelected ? 4 : 2,
                      }}
                    >
                      <Text
                        style={{
                          fontFamily: fontFamily.nunitoBold,
                          fontSize: 15,
                          color: item.color.text,
                        }}
                      >
                        {item.pill}
                      </Text>
                    </View>
                  )}
                </Pressable>
              );
            })}
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

          {/* Voice mode option */}
          <Pressable
            onPress={() => router.replace('/new-voice')}
            style={{
              marginTop: 24,
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
          >
            <Text style={{ fontSize: 18 }}>🎤</Text>
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 14,
                color: '#6B7280',
              }}
            >
              Or use voice instead
            </Text>
          </Pressable>
        </ScrollView>
      </View>
    </LinearGradient>
  );
}
