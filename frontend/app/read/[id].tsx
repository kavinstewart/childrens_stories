import { View, Text, Pressable, Image, ActivityIndicator, Dimensions, Animated } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useState, useEffect, useRef } from 'react';
import { useStory } from '@/features/stories/hooks';
import { api } from '@/lib/api';
import { fontFamily } from '@/lib/fonts';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

export default function StoryReader() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: story, isLoading, error } = useStory(id);
  const [currentSpread, setCurrentSpread] = useState(0);
  const [endButtonsActive, setEndButtonsActive] = useState(false);

  // Animation values for "The End" text
  const theEndOpacity = useRef(new Animated.Value(0)).current;
  const theEndScale = useRef(new Animated.Value(0.85)).current;
  const buttonsOpacity = useRef(new Animated.Value(0)).current;

  // Use spreads (new format) or fall back to pages (backwards compatibility)
  const spreads = story?.spreads || story?.pages || [];
  const totalSpreads = spreads.length;
  const isLastSpread = currentSpread >= totalSpreads - 1;

  // Trigger animations when reaching last page
  useEffect(() => {
    if (isLastSpread && totalSpreads > 0) {
      // Reset animation values
      theEndOpacity.setValue(0);
      theEndScale.setValue(0.85);
      buttonsOpacity.setValue(0);
      setEndButtonsActive(false);

      // Animate "The End" text: fade + scale over 300ms, then pulse
      Animated.sequence([
        // Fade in and scale up
        Animated.parallel([
          Animated.timing(theEndOpacity, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
          Animated.timing(theEndScale, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
        ]),
        // Pulse: scale to 1.05
        Animated.timing(theEndScale, {
          toValue: 1.05,
          duration: 150,
          useNativeDriver: true,
        }),
        // Settle back to 1.0
        Animated.timing(theEndScale, {
          toValue: 1,
          duration: 150,
          useNativeDriver: true,
        }),
      ]).start();

      // Activate buttons after 1000ms delay
      const buttonTimer = setTimeout(() => {
        Animated.timing(buttonsOpacity, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }).start();
        setEndButtonsActive(true);
      }, 1000);

      return () => clearTimeout(buttonTimer);
    }
  }, [isLastSpread, totalSpreads]);

  const goBack = () => setCurrentSpread(Math.max(0, currentSpread - 1));
  const goForward = () => setCurrentSpread(Math.min(totalSpreads - 1, currentSpread + 1));
  const goToStart = () => setCurrentSpread(0);
  const goToCompleted = () => router.replace(`/completed/${id}`);

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
          style={{
            backgroundColor: '#FAF7F2',
            paddingVertical: 16,
            paddingHorizontal: 22,
            borderRadius: 22,
            borderWidth: 2,
            borderColor: '#EDE8E0',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            shadowColor: '#000',
            shadowOffset: { width: 0, height: 2 },
            shadowOpacity: 0.15,
            shadowRadius: 6,
            elevation: 4,
          }}
        >
          <Text style={{ fontSize: 32 }}>🏠</Text>
        </Pressable>

        {/* Progress Indicator */}
        <View style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 16,
          backgroundColor: '#FAF7F2',
          paddingVertical: 12,
          paddingHorizontal: 24,
          borderRadius: 20,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.15,
          shadowRadius: 6,
          elevation: 4,
        }}>
          <View style={{
            width: 180,
            height: 8,
            backgroundColor: '#E8E0D5',
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
            color: '#4A4035',
            fontFamily: fontFamily.nunitoBold,
            fontSize: 16,
          }}>
            {currentSpread + 1} / {totalSpreads}
          </Text>
        </View>

      </View>

      {/* Bottom Content: Buttons + Text in columns */}
      <View style={{
        position: 'absolute',
        bottom: 48,
        left: 24,
        right: 24,
        flexDirection: 'row',
        alignItems: 'flex-end',
      }}>
        {/* Left Button: Back (normal) or Again (last page) */}
        {isLastSpread ? (
          <Animated.View style={{ opacity: buttonsOpacity }}>
            <Pressable
              onPress={goToStart}
              disabled={!endButtonsActive}
              style={{
                backgroundColor: '#FAF7F2',
                width: 80,
                height: 80,
                borderRadius: 20,
                borderWidth: 2,
                borderColor: '#EDE8E0',
                alignItems: 'center',
                justifyContent: 'center',
                shadowColor: '#000',
                shadowOffset: { width: 0, height: 2 },
                shadowOpacity: 0.15,
                shadowRadius: 6,
                elevation: 4,
              }}
            >
              <Text style={{ fontSize: 28 }}>📖</Text>
              <Text style={{
                fontSize: 12,
                fontFamily: fontFamily.nunitoBold,
                color: '#4A4035',
                marginTop: 2,
              }}>Again</Text>
            </Pressable>
          </Animated.View>
        ) : (
          <Pressable
            onPress={goBack}
            disabled={isFirstSpread}
            style={{
              backgroundColor: '#FAF7F2',
              width: 64,
              height: 64,
              borderRadius: 32,
              borderWidth: 2,
              borderColor: '#EDE8E0',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: isFirstSpread ? 0.4 : 1,
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 2 },
              shadowOpacity: 0.15,
              shadowRadius: 6,
              elevation: 4,
            }}
          >
            <Text style={{ fontSize: 28 }}>👈</Text>
          </Pressable>
        )}

        {/* Center: Story Text or "The End" */}
        <View style={{
          flex: 1,
          paddingHorizontal: 32,
        }}>
          {isLastSpread ? (
            <Animated.View style={{
              opacity: theEndOpacity,
              transform: [{ scale: theEndScale }],
              alignItems: 'center',
            }}>
              <Text style={{
                fontSize: 32,
                color: '#F97316',
                textAlign: 'center',
                fontFamily: fontFamily.nunitoBold,
                textShadowColor: 'rgba(0,0,0,0.5)',
                textShadowOffset: { width: 0, height: 2 },
                textShadowRadius: 8,
              }}>
                ✨ The End ✨
              </Text>
            </Animated.View>
          ) : currentSpreadData ? (
            <Text style={{
              fontSize: 26,
              lineHeight: 40,
              color: 'white',
              textAlign: 'center',
              fontFamily: fontFamily.nunitoSemiBold,
              textShadowColor: 'rgba(0,0,0,0.5)',
              textShadowOffset: { width: 0, height: 2 },
              textShadowRadius: 8,
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

        {/* Right Button: Next (normal) or Done (last page) */}
        {isLastSpread ? (
          <Animated.View style={{ opacity: buttonsOpacity }}>
            <Pressable
              onPress={goToCompleted}
              disabled={!endButtonsActive}
              style={{
                overflow: 'hidden',
                width: 80,
                height: 80,
                borderRadius: 20,
                alignItems: 'center',
                justifyContent: 'center',
                shadowColor: '#F97316',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.4,
                shadowRadius: 12,
                elevation: 6,
              }}
            >
              <LinearGradient
                colors={['#FBBF24', '#F97316']}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                }}
              />
              <Text style={{ fontSize: 28 }}>🏠</Text>
              <Text style={{
                fontSize: 12,
                fontFamily: fontFamily.nunitoBold,
                color: 'white',
                marginTop: 2,
              }}>Done</Text>
            </Pressable>
          </Animated.View>
        ) : (
          <Pressable
            onPress={goForward}
            style={{
              backgroundColor: '#FAF7F2',
              width: 64,
              height: 64,
              borderRadius: 32,
              borderWidth: 2,
              borderColor: '#EDE8E0',
              alignItems: 'center',
              justifyContent: 'center',
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 2 },
              shadowOpacity: 0.15,
              shadowRadius: 6,
              elevation: 4,
            }}
          >
            <Text style={{ fontSize: 28 }}>👉</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}
