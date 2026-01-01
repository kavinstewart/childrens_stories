import { View, Text, Pressable, TextInput, ActivityIndicator, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  runOnJS,
} from 'react-native-reanimated';
import { useEffect } from 'react';
import { fontFamily } from '@/lib/fonts';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');
const OVERLAY_HEIGHT = SCREEN_HEIGHT * 0.55;

interface SpreadEditOverlayProps {
  isVisible: boolean;
  spreadNumber: number;
  currentPrompt?: string;
  isRegenerating: boolean;
  onRegenerate: () => void;
  onDismiss: () => void;
}

export function SpreadEditOverlay({
  isVisible,
  spreadNumber,
  currentPrompt,
  isRegenerating,
  onRegenerate,
  onDismiss,
}: SpreadEditOverlayProps) {
  const translateY = useSharedValue(SCREEN_HEIGHT);
  const backdropOpacity = useSharedValue(0);

  useEffect(() => {
    if (isVisible) {
      translateY.value = withSpring(SCREEN_HEIGHT - OVERLAY_HEIGHT, {
        damping: 20,
        stiffness: 90,
      });
      backdropOpacity.value = withTiming(1, { duration: 300 });
    } else {
      translateY.value = withTiming(SCREEN_HEIGHT, { duration: 250 });
      backdropOpacity.value = withTiming(0, { duration: 200 });
    }
  }, [isVisible]);

  const overlayStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
  }));

  const backdropStyle = useAnimatedStyle(() => ({
    opacity: backdropOpacity.value,
  }));

  if (!isVisible && backdropOpacity.value === 0) {
    return null;
  }

  return (
    <>
      {/* Backdrop */}
      <Animated.View
        style={[
          {
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
          },
          backdropStyle,
        ]}
      >
        <Pressable
          style={{ flex: 1 }}
          onPress={isRegenerating ? undefined : onDismiss}
        />
      </Animated.View>

      {/* Overlay Panel */}
      <Animated.View
        style={[
          {
            position: 'absolute',
            left: 0,
            right: 0,
            height: OVERLAY_HEIGHT,
            backgroundColor: 'rgba(30, 20, 10, 0.98)',
            borderTopLeftRadius: 24,
            borderTopRightRadius: 24,
            padding: 24,
          },
          overlayStyle,
        ]}
      >
        {/* Drag Handle */}
        <View
          style={{
            alignSelf: 'center',
            width: 40,
            height: 4,
            backgroundColor: 'rgba(255,255,255,0.3)',
            borderRadius: 2,
            marginBottom: 20,
          }}
        />

        {/* Header */}
        <View
          style={{
            flexDirection: 'row',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 20,
          }}
        >
          <Text
            style={{
              fontSize: 22,
              color: 'white',
              fontFamily: fontFamily.nunitoBold,
            }}
          >
            Edit Spread {spreadNumber}
          </Text>
          <Pressable
            onPress={isRegenerating ? undefined : onDismiss}
            disabled={isRegenerating}
            style={{
              width: 36,
              height: 36,
              borderRadius: 18,
              backgroundColor: 'rgba(255,255,255,0.1)',
              alignItems: 'center',
              justifyContent: 'center',
              opacity: isRegenerating ? 0.5 : 1,
            }}
          >
            <Text style={{ color: 'white', fontSize: 18 }}>✕</Text>
          </Pressable>
        </View>

        {isRegenerating ? (
          /* Loading State */
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
                fontSize: 18,
                fontFamily: fontFamily.nunitoSemiBold,
                marginTop: 20,
              }}
            >
              Regenerating illustration...
            </Text>
            <Text
              style={{
                color: 'rgba(255,255,255,0.6)',
                fontSize: 14,
                fontFamily: fontFamily.nunito,
                marginTop: 8,
                textAlign: 'center',
              }}
            >
              This may take a moment.{'\n'}The image will update automatically.
            </Text>
          </View>
        ) : (
          /* Edit Form */
          <>
            {/* Current Prompt Display */}
            <Text
              style={{
                color: 'rgba(255,255,255,0.7)',
                fontSize: 14,
                fontFamily: fontFamily.nunitoSemiBold,
                marginBottom: 8,
              }}
            >
              Current Prompt
            </Text>
            <View
              style={{
                backgroundColor: '#FAF7F2',
                borderRadius: 16,
                padding: 16,
                marginBottom: 24,
              }}
            >
              <TextInput
                value={currentPrompt || 'No prompt available'}
                editable={false}
                multiline
                style={{
                  fontFamily: fontFamily.nunito,
                  fontSize: 14,
                  color: '#374151',
                  minHeight: 80,
                  textAlignVertical: 'top',
                }}
              />
            </View>

            {/* Action Buttons */}
            <View style={{ gap: 16 }}>
              {/* Regenerate Button */}
              <Pressable
                onPress={onRegenerate}
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
                    paddingVertical: 16,
                    paddingHorizontal: 24,
                    borderRadius: 16,
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 10,
                  }}
                >
                  <Text style={{ fontSize: 20 }}>🔄</Text>
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

              {/* Helper Text */}
              <Text
                style={{
                  color: 'rgba(255,255,255,0.5)',
                  fontSize: 13,
                  fontFamily: fontFamily.nunito,
                  textAlign: 'center',
                }}
              >
                Generate a new illustration using the same prompt
              </Text>

              {/* Cancel Button */}
              <Pressable
                onPress={onDismiss}
                style={({ pressed }) => ({
                  paddingVertical: 12,
                  opacity: pressed ? 0.7 : 1,
                })}
              >
                <Text
                  style={{
                    color: 'rgba(255,255,255,0.6)',
                    fontSize: 16,
                    fontFamily: fontFamily.nunitoSemiBold,
                    textAlign: 'center',
                  }}
                >
                  Cancel
                </Text>
              </Pressable>
            </View>
          </>
        )}
      </Animated.View>
    </>
  );
}
