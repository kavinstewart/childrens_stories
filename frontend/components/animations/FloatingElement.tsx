import { useEffect } from 'react';
import { ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';

interface FloatingElementProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  style?: ViewStyle;
}

/**
 * A container that makes its children float gently up and down
 * with a subtle rotation, like a leaf drifting in the wind.
 */
export function FloatingElement({
  children,
  delay = 0,
  duration = 4,
  style,
}: FloatingElementProps) {
  const translateY = useSharedValue(0);
  const rotation = useSharedValue(0);

  useEffect(() => {
    const durationMs = duration * 1000;

    translateY.value = withDelay(
      delay * 1000,
      withRepeat(
        withSequence(
          withTiming(-15, { duration: durationMs / 2, easing: Easing.inOut(Easing.ease) }),
          withTiming(0, { duration: durationMs / 2, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      )
    );

    rotation.value = withDelay(
      delay * 1000,
      withRepeat(
        withSequence(
          withTiming(3, { duration: durationMs / 2, easing: Easing.inOut(Easing.ease) }),
          withTiming(0, { duration: durationMs / 2, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      )
    );
  }, [delay, duration]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateY: translateY.value },
      { rotate: `${rotation.value}deg` },
    ],
  }));

  return (
    <Animated.View
      style={[{ position: 'absolute', pointerEvents: 'none' }, style, animatedStyle]}
    >
      {children}
    </Animated.View>
  );
}
