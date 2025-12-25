import { View, Text, Pressable, Image, ActivityIndicator, Dimensions } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useState } from 'react';
import { useStory, useRecommendations } from '@/features/stories/hooks';
import { api, StoryRecommendation } from '@/lib/api';
import { fontFamily } from '@/lib/fonts';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Card sizing for recommendations
const CARD_GAP = 12;
const CARD_COUNT = 4;

export default function StoryReader() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: story, isLoading, error } = useStory(id);
  const [currentSpread, setCurrentSpread] = useState(0);

  // Use spreads (new format) or fall back to pages (backwards compatibility)
  const spreads = story?.spreads || story?.pages || [];
  const totalSpreads = spreads.length;
  const isLastSpread = currentSpread >= totalSpreads - 1;

  // Fetch recommendations (only used on last page, but hook must be called unconditionally)
  const { data: recommendations } = useRecommendations(id, CARD_COUNT);

  const goBack = () => setCurrentSpread(Math.max(0, currentSpread - 1));
  const goForward = () => setCurrentSpread(Math.min(totalSpreads - 1, currentSpread + 1));
  const goToStart = () => setCurrentSpread(0);
  const goToLibrary = () => router.replace('/');
  const goToStory = (storyId: string) => router.replace(`/read/${storyId}`);

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

  // Calculate card dimensions for recommendations
  const availableWidth = SCREEN_WIDTH - 48 - (CARD_GAP * (CARD_COUNT - 1)); // padding + gaps
  const cardWidth = availableWidth / CARD_COUNT;
  const cardHeight = cardWidth * 1.1;

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

      {/* Dark gradient overlay at bottom for text - taller on last page */}
      <LinearGradient
        colors={['transparent', 'rgba(30, 20, 10, 0.3)', 'rgba(30, 20, 10, 0.85)', 'rgba(30, 20, 10, 0.95)']}
        locations={[0, 0.15, 0.5, 1]}
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: isLastSpread ? '55%' : '45%',
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

      {/* Tap zones for gesture navigation (disabled on last page) */}
      {!isLastSpread && (
        <>
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
            style={{
              position: 'absolute',
              top: 100,
              right: 0,
              width: '25%',
              height: SCREEN_HEIGHT - 220,
            }}
          />
        </>
      )}

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

      {/* Bottom Content */}
      {isLastSpread ? (
        /* END PAGE: The End + Recommendations + Buttons */
        <View style={{
          position: 'absolute',
          bottom: 32,
          left: 24,
          right: 24,
        }}>
          {/* The End */}
          <Text style={{
            fontSize: 36,
            color: '#F97316',
            textAlign: 'center',
            fontFamily: fontFamily.nunitoBold,
            textShadowColor: 'rgba(0,0,0,0.5)',
            textShadowOffset: { width: 0, height: 2 },
            textShadowRadius: 8,
            marginBottom: 20,
          }}>
            The End
          </Text>

          {/* Recommendation Cards */}
          {recommendations && recommendations.length > 0 && (
            <View style={{ marginBottom: 20 }}>
              <Text style={{
                fontSize: 16,
                color: 'rgba(255,255,255,0.7)',
                textAlign: 'center',
                fontFamily: fontFamily.nunitoSemiBold,
                marginBottom: 12,
              }}>
                More Adventures
              </Text>
              <View style={{
                flexDirection: 'row',
                justifyContent: 'center',
                gap: CARD_GAP,
              }}>
                {recommendations.slice(0, CARD_COUNT).map((rec: StoryRecommendation) => (
                  <RecommendationCard
                    key={rec.id}
                    recommendation={rec}
                    width={cardWidth}
                    height={cardHeight}
                    onPress={() => goToStory(rec.id)}
                  />
                ))}
              </View>
            </View>
          )}

          {/* Action Buttons */}
          <View style={{
            flexDirection: 'row',
            justifyContent: 'center',
            gap: 24,
          }}>
            {/* Read Again Button */}
            <Pressable
              onPress={goToStart}
              style={{
                backgroundColor: '#FAF7F2',
                width: 100,
                height: 70,
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
              <Text style={{ fontSize: 24 }}>📖</Text>
              <Text style={{
                fontSize: 12,
                fontFamily: fontFamily.nunitoBold,
                color: '#4A4035',
                marginTop: 2,
              }}>Again</Text>
            </Pressable>

            {/* Library Button */}
            <Pressable
              onPress={goToLibrary}
              style={{
                overflow: 'hidden',
                width: 100,
                height: 70,
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
              <Text style={{ fontSize: 24 }}>🏠</Text>
              <Text style={{
                fontSize: 12,
                fontFamily: fontFamily.nunitoBold,
                color: 'white',
                marginTop: 2,
              }}>Library</Text>
            </Pressable>
          </View>
        </View>
      ) : (
        /* NORMAL PAGE: Back button + Text + Next button */
        <View style={{
          position: 'absolute',
          bottom: 48,
          left: 24,
          right: 24,
          flexDirection: 'row',
          alignItems: 'flex-end',
        }}>
          {/* Back Button */}
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

          {/* Story Text */}
          <View style={{
            flex: 1,
            paddingHorizontal: 32,
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

          {/* Next Button */}
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
        </View>
      )}
    </View>
  );
}

// Recommendation Card Component
function RecommendationCard({
  recommendation,
  width,
  height,
  onPress,
}: {
  recommendation: StoryRecommendation;
  width: number;
  height: number;
  onPress: () => void;
}) {
  const coverUrl = recommendation.is_illustrated && recommendation.cover_url
    ? recommendation.cover_url.startsWith('http')
      ? recommendation.cover_url
      : `http://192.168.86.39:8000${recommendation.cover_url}`
    : null;

  const illustrationHeight = height * 0.65;
  const infoHeight = height * 0.35;

  // Color gradients for cards without images
  const gradientColors: [string, string][] = [
    ['#FCD34D', '#F97316'],
    ['#A78BFA', '#7C3AED'],
    ['#F472B6', '#EC4899'],
    ['#22D3EE', '#3B82F6'],
  ];
  const colorIndex = recommendation.id.charCodeAt(0) % gradientColors.length;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => ({
        width,
        height,
        borderRadius: 12,
        overflow: 'hidden',
        opacity: pressed ? 0.9 : 1,
        transform: [{ scale: pressed ? 0.98 : 1 }],
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
        elevation: 3,
      })}
    >
      {/* Illustration area */}
      <View style={{
        height: illustrationHeight,
        overflow: 'hidden',
      }}>
        {coverUrl ? (
          <Image
            source={{ uri: coverUrl }}
            style={{ width: '100%', height: '100%' }}
            resizeMode="cover"
          />
        ) : (
          <LinearGradient
            colors={gradientColors[colorIndex]}
            style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
          >
            <Text style={{ fontSize: 24 }}>📖</Text>
          </LinearGradient>
        )}
      </View>

      {/* Info section */}
      <View style={{
        height: infoHeight,
        backgroundColor: '#FEF3C7',
        paddingHorizontal: 6,
        paddingVertical: 4,
        justifyContent: 'center',
      }}>
        <Text
          style={{
            color: '#1F2937',
            fontWeight: 'bold',
            fontSize: 11,
            lineHeight: 13,
          }}
          numberOfLines={2}
        >
          {recommendation.title || recommendation.goal || 'Untitled'}
        </Text>
      </View>
    </Pressable>
  );
}
