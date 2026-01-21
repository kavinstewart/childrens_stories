import { View, Text, TextInput, ActivityIndicator, Pressable, Alert } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState, useRef, useEffect } from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import * as Haptics from 'expo-haptics';
import { fontFamily } from '@/lib/fonts';
import { useRegenerateSpread, useDeleteStory, useStory, storyKeys } from '@/features/stories/hooks';
import { api } from '@/lib/api';
import { useQueryClient } from '@tanstack/react-query';
import { StoryCacheManager } from '@/lib/story-cache';

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
  const deleteStory = useDeleteStory();
  const { data: story } = useStory(storyId);
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

      // Poll the job status endpoint for completion/failure
      pollIntervalRef.current = setInterval(async () => {
        if (!isMountedRef.current) return;

        try {
          const status = await api.getRegenerateStatus(storyId, spreadNumber);

          if (status.status === 'running') {
            setStatusMessage('Generating new illustration...');
          } else if (status.status === 'completed') {
            // Success! Clean up and navigate back
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (timeoutRef.current) clearTimeout(timeoutRef.current);

            // Refresh story data to get new illustration
            const story = await api.getStory(storyId);
            queryClient.setQueryData(storyKeys.detail(storyId), story);

            // Invalidate offline cache so it re-downloads the new illustration
            await StoryCacheManager.invalidateStory(storyId);

            // Haptic feedback for success
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

            if (isMountedRef.current) {
              setIsRegenerating(false);
              router.back();
            }
          } else if (status.status === 'failed') {
            // Job failed - show the actual error message
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            if (timeoutRef.current) clearTimeout(timeoutRef.current);

            const errorMsg = status.error_message
              ? formatErrorMessage(status.error_message)
              : 'Regeneration failed. Please try again.';

            setError(errorMsg);
            setIsRegenerating(false);
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
          }
          // 'pending' status - just keep polling
        } catch {
          // Ignore polling errors, will retry
        }
      }, POLL_INTERVAL_MS);

      // Set timeout as a fallback (in case polling never returns completed/failed)
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

  // Format server error messages for user display
  const formatErrorMessage = (msg: string): string => {
    if (msg.includes('503') || msg.includes('UNAVAILABLE') || msg.includes('overloaded')) {
      return 'Image service is temporarily busy. Please try again in a few minutes.';
    }
    if (msg.includes('429') || msg.includes('RESOURCE_EXHAUSTED') || msg.includes('rate limit')) {
      return 'Too many requests. Please wait a moment and try again.';
    }
    if (msg.includes('timeout') || msg.includes('timed out')) {
      return 'Request timed out. Please try again.';
    }
    // For other errors, show a generic message
    return 'Regeneration failed. Please try again.';
  };

  const handleCancel = () => {
    router.back();
  };

  const handleReset = () => {
    setPrompt(initialPrompt);
  };

  const handleDelete = () => {
    const storyTitle = story?.title || 'this story';
    Alert.alert(
      `Delete '${storyTitle}'?`,
      'This will permanently delete the story and all illustrations.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            if (!storyId) return;
            try {
              await deleteStory.mutateAsync(storyId);
              await StoryCacheManager.invalidateStory(storyId);
              router.replace('/');
            } catch (err) {
              Alert.alert('Error', 'Failed to delete story. Please try again.');
            }
          },
        },
      ]
    );
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

        {isRegenerating ? (
          <View style={{ width: 50 }} />
        ) : hasChanges ? (
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
          <Pressable onPress={handleDelete}>
            <Text
              style={{
                color: '#DC2626',
                fontSize: 17,
                fontFamily: fontFamily.nunitoSemiBold,
              }}
            >
              Delete
            </Text>
          </Pressable>
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
                <Pressable
                  onPress={handleRegenerate}
                  style={({ pressed }) => ({
                    backgroundColor: pressed ? 'rgba(239, 68, 68, 0.4)' : 'rgba(239, 68, 68, 0.3)',
                    borderRadius: 8,
                    paddingVertical: 10,
                    paddingHorizontal: 20,
                    marginTop: 12,
                    alignSelf: 'center',
                  })}
                >
                  <Text
                    style={{
                      color: '#FCA5A5',
                      fontSize: 14,
                      fontFamily: fontFamily.nunitoSemiBold,
                    }}
                  >
                    Retry
                  </Text>
                </Pressable>
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
