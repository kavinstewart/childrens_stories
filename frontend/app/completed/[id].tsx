import { View, Text, Pressable, Image, ActivityIndicator, Animated, useWindowDimensions } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { useRef, useEffect } from 'react';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useStory, useRecommendations } from '@/features/stories/hooks';
import { api, StoryRecommendation } from '@/lib/api';
import { fontFamily } from '@/lib/fonts';

// Grid configuration for recommendations
const CARD_GAP = 16;

export default function CompletedScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { width: screenWidth } = useWindowDimensions();
  const { data: story, isLoading: storyLoading } = useStory(id);
  const { data: recommendations, isLoading: recsLoading } = useRecommendations(id);

  // Animation values
  const theEndOpacity = useRef(new Animated.Value(0)).current;
  const theEndScale = useRef(new Animated.Value(0.85)).current;
  const coverOpacity = useRef(new Animated.Value(0)).current;
  const buttonsOpacity = useRef(new Animated.Value(0)).current;
  const recsHeaderOpacity = useRef(new Animated.Value(0)).current;
  const cardAnimations = useRef([
    new Animated.Value(0),
    new Animated.Value(0),
    new Animated.Value(0),
    new Animated.Value(0),
  ]).current;

  // Calculate card dimensions (4 cards in a row)
  const availableWidth = screenWidth - 48 - (CARD_GAP * 3); // padding + gaps
  const cardWidth = availableWidth / 4;
  const cardHeight = cardWidth * 1.1;

  // Trigger staggered animations on mount
  useEffect(() => {
    // Animate "The End" text: fade + scale + pulse
    Animated.sequence([
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
      Animated.timing(theEndScale, {
        toValue: 1.05,
        duration: 150,
        useNativeDriver: true,
      }),
      Animated.timing(theEndScale, {
        toValue: 1,
        duration: 150,
        useNativeDriver: true,
      }),
    ]).start();

    // Cover image fades in at 200ms
    setTimeout(() => {
      Animated.timing(coverOpacity, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }, 200);

    // Buttons fade in at 400ms
    setTimeout(() => {
      Animated.timing(buttonsOpacity, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }, 400);

    // "More Adventures" header fades in at 600ms
    setTimeout(() => {
      Animated.timing(recsHeaderOpacity, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }, 600);

    // Recommendation cards stagger in at 800ms+
    cardAnimations.forEach((anim, index) => {
      setTimeout(() => {
        Animated.timing(anim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }).start();
      }, 800 + (index * 100));
    });
  }, []);

  const handleReadAgain = () => {
    router.replace(`/read/${id}`);
  };

  const handleGoToLibrary = () => {
    router.replace('/');
  };

  const handleSelectRecommendation = (recId: string) => {
    router.replace(`/read/${recId}`);
  };

  if (storyLoading) {
    return (
      <LinearGradient colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']} style={{ flex: 1 }}>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator size="large" color="#7C3AED" />
        </View>
      </LinearGradient>
    );
  }

  const coverUrl = story?.is_illustrated
    ? api.getSpreadImageUrl(story.id, 1)
    : null;

  return (
    <LinearGradient colors={['#E0E7FF', '#FAE8FF', '#FCE7F3']} style={{ flex: 1 }}>
      <SafeAreaView style={{ flex: 1 }} edges={['top', 'left', 'right']}>
        <View style={{ flex: 1, padding: 24 }}>
          {/* Hero Section */}
          <View style={{ alignItems: 'center', marginBottom: 32 }}>
            {/* The End Header */}
            <Animated.View style={{
              opacity: theEndOpacity,
              transform: [{ scale: theEndScale }],
              marginBottom: 8,
            }}>
              <Text style={{
                fontSize: 36,
                fontFamily: fontFamily.nunitoBold,
                color: '#F97316',
                textAlign: 'center',
              }}>
                ✨ The End ✨
              </Text>
            </Animated.View>

            {/* Subtitle */}
            <Animated.Text style={{
              opacity: theEndOpacity,
              fontSize: 18,
              fontFamily: fontFamily.nunitoSemiBold,
              color: '#4A4035',
              textAlign: 'center',
              marginBottom: 24,
            }}>
              You finished "{story?.title || 'the story'}"!
            </Animated.Text>

            {/* Cover + Buttons Row */}
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 24 }}>
              {/* Read Again Button */}
              <Animated.View style={{ opacity: buttonsOpacity }}>
                <Pressable
                  onPress={handleReadAgain}
                  style={{
                    backgroundColor: '#FAF7F2',
                    width: 100,
                    height: 100,
                    borderRadius: 24,
                    borderWidth: 2,
                    borderColor: '#EDE8E0',
                    alignItems: 'center',
                    justifyContent: 'center',
                    shadowColor: '#000',
                    shadowOffset: { width: 0, height: 2 },
                    shadowOpacity: 0.1,
                    shadowRadius: 8,
                    elevation: 4,
                  }}
                >
                  <Text style={{ fontSize: 36 }}>📖</Text>
                  <Text style={{
                    fontSize: 14,
                    fontFamily: fontFamily.nunitoBold,
                    color: '#4A4035',
                    marginTop: 4,
                  }}>Read Again</Text>
                </Pressable>
              </Animated.View>

              {/* Cover Image */}
              <Animated.View style={{
                opacity: coverOpacity,
                width: 180,
                height: 200,
                borderRadius: 16,
                overflow: 'hidden',
                shadowColor: '#000',
                shadowOffset: { width: 0, height: 4 },
                shadowOpacity: 0.2,
                shadowRadius: 12,
                elevation: 6,
              }}>
                {coverUrl ? (
                  <Image
                    source={{ uri: coverUrl }}
                    style={{ width: '100%', height: '100%' }}
                    resizeMode="cover"
                  />
                ) : (
                  <LinearGradient
                    colors={['#A78BFA', '#7C3AED']}
                    style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}
                  >
                    <Text style={{ fontSize: 64 }}>📖</Text>
                  </LinearGradient>
                )}
              </Animated.View>

              {/* Library Button */}
              <Animated.View style={{ opacity: buttonsOpacity }}>
                <Pressable
                  onPress={handleGoToLibrary}
                  style={{
                    width: 100,
                    height: 100,
                    borderRadius: 24,
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                    shadowColor: '#F97316',
                    shadowOffset: { width: 0, height: 4 },
                    shadowOpacity: 0.3,
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
                  <Text style={{ fontSize: 36 }}>🏠</Text>
                  <Text style={{
                    fontSize: 14,
                    fontFamily: fontFamily.nunitoBold,
                    color: 'white',
                    marginTop: 4,
                  }}>Library</Text>
                </Pressable>
              </Animated.View>
            </View>
          </View>

          {/* Divider */}
          <View style={{
            height: 2,
            backgroundColor: 'rgba(0,0,0,0.1)',
            marginHorizontal: 48,
            marginBottom: 24,
            borderRadius: 1,
          }} />

          {/* Recommendations Section */}
          <Animated.View style={{ opacity: recsHeaderOpacity }}>
            <Text style={{
              fontSize: 22,
              fontFamily: fontFamily.nunitoBold,
              color: '#7C3AED',
              textAlign: 'center',
              marginBottom: 16,
            }}>
              More Adventures
            </Text>
          </Animated.View>

          {/* Recommendation Cards */}
          {recsLoading ? (
            <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
              <ActivityIndicator size="small" color="#7C3AED" />
            </View>
          ) : recommendations && recommendations.length > 0 ? (
            <View style={{
              flexDirection: 'row',
              justifyContent: 'center',
              gap: CARD_GAP,
            }}>
              {recommendations.slice(0, 4).map((rec: StoryRecommendation, index: number) => (
                <RecommendationCard
                  key={rec.id}
                  recommendation={rec}
                  width={cardWidth}
                  height={cardHeight}
                  animation={cardAnimations[index]}
                  onPress={() => handleSelectRecommendation(rec.id)}
                />
              ))}
            </View>
          ) : (
            <Animated.View style={{
              opacity: recsHeaderOpacity,
              alignItems: 'center',
              paddingVertical: 32,
            }}>
              <Text style={{ fontSize: 48, marginBottom: 8 }}>📚</Text>
              <Text style={{
                fontSize: 16,
                fontFamily: fontFamily.nunito,
                color: '#6B7280',
                textAlign: 'center',
              }}>
                No other stories yet!{'\n'}Create more adventures in the library.
              </Text>
            </Animated.View>
          )}
        </View>
      </SafeAreaView>
    </LinearGradient>
  );
}

