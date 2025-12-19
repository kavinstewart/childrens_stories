import { useEffect } from 'react';
import { ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSequence,
  withTiming,
  withSpring,
  Easing,
} from 'react-native-reanimated';

interface CompletePopProps {
  children: React.ReactNode;
  /** Additional container styles */
  style?: ViewStyle;
}

/**
 * A wrapper that makes its children pop in with a satisfying
 * scale animation when mounted, perfect for completion states.
 */
export function CompletePop({ children, style }: CompletePopProps) {
  const scale = useSharedValue(0);

  useEffect(() => {
    scale.value = withSequence(
      withTiming(1.2, { duration: 250, easing: Easing.out(Easing.ease) }),
      withSpring(1, { damping: 8, stiffness: 100 })
    );
  }, []);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <Animated.View style={[style, animatedStyle]}>
      {children}
    </Animated.View>
  );
}
