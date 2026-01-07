/**
 * Voice recording screen for creating stories via speech.
 *
 * Uses Deepgram STT to transcribe speech in real-time,
 * then creates a story from the transcript.
 */

import { View, Text, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useState, useCallback, useEffect, useRef } from 'react';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
  withSpring,
  Easing,
  interpolate,
  cancelAnimation,
} from 'react-native-reanimated';
import { useCreateStory } from '@/features/stories/hooks';
import { fontFamily } from '@/lib/fonts';
import { FloatingElement } from '@/components/animations';
import { useSTT, STTTranscript } from '@/lib/voice';

// Pulsing microphone animation
function PulseMic({
  isListening,
  isSpeaking,
  onPress,
  disabled,
}: {
  isListening: boolean;
  isSpeaking: boolean;
  onPress: () => void;
  disabled: boolean;
}) {
  const pulse = useSharedValue(1);
  const ring = useSharedValue(0);

  useEffect(() => {
    if (isListening) {
      // Continuous pulse when listening
      pulse.value = withRepeat(
        withSequence(
          withTiming(1.05, { duration: 800, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: 800, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      );
    } else {
      cancelAnimation(pulse);
      pulse.value = withSpring(1);
    }
  }, [isListening, pulse]);

  useEffect(() => {
    if (isSpeaking) {
      // Expanding ring when speech detected
      ring.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 600 }),
          withTiming(0, { duration: 0 })
        ),
        -1,
        false
      );
    } else {
      cancelAnimation(ring);
      ring.value = 0;
    }
  }, [isSpeaking, ring]);

  const micStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
  }));

  const ringStyle = useAnimatedStyle(() => ({
    opacity: interpolate(ring.value, [0, 0.5, 1], [0.6, 0.3, 0]),
    transform: [{ scale: interpolate(ring.value, [0, 1], [1, 2]) }],
  }));

  return (
    <Pressable onPress={onPress} disabled={disabled}>
      <View style={{ alignItems: 'center', justifyContent: 'center' }}>
        {/* Pulsing ring when speaking */}
        {isSpeaking && (
          <Animated.View
            style={[
              {
                position: 'absolute',
                width: 140,
                height: 140,
                borderRadius: 70,
                backgroundColor: '#7C3AED',
              },
              ringStyle,
            ]}
          />
        )}

        <Animated.View style={micStyle}>
          <LinearGradient
            colors={
              isListening
                ? ['#EC4899', '#8B5CF6']
                : disabled
                ? ['#D1D5DB', '#9CA3AF']
                : ['#8B5CF6', '#6366F1']
            }
            style={{
              width: 140,
              height: 140,
              borderRadius: 70,
              alignItems: 'center',
              justifyContent: 'center',
              shadowColor: isListening ? '#EC4899' : '#8B5CF6',
              shadowOffset: { width: 0, height: 6 },
              shadowOpacity: 0.4,
              shadowRadius: 12,
              elevation: 10,
            }}
          >
            <Text style={{ fontSize: 56 }}>{isListening ? '🎙️' : '🎤'}</Text>
          </LinearGradient>
        </Animated.View>
      </View>
    </Pressable>
  );
}

