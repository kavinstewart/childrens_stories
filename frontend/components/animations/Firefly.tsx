import { useEffect } from 'react';
import { DimensionValue, View, ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';

interface FireflyProps {
  /** Delay before animation starts (in seconds) */
  delay?: number;
  /** Horizontal position (percentage string like "20%" or number) */
  x: DimensionValue;
  /** Vertical position (percentage string like "30%" or number) */
  y: DimensionValue;
  /** Size of the firefly dot (default 8) */
  size?: number;
  /** Additional container styles */
  style?: ViewStyle;
}

/**
 * A glowing dot that floats around randomly like a firefly,
 * fading in and out as it moves.
 */
export function Firefly({
  delay = 0,
  x,
  y,
  size = 8,
  style,
}: FireflyProps) {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.3);

  useEffect(() => {
    const duration = 3000;
    const delayMs = delay * 1000;

    // X movement: 0 -> 15 -> -10 -> 20 -> 0
    translateX.value = withDelay(
      delayMs,
      withRepeat(
        withSequence(
          withTiming(15, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(-10, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(20, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(0, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        false
      )
    );

    // Y movement: 0 -> -20 -> -35 -> -15 -> 0
    translateY.value = withDelay(
      delayMs,
      withRepeat(
        withSequence(
          withTiming(-20, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(-35, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(-15, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(0, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        false
      )
    );

    // Scale: 1 -> 1.2 -> 0.8 -> 1.1 -> 1
    scale.value = withDelay(
      delayMs,
      withRepeat(
        withSequence(
          withTiming(1.2, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.8, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(1.1, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        false
      )
    );

    // Opacity: 0.3 -> 1 -> 0.6 -> 0.9 -> 0.3
    opacity.value = withDelay(
      delayMs,
      withRepeat(
        withSequence(
          withTiming(1, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.6, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.9, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.3, { duration: duration * 0.25, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        false
      )
    );
  }, [delay]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: scale.value },
    ],
    opacity: opacity.value,
  }));

  return (
    <Animated.View
      style={[
        {
          position: 'absolute',
          left: x,
          top: y,
        },
        style,
        animatedStyle,
      ]}
    >
      <View
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: '#FDE047', // yellow-300
          shadowColor: '#FDE047',
          shadowOffset: { width: 0, height: 0 },
          shadowOpacity: 0.6,
          shadowRadius: 8,
        }}
      />
    </Animated.View>
  );
}
