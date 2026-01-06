/**
 * Voice-based story creation screen using Hume EVI
 *
 * Primary story creation flow where users speak to an AI assistant
 * to describe what story they want to create.
 */

import { View, Text, ScrollView, Pressable, Platform } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useCallback, useEffect, useState } from 'react';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  Easing,
  cancelAnimation,
} from 'react-native-reanimated';
import Constants from 'expo-constants';

import { fontFamily } from '@/lib/fonts';
import { FloatingElement } from '@/components/animations';
import { api } from '@/lib/api';
import {
  useEviChat,
  STORY_CREATOR_SESSION_SETTINGS,
  type ToolCall,
  type ChatMessage,
} from '@/lib/hume';

// EVI config ID from environment
const EVI_CONFIG_ID = Constants.expoConfig?.extra?.humeConfigId || process.env.EXPO_PUBLIC_HUME_CONFIG_ID || '';

// Pulsing animation for the listening indicator
function PulsingCircle({ isActive }: { isActive: boolean }) {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.5);

  useEffect(() => {
    if (isActive) {
      scale.value = withRepeat(
        withTiming(1.3, { duration: 1000, easing: Easing.inOut(Easing.ease) }),
        -1,
        true
      );
      opacity.value = withRepeat(
        withTiming(0.2, { duration: 1000, easing: Easing.inOut(Easing.ease) }),
        -1,
        true
      );
    } else {
      cancelAnimation(scale);
      cancelAnimation(opacity);
      scale.value = withTiming(1, { duration: 200 });
      opacity.value = withTiming(0.5, { duration: 200 });
    }
  }, [isActive, scale, opacity]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  return (
    <View style={{ alignItems: 'center', justifyContent: 'center', marginVertical: 32 }}>
      <Animated.View
        style={[
          {
            position: 'absolute',
            width: 120,
            height: 120,
            borderRadius: 60,
            backgroundColor: isActive ? '#8B5CF6' : '#9CA3AF',
          },
          animatedStyle,
        ]}
      />
      <View
        style={{
          width: 80,
          height: 80,
          borderRadius: 40,
          backgroundColor: isActive ? '#7C3AED' : '#6B7280',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Text style={{ fontSize: 32 }}>{isActive ? '🎤' : '🔇'}</Text>
      </View>
    </View>
  );
}

// Chat message bubble
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <View
      style={{
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        maxWidth: '80%',
        marginVertical: 4,
      }}
    >
      <View
        style={{
          backgroundColor: isUser ? '#7C3AED' : 'rgba(255,255,255,0.9)',
          borderRadius: 16,
          paddingHorizontal: 16,
          paddingVertical: 10,
          borderBottomRightRadius: isUser ? 4 : 16,
          borderBottomLeftRadius: isUser ? 16 : 4,
        }}
      >
        <Text
          style={{
            fontFamily: fontFamily.nunito,
            fontSize: 16,
            color: isUser ? 'white' : '#374151',
          }}
        >
          {message.content}
        </Text>
      </View>
    </View>
  );
}

