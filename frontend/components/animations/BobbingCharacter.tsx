import { useEffect, useState } from 'react';
import { Text, ViewStyle } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
  Easing,
} from 'react-native-reanimated';

// Collection of story-themed emojis to cycle through
const storyEmojis = [
  // Wizards - all variants
  '\u{1F9D9}', '\u{1F9D9}\u200D\u2642\uFE0F', '\u{1F9D9}\u200D\u2640\uFE0F',
  '\u{1F9D9}\u{1F3FB}', '\u{1F9D9}\u{1F3FC}', '\u{1F9D9}\u{1F3FD}', '\u{1F9D9}\u{1F3FE}', '\u{1F9D9}\u{1F3FF}',
  // Fairies
  '\u{1F9DA}', '\u{1F9DA}\u200D\u2640\uFE0F', '\u{1F9DA}\u200D\u2642\uFE0F',
  '\u{1F9DA}\u{1F3FB}', '\u{1F9DA}\u{1F3FC}', '\u{1F9DA}\u{1F3FD}', '\u{1F9DA}\u{1F3FE}', '\u{1F9DA}\u{1F3FF}',
  // Royalty
  '\u{1F934}', '\u{1F934}\u{1F3FB}', '\u{1F934}\u{1F3FC}', '\u{1F934}\u{1F3FD}', '\u{1F934}\u{1F3FE}', '\u{1F934}\u{1F3FF}',
  '\u{1F478}', '\u{1F478}\u{1F3FB}', '\u{1F478}\u{1F3FC}', '\u{1F478}\u{1F3FD}', '\u{1F478}\u{1F3FE}', '\u{1F478}\u{1F3FF}',
  // Superheroes
  '\u{1F9B8}', '\u{1F9B8}\u200D\u2642\uFE0F', '\u{1F9B8}\u200D\u2640\uFE0F',
  '\u{1F9B8}\u{1F3FB}', '\u{1F9B8}\u{1F3FC}', '\u{1F9B8}\u{1F3FD}', '\u{1F9B8}\u{1F3FE}', '\u{1F9B8}\u{1F3FF}',
  // Children
  '\u{1F9D2}', '\u{1F9D2}\u{1F3FB}', '\u{1F9D2}\u{1F3FC}', '\u{1F9D2}\u{1F3FD}', '\u{1F9D2}\u{1F3FE}', '\u{1F9D2}\u{1F3FF}',
  '\u{1F466}', '\u{1F466}\u{1F3FB}', '\u{1F466}\u{1F3FC}', '\u{1F466}\u{1F3FD}', '\u{1F466}\u{1F3FE}', '\u{1F466}\u{1F3FF}',
  '\u{1F467}', '\u{1F467}\u{1F3FB}', '\u{1F467}\u{1F3FC}', '\u{1F467}\u{1F3FD}', '\u{1F467}\u{1F3FE}', '\u{1F467}\u{1F3FF}',
  // Magical creatures
  '\u{1F984}', '\u{1F409}', '\u{1F432}', '\u{1F9DC}\u200D\u2640\uFE0F', '\u{1F9DC}\u200D\u2642\uFE0F',
  '\u{1F9DE}', '\u{1F9DE}\u200D\u2642\uFE0F', '\u{1F9DE}\u200D\u2640\uFE0F',
  // Cute animals (story characters)
  '\u{1F43B}', '\u{1F981}', '\u{1F430}', '\u{1F98A}', '\u{1F438}', '\u{1F422}', '\u{1F989}', '\u{1F427}',
  '\u{1F428}', '\u{1F43C}', '\u{1F98B}', '\u{1F431}', '\u{1F436}', '\u{1F42D}', '\u{1F439}', '\u{1F994}',
  // Storybook items
  '\u{1F4D6}', '\u{1FA84}', '\u{1F52E}', '\u{1F451}', '\u{1F3F0}', '\u{1F308}', '\u2B50', '\u{1F319}', '\u2728', '\u{1F4AB}',
];

interface BobbingCharacterProps {
  /** If true, cycles through random emojis. If false, stays on initial emoji. */
  cycling?: boolean;
  /** Interval in ms between emoji changes (default 600) */
  cycleInterval?: number;
  /** Font size for the emoji (default 120) */
  size?: number;
  /** Additional container styles */
  style?: ViewStyle;
}

/**
 * A large character emoji that bobs gently up and down,
 * optionally cycling through different story-themed emojis.
 */
export function BobbingCharacter({
  cycling = true,
  cycleInterval = 600,
  size = 120,
  style,
}: BobbingCharacterProps) {
  const [currentEmoji, setCurrentEmoji] = useState(storyEmojis[0]);

  const translateY = useSharedValue(0);
  const rotation = useSharedValue(-2);

  // Bobbing animation
  useEffect(() => {
    translateY.value = withRepeat(
      withSequence(
        withTiming(-8, { duration: 500, easing: Easing.inOut(Easing.ease) }),
        withTiming(0, { duration: 500, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      true
    );

    rotation.value = withRepeat(
      withSequence(
        withTiming(2, { duration: 500, easing: Easing.inOut(Easing.ease) }),
        withTiming(-2, { duration: 500, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      true
    );
  }, []);

  // Emoji cycling
  useEffect(() => {
    if (!cycling) return;

    const interval = setInterval(() => {
      const randomIndex = Math.floor(Math.random() * storyEmojis.length);
      setCurrentEmoji(storyEmojis[randomIndex]);
    }, cycleInterval);

    return () => clearInterval(interval);
  }, [cycling, cycleInterval]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateY: translateY.value },
      { rotate: `${rotation.value}deg` },
    ],
  }));

  return (
    <Animated.View style={[style, animatedStyle]}>
      <Text style={{ fontSize: size, lineHeight: size * 1.2 }}>
        {currentEmoji}
      </Text>
    </Animated.View>
  );
}