// Recommendation Card Component
function RecommendationCard({
  recommendation,
  width,
  height,
  animation,
  onPress,
}: {
  recommendation: StoryRecommendation;
  width: number;
  height: number;
  animation: Animated.Value;
  onPress: () => void;
}) {
  const coverUrl = recommendation.is_illustrated && recommendation.cover_url
    ? recommendation.cover_url.startsWith('http')
      ? recommendation.cover_url
      : `http://192.168.86.39:8000${recommendation.cover_url}`
    : null;

  const illustrationHeight = height * 0.70;
  const infoHeight = height * 0.30;

  // Color gradients for cards without images
  const gradientColors: [string, string][] = [
    ['#FCD34D', '#F97316'],
    ['#A78BFA', '#7C3AED'],
    ['#F472B6', '#EC4899'],
    ['#22D3EE', '#3B82F6'],
  ];
  const colorIndex = recommendation.id.charCodeAt(0) % gradientColors.length;

  return (
    <Animated.View style={{
      opacity: animation,
      transform: [{
        translateY: animation.interpolate({
          inputRange: [0, 1],
          outputRange: [20, 0],
        }),
      }],
      width,
      height,
    }}>
      <Pressable
        onPress={onPress}
        style={({ pressed }) => ({
          flex: 1,
          borderRadius: 16,
          overflow: 'hidden',
          opacity: pressed ? 0.9 : 1,
          transform: [{ scale: pressed ? 0.98 : 1 }],
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.1,
          shadowRadius: 4,
          elevation: 3,
        })}
      >
        {/* Illustration area */}
        <View style={{
          height: illustrationHeight,
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
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
              <Text style={{ fontSize: 32 }}>📖</Text>
            </LinearGradient>
          )}
        </View>

        {/* Info section */}
        <View style={{
          height: infoHeight,
          backgroundColor: '#FEF3C7',
          paddingHorizontal: 8,
          paddingVertical: 6,
          justifyContent: 'center',
          borderBottomLeftRadius: 16,
          borderBottomRightRadius: 16,
        }}>
          <Text
            style={{
              color: '#1F2937',
              fontWeight: 'bold',
              fontSize: 13,
              lineHeight: 16,
            }}
            numberOfLines={2}
          >
            {recommendation.title || recommendation.goal || 'Untitled'}
          </Text>
        </View>
      </Pressable>
    </Animated.View>
  );
}
