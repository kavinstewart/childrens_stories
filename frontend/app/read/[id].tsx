import { View, Text, Pressable, Image, ActivityIndicator, Dimensions } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { useStory } from '@/features/stories/hooks';
import { api } from '@/lib/api';
import { fontFamily } from '@/lib/fonts';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

export default function StoryReader() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: story, isLoading, error } = useStory(id);
  const [currentSpread, setCurrentSpread] = useState(0);

  // Use spreads (new format) or fall back to pages (backwards compatibility)
  const spreads = story?.spreads || story?.pages || [];
  const totalSpreads = spreads.length;

  const goBack = () => setCurrentSpread(Math.max(0, currentSpread - 1));
  const goForward = () => setCurrentSpread(Math.min(totalSpreads - 1, currentSpread + 1));

  if (isLoading) {
    return (
      <View style={{ flex: 1, backgroundColor: '#1a1a2e', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator size="large" color="#FBBF24" />
        <Text style={{ color: 'white', marginTop: 16, fontFamily: fontFamily.nunito }}>
          Loading story...
        </Text>
      </View>
    );
  }

  if (error || !story) {
    return (
      <View style={{ flex: 1, backgroundColor: '#1a1a2e', alignItems: 'center', justifyContent: 'center' }}>
        <Text style={{ fontSize: 64, marginBottom: 16 }}>😕</Text>
        <Text style={{ color: 'white', fontSize: 20, fontFamily: fontFamily.nunitoBold, marginBottom: 16 }}>
          Couldn't load story
        </Text>
        <Pressable
          onPress={() => router.back()}
          style={{ backgroundColor: '#8B5CF6', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 16 }}
        >
          <Text style={{ color: 'white', fontFamily: fontFamily.nunitoBold }}>Go Back</Text>
        </Pressable>
      </View>
    );
  }

  const currentSpreadData = spreads[currentSpread];

  // Get image URL for current spread if it has an illustration
  const imageUrl = story.is_illustrated && currentSpreadData
    ? api.getSpreadImageUrl(story.id, currentSpreadData.spread_number)
    : null;

  const isFirstSpread = currentSpread === 0;
  const isLastSpread = currentSpread >= totalSpreads - 1;
  const progressPercent = totalSpreads > 0 ? ((currentSpread + 1) / totalSpreads) * 100 : 0;

  return (
    <View style={{ flex: 1, backgroundColor: '#1a1a2e' }}>
      {/* Full-bleed Illustration */}
      {imageUrl ? (
        <Image
          source={{ uri: imageUrl }}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            width: SCREEN_WIDTH,
            height: SCREEN_HEIGHT,
          }}
          resizeMode="cover"
        />
      ) : (
        <View style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: '#2d1f1a',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <Text style={{ fontSize: 80 }}>📖</Text>
          <Text style={{ color: 'rgba(255,255,255,0.6)', marginTop: 16, fontFamily: fontFamily.nunito }}>
            {story.is_illustrated ? 'Illustration loading...' : 'Text-only story'}
          </Text>
        </View>
      )}

      {/* Dark gradient overlay at bottom for text */}
      <LinearGradient
        colors={['transparent', 'rgba(30, 20, 10, 0.3)', 'rgba(30, 20, 10, 0.85)', 'rgba(30, 20, 10, 0.95)']}
        locations={[0, 0.25, 0.6, 1]}
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '45%',
        }}
      />

      {/* Top gradient for header */}
      <LinearGradient
        colors={['rgba(0,0,0,0.4)', 'transparent']}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 100,
        }}
      />

      {/* Tap zones for gesture navigation */}
      <Pressable
        onPress={goBack}
        disabled={isFirstSpread}
        style={{
          position: 'absolute',
          top: 100,
          left: 0,
          width: '25%',
          height: SCREEN_HEIGHT - 220,
        }}
      />
      <Pressable
        onPress={goForward}
        disabled={isLastSpread}
        style={{
          position: 'absolute',
          top: 100,
          right: 0,
          width: '25%',
          height: SCREEN_HEIGHT - 220,
        }}
      />

      {/* Top Bar */}
      <View style={{
        position: 'absolute',
        top: 48,
        left: 32,
        right: 32,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Library Button */}
        <Pressable
          onPress={() => router.back()}
          style={({ pressed }) => ({
            backgroundColor: 'rgba(255,255,255,0.85)',
            paddingVertical: 14,
            paddingHorizontal: 22,
            borderRadius: 16,
            flexDirection: 'row',
            alignItems: 'center',
            gap: 8,
            opacity: pressed ? 0.8 : 1,
          })}
        >
          <Text style={{ fontSize: 20 }}>←</Text>
          <Text style={{ fontSize: 18, fontFamily: fontFamily.nunitoBold, color: '#374151' }}>
            Library
          </Text>
        </Pressable>

        {/* Progress Indicator */}
        <View style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 16,
          backgroundColor: 'rgba(255,255,255,0.2)',
          paddingVertical: 12,
          paddingHorizontal: 24,
          borderRadius: 20,
        }}>
          <View style={{
            width: 180,
            height: 8,
            backgroundColor: 'rgba(255,255,255,0.3)',
            borderRadius: 4,
            overflow: 'hidden',
          }}>
            <LinearGradient
              colors={['#FBBF24', '#F97316']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={{
                width: `${progressPercent}%`,
                height: '100%',
                borderRadius: 4,
              }}
            />
          </View>
          <Text style={{
            color: 'white',
            fontFamily: fontFamily.nunitoBold,
            fontSize: 16,
            textShadowColor: 'rgba(0,0,0,0.3)',
            textShadowOffset: { width: 0, height: 1 },
            textShadowRadius: 4,
          }}>
            {currentSpread + 1} / {totalSpreads}
          </Text>
        </View>

        {/* Settings Button */}
        <Pressable
          style={({ pressed }) => ({
            backgroundColor: 'rgba(255,255,255,0.85)',
            padding: 14,
            borderRadius: 16,
            opacity: pressed ? 0.8 : 1,
          })}
        >
          <Text style={{ fontSize: 20 }}>⚙️</Text>
        </Pressable>
      </View>

      {/* Story Text */}
      <View style={{
        position: 'absolute',
        bottom: 140,
        left: 100,
        right: 100,
      }}>
        {currentSpreadData ? (
          <Text style={{
            fontSize: 26,
            lineHeight: 40,
            color: 'white',
            textAlign: 'center',
            fontFamily: fontFamily.nunitoSemiBold,
            textShadowColor: 'rgba(0,0,0,0.5)',
            textShadowOffset: { width: 0, height: 2 },
            textShadowRadius: 8,
            maxWidth: 900,
            alignSelf: 'center',
          }}>
            {currentSpreadData.text}
          </Text>
        ) : (
          <Text style={{
            fontSize: 20,
            color: 'rgba(255,255,255,0.6)',
            textAlign: 'center',
            fontFamily: fontFamily.nunito,
            fontStyle: 'italic',
          }}>
            No content for this spread
          </Text>
        )}
      </View>

      {/* Navigation Buttons */}
      <View style={{
        position: 'absolute',
        bottom: 100,
        left: 40,
        right: 40,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Back Button */}
        <Pressable
          onPress={goBack}
          disabled={isFirstSpread}
          style={({ pressed }) => ({
            backgroundColor: 'rgba(255,255,255,0.25)',
            paddingVertical: 18,
            paddingHorizontal: 30,
            borderRadius: 22,
            borderWidth: 2,
            borderColor: 'rgba(255,255,255,0.35)',
            flexDirection: 'row',
            alignItems: 'center',
            gap: 12,
            opacity: isFirstSpread ? 0.5 : pressed ? 0.8 : 1,
          })}
        >
          <Text style={{ fontSize: 26 }}>👈</Text>
          <Text style={{
            fontSize: 20,
            fontFamily: fontFamily.nunitoExtraBold,
            color: isFirstSpread ? 'rgba(255,255,255,0.45)' : 'white',
          }}>
            Back
          </Text>
        </Pressable>

        {/* Next Button */}
        <Pressable
          onPress={goForward}
          disabled={isLastSpread}
          style={({ pressed }) => ({
            opacity: isLastSpread ? 0.5 : pressed ? 0.9 : 1,
            transform: [{ scale: pressed ? 0.98 : 1 }],
          })}
        >
          <LinearGradient
            colors={['#EC4899', '#8B5CF6']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={{
              paddingVertical: 18,
              paddingHorizontal: 36,
              borderRadius: 22,
              flexDirection: 'row',
              alignItems: 'center',
              gap: 12,
              shadowColor: '#8B5CF6',
              shadowOffset: { width: 0, height: 8 },
              shadowOpacity: 0.5,
              shadowRadius: 16,
              elevation: 8,
            }}
          >
            <Text style={{
              fontSize: 20,
              fontFamily: fontFamily.nunitoExtraBold,
              color: 'white',
            }}>
              Next
            </Text>
            <Text style={{ fontSize: 26 }}>👉</Text>
          </LinearGradient>
        </Pressable>
      </View>
    </View>
  );
}
