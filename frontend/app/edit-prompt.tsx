import { View, Text, TextInput, Pressable, ScrollView, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { fontFamily } from '@/lib/fonts';
import { useRegenerateSpread } from '@/features/stories/hooks';

export default function EditPromptScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const params = useLocalSearchParams<{
    storyId: string;
    spreadNumber: string;
    composedPrompt: string;
  }>();

  const storyId = params.storyId;
  const spreadNumber = parseInt(params.spreadNumber || '1', 10);
  const initialPrompt = params.composedPrompt || '';

  const [prompt, setPrompt] = useState(initialPrompt);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const regenerateSpread = useRegenerateSpread();

  const hasChanges = prompt !== initialPrompt;

  const handleRegenerate = () => {
    if (!storyId) return;

    setIsRegenerating(true);
    regenerateSpread.mutate(
      {
        storyId,
        spreadNumber,
        prompt,
      },
      {
        onSuccess: () => {
          router.back();
        },
        onError: () => {
          setIsRegenerating(false);
        },
      }
    );
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
            Regenerating illustration...
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
            This may take a moment.{'\n'}You'll be returned to the story when complete.
          </Text>
        </View>
      ) : (
        <>
          <ScrollView
            style={{ flex: 1 }}
            contentContainerStyle={{ padding: 24 }}
            keyboardShouldPersistTaps="handled"
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
          </ScrollView>

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
