import { useEffect } from 'react';
import { Text, ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSequence,
  withTiming,
  withSpring,
  Easing,
} from 'react-native-reanimated';

interface StageIconProps {
  /** The emoji to display */
  emoji: string;
  /** Font size (default 36) */
  size?: number;
  /** Unique key to trigger animation on change */
  stageKey: number | string;
  /** Additional container styles */
  style?: ViewStyle;
}

/**
 * An icon that pops in with a scale and rotation animation
 * when the stage changes.
 */
export function StageIcon({
  emoji,
  size = 36,
  stageKey,
  style,
}: StageIconProps) {
  const scale = useSharedValue(0);
  const rotation = useSharedValue(-180);
  const opacity = useSharedValue(0);

  useEffect(() => {
    // Reset and animate
    scale.value = 0;
    rotation.value = -180;
    opacity.value = 0;

    // Pop-in animation
    scale.value = withSequence(
      withTiming(1.3, { duration: 250, easing: Easing.out(Easing.ease) }),
      withSpring(1, { damping: 10, stiffness: 100 })
    );

    rotation.value = withSequence(
      withTiming(10, { duration: 250, easing: Easing.out(Easing.ease) }),
      withSpring(0, { damping: 10, stiffness: 100 })
    );

    opacity.value = withTiming(1, { duration: 200 });
  }, [stageKey]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: scale.value },
      { rotate: `${rotation.value}deg` },
    ],
    opacity: opacity.value,
  }));

  return (
    <Animated.View style={[style, animatedStyle]}>
      <Text style={{ fontSize: size }}>{emoji}</Text>
    </Animated.View>
  );
}
