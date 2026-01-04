import { View, Text, Pressable, Image, ActivityIndicator, Dimensions } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useState, useEffect } from 'react';
import { useStory, useRecommendations } from '@/features/stories/hooks';
import { api } from '@/lib/api';
import { fontFamily } from '@/lib/fonts';
import { StoryCard } from '@/components/StoryCard';
import { StoryCacheManager } from '@/lib/story-cache';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Card sizing for recommendations
const CARD_GAP = 16;
const CARD_COUNT = 4;

export default function StoryReader() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: story, isLoading, error } = useStory(id);
  const [currentSpread, setCurrentSpread] = useState(0);
  const [isCaching, setIsCaching] = useState(false);
  const [isCached, setIsCached] = useState(false);
  const [cacheCheckComplete, setCacheCheckComplete] = useState(false);

  const spreads = story?.spreads || [];
  const totalSpreads = spreads.length;
  const [showEndScreen, setShowEndScreen] = useState(false);
  const isLastSpread = currentSpread === totalSpreads - 1;

  // Check if story is already cached on mount
  useEffect(() => {
    if (!id) return;

    setCacheCheckComplete(false);
    StoryCacheManager.isStoryCached(id).then(cached => {
      console.log(`[Cache] isStoryCached(${id}): ${cached}`);
      setIsCached(cached);
      setCacheCheckComplete(true);
    });
  }, [id]);

  // Trigger background caching when story loads (if eligible)
  // Only runs after cache check completes to avoid race condition
  useEffect(() => {
    if (!cacheCheckComplete) return; // Wait for cache check to finish
    if (story?.is_illustrated && story.status === 'completed' && !isCached && !isCaching) {
      setIsCaching(true);
      console.log(`[Cache] Starting cache for story ${story.id}`);
      StoryCacheManager.cacheStory(story)
        .then(success => {
          console.log(`[Cache] Caching ${success ? 'succeeded' : 'failed'} for story ${story.id}`);
          if (success) {
            setIsCached(true);
          }
        })
        .finally(() => {
          setIsCaching(false);
        });
    }
  }, [story, isCached, isCaching, cacheCheckComplete]);

  // Fetch recommendations (only used on last page, but hook must be called unconditionally)
  const { data: recommendations } = useRecommendations(id, CARD_COUNT);

  const goBack = () => {
    if (showEndScreen) {
      setShowEndScreen(false);
    } else {
      setCurrentSpread(Math.max(0, currentSpread - 1));
    }
  };
  const goForward = () => {
    if (isLastSpread) {
      setShowEndScreen(true);
    } else {
      setCurrentSpread(currentSpread + 1);
    }
  };
  const goToStart = () => {
    setShowEndScreen(false);
    setCurrentSpread(0);
  };
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
  const lastSpreadData = spreads[totalSpreads - 1];

  // Get image URL - use last spread's image on end screen
  // Include illustration_updated_at for cache busting after regeneration
  const displaySpread = showEndScreen ? lastSpreadData : currentSpreadData;
  const imageUrl = story.is_illustrated && displaySpread
    ? api.getSpreadImageUrl(story.id, displaySpread.spread_number, displaySpread.illustration_updated_at)
    : null;

  const isFirstSpread = currentSpread === 0 && !showEndScreen;
  const progressPercent = showEndScreen ? 100 : (totalSpreads > 0 ? ((currentSpread + 1) / totalSpreads) * 100 : 0);

  // Calculate card dimensions for recommendations
  const availableWidth = SCREEN_WIDTH - 48 - (CARD_GAP * (CARD_COUNT - 1)); // padding + gaps
  const cardWidth = availableWidth / CARD_COUNT;
  const cardHeight = cardWidth * 1.1;

  return (
    <View style={{ flex: 1, backgroundColor: '#1a1a2e' }}>
      {/* Full-bleed Illustration */}
      {imageUrl ? (
        <Image
          key={imageUrl}
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
          onError={(e) => console.error(`[Image] Reader failed to load spread ${currentSpread + 1}: ${imageUrl}`, e.nativeEvent.error)}
          onLoad={() => console.log(`[Image] Reader loaded spread ${currentSpread + 1}: ${imageUrl}`)}
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

      {/* Dark gradient overlay at bottom for text - taller on end screen */}
      <LinearGradient
        colors={['transparent', 'rgba(30, 20, 10, 0.4)', 'rgba(30, 20, 10, 0.88)', 'rgba(30, 20, 10, 0.95)']}
        locations={showEndScreen ? [0, 0.05, 0.25, 1] : [0, 0.1, 0.4, 1]}
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: showEndScreen ? '80%' : '45%',
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

      {/* Tap zones for gesture navigation (disabled on end screen) */}
      {!showEndScreen && (
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

        {/* Edit Button - only show when on a spread (not end screen) and story is illustrated */}
        {!showEndScreen && story.is_illustrated && currentSpreadData && (
          <Pressable
            onPress={() => {
              router.push({
                pathname: '/edit-prompt',
                params: {
                  storyId: story.id,
                  spreadNumber: currentSpreadData.spread_number.toString(),
                  composedPrompt: currentSpreadData.composed_prompt || '',
                  illustrationUpdatedAt: currentSpreadData.illustration_updated_at || '',
                },
              });
            }}
            style={{
              backgroundColor: '#FAF7F2',
              paddingVertical: 16,
              paddingHorizontal: 22,
              borderRadius: 22,
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
            <Text style={{ fontSize: 32 }}>✏️</Text>
          </Pressable>
        )}
      </View>

      {/* Bottom Content */}
      {showEndScreen ? (
        /* END SCREEN: The End + Recommendations + Buttons */
        <View style={{
          position: 'absolute',
          bottom: 48,
          left: 24,
          right: 24,
          top: SCREEN_HEIGHT * 0.22, // Start from 22% down - gives illustration room while keeping content higher
          justifyContent: 'flex-start',
          alignItems: 'center',
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
            marginBottom: 24,
          }}>
            The End
          </Text>

          {/* Recommendation Cards */}
          {recommendations && recommendations.length > 0 && (
            <View style={{ marginBottom: 24 }}>
              <Text style={{
                fontSize: 16,
                color: 'rgba(255,255,255,0.7)',
                textAlign: 'center',
                fontFamily: fontFamily.nunitoSemiBold,
                marginBottom: 16,
              }}>
                More Adventures
              </Text>
              <View style={{
                flexDirection: 'row',
                justifyContent: 'center',
                gap: CARD_GAP,
              }}>
                {recommendations.slice(0, CARD_COUNT).map((rec, index) => (
                  <StoryCard
                    key={rec.id}
                    recommendation={rec}
                    width={cardWidth}
                    height={cardHeight}
                    colorIndex={index}
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

      {/* Offline caching indicator */}
      {isCaching && (
        <View style={{
          position: 'absolute',
          bottom: 16,
          alignSelf: 'center',
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          paddingVertical: 8,
          paddingHorizontal: 16,
          borderRadius: 20,
          gap: 8,
        }}>
          <ActivityIndicator size="small" color="white" />
          <Text style={{
            color: 'white',
            fontSize: 13,
            fontFamily: fontFamily.nunito,
          }}>
            Saving for offline...
          </Text>
        </View>
      )}

    </View>
  );
}