export default function NewVoiceStory() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [transcript, setTranscript] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const transcriptRef = useRef('');

  const createStory = useCreateStory();

  // Handle transcript updates
  const handleTranscript = useCallback((data: STTTranscript) => {
    if (data.isFinal) {
      // Final transcript - append to accumulated text
      const newText = transcriptRef.current
        ? `${transcriptRef.current} ${data.transcript}`
        : data.transcript;
      transcriptRef.current = newText;
      setTranscript(newText);
    } else {
      // Interim transcript - show current accumulated + interim
      const displayText = transcriptRef.current
        ? `${transcriptRef.current} ${data.transcript}`
        : data.transcript;
      setTranscript(displayText);
    }
  }, []);

  // Handle speech detection
  const handleSpeechStarted = useCallback(() => {
    setIsSpeaking(true);
  }, []);

  const handleUtteranceEnd = useCallback(() => {
    setIsSpeaking(false);
  }, []);

  // Handle errors by navigating to text input as fallback
  const handleError = useCallback((errorMsg: string) => {
    // Map error to fallback message
    let fallbackMsg = 'Voice unavailable - connection failed';
    if (errorMsg.includes('permission')) {
      fallbackMsg = 'Voice unavailable - microphone permission denied';
    } else if (errorMsg.includes('timeout')) {
      fallbackMsg = 'Voice unavailable - connection timeout';
    }

    // Navigate to text input with fallback banner
    router.replace({
      pathname: '/new',
      params: { fallback: fallbackMsg },
    });
  }, [router]);

  const {
    status,
    startListening,
    stopListening,
    isListening,
    error,
  } = useSTT({
    onTranscript: handleTranscript,
    onSpeechStarted: handleSpeechStarted,
    onUtteranceEnd: handleUtteranceEnd,
    onError: handleError,
  });

  // Toggle recording
  const handleMicPress = async () => {
    if (isListening) {
      await stopListening();
    } else {
      // Clear previous transcript when starting fresh
      transcriptRef.current = '';
      setTranscript('');
      await startListening();
    }
  };

  // Create story from transcript
  const handleCreate = async () => {
    const goal = transcript.trim();
    if (!goal) return;

    try {
      await stopListening();
      const result = await createStory.mutateAsync({ goal });
      router.replace(`/creating/${result.id}`);
    } catch (err) {
      console.error('Failed to create story:', err);
    }
  };

  const canCreate = transcript.trim().length > 0 && !isListening;
  const isConnecting = status === 'connecting';

  return (
    <LinearGradient
      colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']}
      style={{ flex: 1 }}
    >
      {/* Floating decorations */}
      <FloatingElement delay={0} duration={4} style={{ top: 80, left: 24 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>🎵</Text>
      </FloatingElement>
      <FloatingElement delay={1} duration={5} style={{ top: 128, right: 32 }}>
        <Text style={{ fontSize: 20, opacity: 0.25 }}>💬</Text>
      </FloatingElement>
      <FloatingElement delay={2} duration={4.5} style={{ bottom: 180, right: 48 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>✨</Text>
      </FloatingElement>
      <FloatingElement delay={0.5} duration={5} style={{ bottom: 140, left: 40 }}>
        <Text style={{ fontSize: 20, opacity: 0.25 }}>🔊</Text>
      </FloatingElement>

      <View style={{ flex: 1, paddingTop: insets.top, paddingLeft: insets.left, paddingRight: insets.right }}>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ padding: 24, flexGrow: 1 }}>
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
            <Text style={{ fontSize: 24, marginRight: 8 }}>🎙️</Text>
            <Text
              style={{
                fontFamily: fontFamily.baloo,
                fontSize: 28,
                color: '#7C3AED',
              }}
            >
              Voice Story
            </Text>
          </View>

          {/* Instructions */}
          <View
            style={{
              backgroundColor: 'rgba(255,255,255,0.8)',
              borderRadius: 24,
              padding: 20,
              marginBottom: 24,
            }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunitoBold,
                fontSize: 18,
                color: '#374151',
                marginBottom: 8,
                textAlign: 'center',
              }}
            >
              {isListening ? "I'm listening..." : 'Tap the mic and tell me your story idea'}
            </Text>
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 14,
                color: '#6B7280',
                textAlign: 'center',
              }}
            >
              {isListening
                ? 'Speak clearly, I\'ll transcribe what you say'
                : 'For example: "A story about a brave little dragon who learns to make friends"'}
            </Text>
          </View>

          {/* Microphone Button */}
          <View style={{ alignItems: 'center', marginVertical: 32 }}>
            <PulseMic
              isListening={isListening}
              isSpeaking={isSpeaking}
              onPress={handleMicPress}
              disabled={isConnecting || createStory.isPending}
            />

            {/* Status text */}
            <View style={{ marginTop: 16, minHeight: 24, alignItems: 'center' }}>
              {isConnecting && (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <ActivityIndicator size="small" color="#7C3AED" />
                  <Text style={{ fontFamily: fontFamily.nunito, color: '#7C3AED' }}>
                    Connecting...
                  </Text>
                </View>
              )}
              {isListening && (
                <Text style={{ fontFamily: fontFamily.nunitoBold, color: '#EC4899' }}>
                  {isSpeaking ? '🔴 Speaking...' : '⏳ Waiting for speech...'}
                </Text>
              )}
              {!isListening && !isConnecting && transcript.length === 0 && (
                <Text style={{ fontFamily: fontFamily.nunito, color: '#9CA3AF' }}>
                  Tap to start
                </Text>
              )}
            </View>
          </View>

          {/* Transcript Display */}
          {transcript.length > 0 && (
            <View
              style={{
                backgroundColor: 'rgba(255,255,255,0.9)',
                borderRadius: 20,
                padding: 20,
                marginBottom: 24,
                borderWidth: 2,
                borderColor: isListening ? '#EC4899' : '#E5E7EB',
              }}
            >
              <Text
                style={{
                  fontFamily: fontFamily.nunito,
                  fontSize: 16,
                  color: '#374151',
                  lineHeight: 24,
                }}
              >
                {transcript}
              </Text>
            </View>
          )}

          {/* Error Display */}
          {error && (
            <View
              style={{
                backgroundColor: '#FEE2E2',
                borderRadius: 16,
                padding: 16,
                marginBottom: 20,
              }}
            >
              <Text style={{ fontFamily: fontFamily.nunitoBold, color: '#991B1B' }}>
                {error}
              </Text>
            </View>
          )}

          {/* Create Story Error */}
          {createStory.error && (
            <View
              style={{
                backgroundColor: '#FEE2E2',
                borderRadius: 16,
                padding: 16,
                marginBottom: 20,
              }}
            >
              <Text style={{ fontFamily: fontFamily.nunitoBold, color: '#991B1B' }}>
                Failed to create story
              </Text>
              <Text style={{ fontFamily: fontFamily.nunito, color: '#DC2626' }}>
                {createStory.error instanceof Error
                  ? createStory.error.message
                  : 'Unknown error'}
              </Text>
            </View>
          )}

          {/* Spacer to push button to bottom */}
          <View style={{ flex: 1 }} />

          {/* Create Button */}
          <Pressable
            onPress={handleCreate}
            disabled={!canCreate || createStory.isPending}
          >
            {({ pressed }) => (
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
                  transform: [{ scale: pressed ? 0.98 : 1 }],
                  opacity: pressed ? 0.9 : 1,
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
            )}
          </Pressable>

          {/* Switch to text input link */}
          <Pressable
            onPress={() => router.replace('/new')}
            style={{ marginTop: 16, alignItems: 'center', paddingBottom: insets.bottom }}
          >
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 14,
                color: '#7C3AED',
                textDecorationLine: 'underline',
              }}
            >
              Or type your idea instead
            </Text>
          </Pressable>
        </ScrollView>
      </View>
    </LinearGradient>
  );
}
