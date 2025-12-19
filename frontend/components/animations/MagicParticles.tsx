import { useEffect } from 'react';
import { Text, View, ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';

interface ParticleProps {
  emoji: string;
  size: number;
  delay: number;
  top?: number;
  bottom?: number;
  left?: number;
  right?: number;
}

function Particle({ emoji, size, delay, top, bottom, left, right }: ParticleProps) {
  const translateY = useSharedValue(0);
  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.7);

  useEffect(() => {
    const duration = 2000;

    translateY.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(-10, { duration: duration / 2, easing: Easing.inOut(Easing.ease) }),
          withTiming(0, { duration: duration / 2, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      )
    );

    scale.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1.2, { duration: duration / 2, easing: Easing.inOut(Easing.ease) }),
          withTiming(1, { duration: duration / 2, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      )
    );

    opacity.value = withDelay(
      delay,
      withRepeat(
        withSequence(
          withTiming(1, { duration: duration / 2, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.7, { duration: duration / 2, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        true
      )
    );
  }, [delay]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateY: translateY.value },
      { scale: scale.value },
    ],
    opacity: opacity.value,
  }));

  const positionStyle: ViewStyle = {
    position: 'absolute',
    ...(top !== undefined && { top }),
    ...(bottom !== undefined && { bottom }),
    ...(left !== undefined && { left }),
    ...(right !== undefined && { right }),
  };

  return (
    <Animated.View style={[positionStyle, animatedStyle]}>
      <Text style={{ fontSize: size }}>{emoji}</Text>
    </Animated.View>
  );
}

interface MagicParticlesProps {
  /** Additional container styles */
  style?: ViewStyle;
}

/**
 * Four sparkle particles that orbit around a central point,
 * pulsing and floating to create a magical effect.
 */
export function MagicParticles({ style }: MagicParticlesProps) {
  return (
    <View style={[{ position: 'absolute', width: '100%', height: '100%' }, style]}>
      <Particle emoji="\u2728" size={24} delay={0} top={-32} left={-32} />
      <Particle emoji="\u2B50" size={20} delay={500} top={-24} right={-40} />
      <Particle emoji="\u2728" size={20} delay={1000} bottom={-24} left={-40} />
      <Particle emoji="\u{1F31F}" size={24} delay={1500} bottom={32} right={-32} />
    </View>
  );
}
