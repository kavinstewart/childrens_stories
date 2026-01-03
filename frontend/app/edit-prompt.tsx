import { View, Text, TextInput, Pressable, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState, useRef, useEffect } from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import * as Haptics from 'expo-haptics';
import { fontFamily } from '@/lib/fonts';
import { useRegenerateSpread, storyKeys } from '@/features/stories/hooks';
import { api } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';

const POLL_INTERVAL_MS = 2000;
const TIMEOUT_MS = 90000; // 90 seconds for image generation

export default function EditPromptScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const params = useLocalSearchParams<{
    storyId: string;
    spreadNumber: string;
    composedPrompt: string;
    illustrationUpdatedAt: string;
  }>();

  const storyId = params.storyId;
  const spreadNumber = parseInt(params.spreadNumber || '1', 10);
  const initialPrompt = params.composedPrompt || '';
  const originalUpdatedAt = useRef(params.illustrationUpdatedAt || '');

  const [prompt, setPrompt] = useState(initialPrompt);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState('Regenerating illustration...');
  const regenerateSpread = useRegenerateSpread();
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const hasChanges = prompt !== initialPrompt;
  const isMountedRef = useRef(true);

  // Cleanup polling on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const handleRegenerate = async () => {
    if (!storyId) return;

    setIsRegenerating(true);
    setError(null);
    setStatusMessage('Starting regeneration...');

    try {
      await regenerateSpread.mutateAsync({
        storyId,
        spreadNumber,
        prompt,
      });

      setStatusMessage('Generating new illustration...');

      // Start polling for completion
      // Note: We poll for illustration_updated_at changes rather than job status
      // because there's no job status endpoint. Job failures result in timeout.
      pollIntervalRef.current = setInterval(async () => {
        if (!isMountedRef.current) return;

        try {
          const story = await api.getStory(storyId);
          const spread = story.spreads?.find(s => s.spread_number === spreadNumber);

          if (spread?.illustration_updated_at &&
              spread.illustration_updated_at !== originalUpdatedAt.current) {
            // Image was regenerated!
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (timeoutRef.current) clearTimeout(timeoutRef.current);

            // Update cache with fresh data
            queryClient.setQueryData(storyKeys.detail(storyId), story);

            // Haptic feedback for success
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

            if (isMountedRef.current) {
              setIsRegenerating(false);
              router.back();
            }
          }
        } catch {
          // Ignore polling errors, will retry
        }
      }, POLL_INTERVAL_MS);

      // Set timeout for job failures (no job status endpoint to check)
      timeoutRef.current = setTimeout(() => {
        if (!isMountedRef.current) return;
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        setError('Regeneration timed out. Please try again.');
        setIsRegenerating(false);
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }, TIMEOUT_MS);

    } catch {
      setError('Failed to start regeneration. Please try again.');
      setIsRegenerating(false);
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    }
  };

  const handleCancel = () => {
    router.back();
  };

  const handleReset = () => {
    setPrompt(initialPrompt);
  };

  return (
    <View
      style={{
        flex: 1,
        backgroundColor: '#1a1a2e',
        paddingTop: insets.top,
        paddingBottom: insets.bottom,
      }}
    >
      {/* Header */}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingHorizontal: 24,
          paddingVertical: 16,
          borderBottomWidth: 1,
          borderBottomColor: 'rgba(255,255,255,0.1)',
        }}
      >
        <Pressable
          onPress={handleCancel}
          disabled={isRegenerating}
          style={{ opacity: isRegenerating ? 0.5 : 1 }}
        >
          <Text
            style={{
              color: 'rgba(255,255,255,0.7)',
              fontSize: 17,
              fontFamily: fontFamily.nunito,
            }}
          >
            Cancel
          </Text>
        </Pressable>

        <Text
          style={{
            color: 'white',
            fontSize: 18,
            fontFamily: fontFamily.nunitoBold,
          }}
        >
          Edit Prompt - Spread {spreadNumber}
        </Text>

        {hasChanges && !isRegenerating ? (
          <Pressable onPress={handleReset}>
            <Text
              style={{
                color: '#FBBF24',
                fontSize: 17,
                fontFamily: fontFamily.nunitoSemiBold,
              }}
            >
              Reset
            </Text>
          </Pressable>
        ) : (
          <View style={{ width: 50 }} />
        )}
      </View>

      {/* Content */}
      {isRegenerating ? (
        <View
          style={{
            flex: 1,
            alignItems: 'center',
            justifyContent: 'center',
            paddingHorizontal: 24,
          }}
        >
          <ActivityIndicator size="large" color="#FBBF24" />
          <Text
            style={{
              color: 'white',
              fontSize: 20,
              fontFamily: fontFamily.nunitoSemiBold,
              marginTop: 24,
            }}
          >
            {statusMessage}
          </Text>
          <Text
            style={{
              color: 'rgba(255,255,255,0.6)',
              fontSize: 16,
              fontFamily: fontFamily.nunito,
              marginTop: 8,
              textAlign: 'center',
            }}
          >
            This may take up to a minute.{'\n'}You'll be returned to the story when complete.
          </Text>
        </View>
      ) : (
        <>
          <KeyboardAwareScrollView
            style={{ flex: 1 }}
            contentContainerStyle={{ padding: 24 }}
            keyboardShouldPersistTaps="handled"
            extraScrollHeight={100}
            enableOnAndroid={true}
          >
            <Text
              style={{
                color: 'rgba(255,255,255,0.7)',
                fontSize: 14,
                fontFamily: fontFamily.nunitoSemiBold,
                marginBottom: 12,
              }}
            >
              Full Prompt (sent to image model)
            </Text>

            <TextInput
              value={prompt}
              onChangeText={setPrompt}
              multiline
              autoFocus
              style={{
                backgroundColor: '#FAF7F2',
                borderRadius: 16,
                padding: 20,
                fontSize: 16,
                fontFamily: fontFamily.nunito,
                color: '#374151',
                minHeight: 300,
                textAlignVertical: 'top',
              }}
            />

            <Text
              style={{
                color: 'rgba(255,255,255,0.5)',
                fontSize: 13,
                fontFamily: fontFamily.nunito,
                marginTop: 16,
                lineHeight: 20,
              }}
            >
              Edit the prompt above to experiment with different styles, scenes, or
              instructions. Character reference images will still be included
              automatically.
            </Text>

            {error && (
              <View
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.2)',
                  borderRadius: 12,
                  padding: 16,
                  marginTop: 16,
                }}
              >
                <Text
                  style={{
                    color: '#FCA5A5',
                    fontSize: 14,
                    fontFamily: fontFamily.nunitoSemiBold,
                    textAlign: 'center',
                  }}
                >
                  {error}
                </Text>
              </View>
            )}
          </KeyboardAwareScrollView>

          {/* Bottom Action Bar */}
          <View
            style={{
              paddingHorizontal: 24,
              paddingVertical: 16,
              borderTopWidth: 1,
              borderTopColor: 'rgba(255,255,255,0.1)',
            }}
          >
            <Pressable
              onPress={handleRegenerate}
              style={({ pressed }) => ({
                opacity: pressed ? 0.9 : 1,
                transform: [{ scale: pressed ? 0.98 : 1 }],
              })}
            >
              <LinearGradient
                colors={['#FBBF24', '#F97316']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={{
                  paddingVertical: 18,
                  paddingHorizontal: 32,
                  borderRadius: 16,
                  flexDirection: 'row',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 12,
                }}
              >
                <Text style={{ fontSize: 22 }}>🔄</Text>
                <Text
                  style={{
                    color: 'white',
                    fontSize: 18,
                    fontFamily: fontFamily.nunitoBold,
                  }}
                >
                  Regenerate Illustration
                </Text>
              </LinearGradient>
            </Pressable>
          </View>
        </>
      )}
    </View>
  );
}