export default function NewVoiceStory() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [isCreating, setIsCreating] = useState(false);

  // Handle tool calls from EVI
  const handleToolCall = useCallback(
    async (toolCall: ToolCall): Promise<string> => {
      if (toolCall.name === 'create_story') {
        const goal = toolCall.parameters.goal as string;

        if (!goal) {
          return JSON.stringify({ error: 'No goal provided' });
        }

        setIsCreating(true);

        try {
          const result = await api.createStory({ goal });
          // Navigate to creating screen after returning response
          setTimeout(() => {
            router.replace(`/creating/${result.id}`);
          }, 500);
          return JSON.stringify({ success: true, story_id: result.id });
        } catch (error) {
          setIsCreating(false);
          return JSON.stringify({
            error: error instanceof Error ? error.message : 'Failed to create story',
          });
        }
      }

      return JSON.stringify({ error: 'Unknown tool' });
    },
    [router]
  );

  const {
    status,
    error,
    messages,
    connect,
    disconnect,
    mute,
    unmute,
    isMuted,
  } = useEviChat({
    configId: EVI_CONFIG_ID,
    onToolCall: handleToolCall,
    sessionSettings: STORY_CREATOR_SESSION_SETTINGS,
  });

  const isConnected = status === 'connected';
  const isConnecting = status === 'connecting';

  // Auto-connect on mount if on supported platform
  useEffect(() => {
    if (Platform.OS === 'ios' || Platform.OS === 'web') {
      connect();
    }
  }, [connect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Navigate to text input if not on supported platform
  const handleSwitchToText = () => {
    disconnect();
    router.replace('/new');
  };

  // Show unsupported platform message
  if (Platform.OS !== 'ios' && Platform.OS !== 'web') {
    return (
      <LinearGradient colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']} style={{ flex: 1 }}>
        <View
          style={{
            flex: 1,
            paddingTop: insets.top,
            paddingLeft: insets.left,
            paddingRight: insets.right,
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
          }}
        >
          <Text style={{ fontSize: 48, marginBottom: 16 }}>🎤</Text>
          <Text
            style={{
              fontFamily: fontFamily.baloo,
              fontSize: 24,
              color: '#7C3AED',
              textAlign: 'center',
              marginBottom: 12,
            }}
          >
            Voice Not Available
          </Text>
          <Text
            style={{
              fontFamily: fontFamily.nunito,
              fontSize: 16,
              color: '#6B7280',
              textAlign: 'center',
              marginBottom: 24,
            }}
          >
            Voice story creation is only available on iOS devices.
          </Text>
          <Pressable onPress={handleSwitchToText}>
            <LinearGradient
              colors={['#EC4899', '#8B5CF6']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={{
                paddingHorizontal: 24,
                paddingVertical: 14,
                borderRadius: 12,
              }}
            >
              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  fontSize: 16,
                  color: 'white',
                }}
              >
                Use Text Instead
              </Text>
            </LinearGradient>
          </Pressable>
        </View>
      </LinearGradient>
    );
  }

  return (
    <LinearGradient colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']} style={{ flex: 1 }}>
      {/* Floating decorations */}
      <FloatingElement delay={0} duration={4} style={{ top: 80, left: 24 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>✨</Text>
      </FloatingElement>
      <FloatingElement delay={1} duration={5} style={{ top: 128, right: 32 }}>
        <Text style={{ fontSize: 20, opacity: 0.25 }}>🎤</Text>
      </FloatingElement>
      <FloatingElement delay={2} duration={4.5} style={{ bottom: 128, right: 48 }}>
        <Text style={{ fontSize: 24, opacity: 0.3 }}>🌈</Text>
      </FloatingElement>

      <View
        style={{
          flex: 1,
          paddingTop: insets.top,
          paddingLeft: insets.left,
          paddingRight: insets.right,
        }}
      >
        {/* Header */}
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            padding: 16,
          }}
        >
          <Pressable
            onPress={() => {
              disconnect();
              router.back();
            }}
            style={{
              backgroundColor: 'rgba(255,255,255,0.7)',
              padding: 12,
              borderRadius: 12,
              marginRight: 16,
            }}
          >
            <Text style={{ fontSize: 20 }}>←</Text>
          </Pressable>
          <Text style={{ fontSize: 24, marginRight: 8 }}>🎤</Text>
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

        {/* Status indicator */}
        <View style={{ alignItems: 'center', paddingHorizontal: 24 }}>
          <PulsingCircle isActive={isConnected && !isMuted && !isCreating} />

          <Text
            style={{
              fontFamily: fontFamily.nunitoBold,
              fontSize: 18,
              color: '#374151',
              textAlign: 'center',
            }}
          >
            {isCreating
              ? 'Creating your story...'
              : isConnecting
                ? 'Connecting...'
                : isConnected
                  ? isMuted
                    ? 'Microphone muted'
                    : 'Listening...'
                  : error
                    ? 'Connection failed'
                    : 'Disconnected'}
          </Text>

          {error && (
            <Text
              style={{
                fontFamily: fontFamily.nunito,
                fontSize: 14,
                color: '#DC2626',
                textAlign: 'center',
                marginTop: 8,
              }}
            >
              {error.message}
            </Text>
          )}
        </View>

        {/* Chat messages */}
        <ScrollView
          style={{ flex: 1, marginTop: 16 }}
          contentContainerStyle={{ padding: 16 }}
        >
          {messages.length === 0 && isConnected && !isCreating && (
            <View style={{ alignItems: 'center', paddingVertical: 24 }}>
              <Text
                style={{
                  fontFamily: fontFamily.nunito,
                  fontSize: 16,
                  color: '#9CA3AF',
                  textAlign: 'center',
                }}
              >
                Tell me what kind of story you'd like to create!
              </Text>
            </View>
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </ScrollView>

        {/* Bottom controls */}
        <View
          style={{
            flexDirection: 'row',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 16,
            padding: 24,
            paddingBottom: insets.bottom + 24,
          }}
        >
          {/* Mute/Unmute button */}
          {isConnected && !isCreating && (
            <Pressable
              onPress={isMuted ? unmute : mute}
              style={{
                backgroundColor: isMuted ? '#DC2626' : 'rgba(255,255,255,0.8)',
                width: 56,
                height: 56,
                borderRadius: 28,
                alignItems: 'center',
                justifyContent: 'center',
                shadowColor: '#000',
                shadowOffset: { width: 0, height: 2 },
                shadowOpacity: 0.1,
                shadowRadius: 4,
              }}
            >
              <Text style={{ fontSize: 24 }}>{isMuted ? '🔇' : '🎤'}</Text>
            </Pressable>
          )}

          {/* Type instead button */}
          <Pressable
            onPress={handleSwitchToText}
            style={{
              backgroundColor: 'rgba(255,255,255,0.8)',
              paddingHorizontal: 20,
              paddingVertical: 14,
              borderRadius: 12,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 8,
            }}
          >
            <Text style={{ fontSize: 18 }}>⌨️</Text>
            <Text
              style={{
                fontFamily: fontFamily.nunitoBold,
                fontSize: 16,
                color: '#6B7280',
              }}
            >
              Type instead
            </Text>
          </Pressable>

          {/* Reconnect button if disconnected */}
          {status === 'error' && (
            <Pressable
              onPress={connect}
              style={{
                backgroundColor: '#7C3AED',
                paddingHorizontal: 20,
                paddingVertical: 14,
                borderRadius: 12,
              }}
            >
              <Text
                style={{
                  fontFamily: fontFamily.nunitoBold,
                  fontSize: 16,
                  color: 'white',
                }}
              >
                Try Again
              </Text>
            </Pressable>
          )}
        </View>
      </View>
    </LinearGradient>
  );
}
