/**
 * Voice recording screen for creating stories via speech.
 *
 * Flow:
 * 1. idle - Tap mic to start recording
 * 2. recording - STT transcribes speech, stops on tap or 3s silence
 * 3. processing - LLM summarizes transcript into goal
 * 4. confirming - TTS speaks confirmation, user can create or re-record
 * 5. creating - Story creation in progress
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
import { useSTT, useTTS, STTTranscript } from '@/lib/voice';
import { api } from '@/lib/api';

type VoiceState = 'idle' | 'recording' | 'processing' | 'confirming' | 'creating';

const SILENCE_TIMEOUT_MS = 3000; // 3 seconds of silence triggers stop

// Animated microphone button
function MicButton({
  state,
  isSpeaking,
  onPress,
  disabled,
}: {
  state: VoiceState;
  isSpeaking: boolean;
  onPress: () => void;
  disabled: boolean;
}) {
  const pulse = useSharedValue(1);
  const ring = useSharedValue(0);
  const spin = useSharedValue(0);

  const isRecording = state === 'recording';
  const isProcessing = state === 'processing';
  const isConfirming = state === 'confirming';

  useEffect(() => {
    if (isRecording) {
      pulse.value = withRepeat(
        withSequence(
          withTiming(1.05, { duration: 800, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: 800, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      );
    } else if (isProcessing) {
      spin.value = withRepeat(
        withTiming(360, { duration: 1500, easing: Easing.linear }),
        -1,
        false
      );
    } else {
      cancelAnimation(pulse);
      cancelAnimation(spin);
      pulse.value = withSpring(1);
      spin.value = 0;
    }
  }, [isRecording, isProcessing, pulse, spin]);

  useEffect(() => {
    if (isSpeaking && isRecording) {
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
  }, [isSpeaking, isRecording, ring]);

  const micStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: pulse.value },
      { rotate: `${spin.value}deg` },
    ],
  }));

  const ringStyle = useAnimatedStyle(() => ({
    opacity: interpolate(ring.value, [0, 0.5, 1], [0.6, 0.3, 0]),
    transform: [{ scale: interpolate(ring.value, [0, 1], [1, 2]) }],
  }));

  const getColors = (): readonly [string, string] => {
    if (disabled) return ['#D1D5DB', '#9CA3AF'] as const;
    if (isRecording) return ['#EC4899', '#8B5CF6'] as const;
    if (isProcessing) return ['#F59E0B', '#D97706'] as const;
    if (isConfirming) return ['#10B981', '#059669'] as const;
    return ['#8B5CF6', '#6366F1'] as const;
  };

  const getEmoji = () => {
    if (isProcessing) return '🤔';
    if (isConfirming) return '🔊';
    if (isRecording) return '🎙️';
    return '🎤';
  };

  return (
    <Pressable onPress={onPress} disabled={disabled}>
      <View style={{ alignItems: 'center', justifyContent: 'center' }}>
        {isSpeaking && isRecording && (
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
            colors={getColors()}
            style={{
              width: 140,
              height: 140,
              borderRadius: 70,
              alignItems: 'center',
              justifyContent: 'center',
              shadowColor: isRecording ? '#EC4899' : '#8B5CF6',
              shadowOffset: { width: 0, height: 6 },
              shadowOpacity: 0.4,
              shadowRadius: 12,
              elevation: 10,
            }}
          >
            <Text style={{ fontSize: 56 }}>{getEmoji()}</Text>
          </LinearGradient>
        </Animated.View>
      </View>
    </Pressable>
  );
}

export default function NewVoiceStory() {
  const router = useRouter();
  const insets = useSafeAreaInsets();

  const [voiceState, setVoiceState] = useState<VoiceState>('idle');
  const [transcript, setTranscript] = useState('');
  const [extractedGoal, setExtractedGoal] = useState('');
  const [confirmationText, setConfirmationText] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const transcriptRef = useRef(''); // Accumulated final transcript text
  const interimRef = useRef(''); // Latest interim text (Fix 3: useRef to avoid re-renders)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  const createStory = useCreateStory();

  // TTS for speaking confirmation
  const tts = useTTS({
    onDone: () => {
      console.log('[Voice] TTS confirmation complete');
    },
    onError: (err) => {
      console.error('[Voice] TTS error:', err);
    },
  });

  // Handle transcript updates
  // Fix 2 (story-2irr): Debounce interim updates to 150ms
  // Fix 3 (story-hfrs): Use useRef for interim text to avoid re-renders
  const INTERIM_DEBOUNCE_MS = 150;

  const handleTranscript = useCallback((data: STTTranscript) => {
    if (data.isFinal) {
      // Final transcripts: update immediately
      const newText = transcriptRef.current
        ? `${transcriptRef.current} ${data.transcript}`
        : data.transcript;
      transcriptRef.current = newText;
      interimRef.current = ''; // Clear interim
      setTranscript(newText);

      // Clear any pending debounce
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }
    } else {
      // Interim transcripts: store in ref, debounce state updates
      interimRef.current = data.transcript;

      // Only set up debounce if not already pending
      if (!debounceTimerRef.current) {
        debounceTimerRef.current = setTimeout(() => {
          const displayText = transcriptRef.current
            ? `${transcriptRef.current} ${interimRef.current}`
            : interimRef.current;
          setTranscript(displayText);
          debounceTimerRef.current = null;
        }, INTERIM_DEBOUNCE_MS);
      }
    }
  }, []);

  // Process transcript through LLM
  const processTranscript = useCallback(async () => {
    const text = transcriptRef.current.trim();
    if (!text) {
      if (isMountedRef.current) {
        setError('No speech detected. Please try again.');
        setVoiceState('idle');
      }
      return;
    }

    if (isMountedRef.current) {
      setVoiceState('processing');
      setError(null);
    }

    try {
      console.log('[Voice] Summarizing transcript:', text.substring(0, 50) + '...');
      const result = await api.summarizeTranscript(text);

      if (!isMountedRef.current) return;

      setExtractedGoal(result.goal);
      setConfirmationText(result.summary);
      setVoiceState('confirming');

      // Speak the confirmation
      const ttsText = `${result.summary}. The story prompt will be: ${result.goal}. Tap Create My Story to continue, or tap the microphone to try again.`;
      await tts.speak(ttsText);

    } catch (err) {
      console.error('[Voice] Summarization failed:', err);
      if (isMountedRef.current) {
        setError('Failed to process your request. Please try again.');
        setVoiceState('idle');
      }
    }
  }, [tts]);

  // Handle silence timeout - process the transcript
  const handleSilenceTimeout = useCallback(async () => {
    console.log('[Voice] Silence timeout triggered');
    await processTranscript();
  }, [processTranscript]);

  // Handle errors - fallback to text input
  const handleError = useCallback((errorMsg: string) => {
    console.error('[Voice] STT error:', errorMsg);
    setError(errorMsg);
    setVoiceState('idle');
  }, []);

  const {
    status: sttStatus,
    startListening,
    stopListening,
    isListening,
  } = useSTT({
    onTranscript: handleTranscript,
    onSpeechStarted: () => setIsSpeaking(true),
    onUtteranceEnd: () => setIsSpeaking(false),
    onSilenceTimeout: handleSilenceTimeout,
    silenceTimeoutMs: SILENCE_TIMEOUT_MS,
    onError: handleError,
  });

  // Handle mic button press based on current state
  const handleMicPress = async () => {
    switch (voiceState) {
      case 'idle':
        // Start recording
        transcriptRef.current = '';
        interimRef.current = '';
        if (debounceTimerRef.current) {
          clearTimeout(debounceTimerRef.current);
          debounceTimerRef.current = null;
        }
        setTranscript('');
        setError(null);
        setVoiceState('recording');
        await startListening();
        break;

      case 'recording':
        // Stop recording and process
        await stopListening();
        await processTranscript();
        break;

      case 'confirming':
        // User wants to re-record
        tts.stop();
        setExtractedGoal('');
        setConfirmationText('');
        transcriptRef.current = '';
        interimRef.current = '';
        if (debounceTimerRef.current) {
          clearTimeout(debounceTimerRef.current);
          debounceTimerRef.current = null;
        }
        setTranscript('');
        setVoiceState('recording');
        await startListening();
        break;

      default:
        break;
    }
  };

  // Create story with extracted goal
  const handleCreate = async () => {
    if (!extractedGoal) return;

    setVoiceState('creating');
    tts.stop();

    try {
      const result = await createStory.mutateAsync({ goal: extractedGoal });
      router.replace(`/creating/${result.id}`);
    } catch (err) {
      console.error('[Voice] Failed to create story:', err);
      if (isMountedRef.current) {
        setError('Failed to create story. Please try again.');
        setVoiceState('confirming');
      }
    }
  };

  // Store refs for cleanup to avoid re-running effect on function changes
  const stopListeningRef = useRef(stopListening);
  const ttsRef = useRef(tts);
  stopListeningRef.current = stopListening;
  ttsRef.current = tts;

  // Cleanup on unmount only
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      stopListeningRef.current();
      ttsRef.current.stop();
      // Clean up debounce timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const isProcessing = voiceState === 'processing';
  const isConfirming = voiceState === 'confirming';
  const isCreating = voiceState === 'creating';
  const canCreate = isConfirming && extractedGoal.length > 0;

  const getStatusText = () => {
    switch (voiceState) {
      case 'idle':
        return 'Tap the mic and tell me your story idea';
      case 'recording':
        return isSpeaking ? '🔴 Listening...' : '⏳ Waiting for speech...';
      case 'processing':
        return '🤔 Processing your idea...';
      case 'confirming':
        return '✅ Review your story idea';
      case 'creating':
        return '✨ Creating your story...';
      default:
        return '';
    }
  };

  const getInstructionText = () => {
    switch (voiceState) {
      case 'idle':
        return 'For example: "A story about a brave dragon who learns to make friends"';
      case 'recording':
        return 'Tap the mic when done, or pause for 3 seconds';
      case 'processing':
        return 'Extracting your story idea...';
      case 'confirming':
        return 'Tap Create My Story to proceed, or tap the mic to try again';
      case 'creating':
        return 'Please wait...';
      default:
        return '';
    }
  };

  return (
    <LinearGradient
      colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']}
      style={{ flex: 1 }}
    >
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
              disabled={isCreating}
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

          {/* Status Card */}
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
              {getStatusText()}
            </Text>
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 14,
                color: '#6B7280',
                textAlign: 'center',
              }}
            >
              {getInstructionText()}
            </Text>
          </View>

          {/* Microphone Button */}
          <View style={{ alignItems: 'center', marginVertical: 32 }}>
            <MicButton
              state={voiceState}
              isSpeaking={isSpeaking}
              onPress={handleMicPress}
              disabled={isProcessing || isCreating || sttStatus === 'connecting'}
            />

            {sttStatus === 'connecting' && (
              <View style={{ marginTop: 16, flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <ActivityIndicator size="small" color="#7C3AED" />
                <Text style={{ fontFamily: fontFamily.nunito, color: '#7C3AED' }}>
                  Connecting...
                </Text>
              </View>
            )}
          </View>

          {/* Transcript Display (during recording) */}
          {(voiceState === 'recording' || voiceState === 'processing') && transcript.length > 0 && (
            <View
              style={{
                backgroundColor: 'rgba(255,255,255,0.9)',
                borderRadius: 20,
                padding: 20,
                marginBottom: 24,
                borderWidth: 2,
                borderColor: voiceState === 'recording' ? '#EC4899' : '#F59E0B',
              }}
            >
              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  fontSize: 12,
                  color: '#9CA3AF',
                  marginBottom: 8,
                  textTransform: 'uppercase',
                }}
              >
                What I heard:
              </Text>
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

          {/* Confirmation Display */}
          {isConfirming && (
            <View
              style={{
                backgroundColor: 'rgba(255,255,255,0.95)',
                borderRadius: 20,
                padding: 20,
                marginBottom: 24,
                borderWidth: 2,
                borderColor: '#10B981',
              }}
            >
              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  fontSize: 12,
                  color: '#059669',
                  marginBottom: 8,
                  textTransform: 'uppercase',
                }}
              >
                Story Summary:
              </Text>
              <Text
                style={{
                  fontFamily: fontFamily.nunito,
                  fontSize: 16,
                  color: '#374151',
                  lineHeight: 24,
                  marginBottom: 16,
                }}
              >
                {confirmationText}
              </Text>

              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  fontSize: 12,
                  color: '#7C3AED',
                  marginBottom: 8,
                  textTransform: 'uppercase',
                }}
              >
                Story Prompt:
              </Text>
              <Text
                style={{
                  fontFamily: fontFamily.nunito,
                  fontSize: 14,
                  color: '#6B7280',
                  lineHeight: 22,
                  fontStyle: 'italic',
                }}
              >
                "{extractedGoal}"
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

          <View style={{ flex: 1 }} />

          {/* Create Button (only in confirming state) */}
          {isConfirming && (
            <Pressable onPress={handleCreate} disabled={!canCreate || isCreating}>
              {({ pressed }) => (
                <LinearGradient
                  colors={canCreate ? ['#EC4899', '#8B5CF6', '#6366F1'] : ['#D1D5DB', '#9CA3AF', '#9CA3AF']}
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
                </LinearGradient>
              )}
            </Pressable>
          )}

          {/* Creating indicator */}
          {isCreating && (
            <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
              <ActivityIndicator size="large" color="#7C3AED" />
              <Text style={{ fontFamily: fontFamily.nunitoBold, fontSize: 16, color: '#7C3AED' }}>
                Creating your story...
              </Text>
            </View>
          )}

          {/* Switch to text input link */}
          <Pressable
            onPress={() => router.replace('/new')}
            disabled={isCreating}
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
