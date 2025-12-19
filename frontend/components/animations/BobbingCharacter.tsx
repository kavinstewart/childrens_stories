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
  '🧙', '🧙‍♂️', '🧙‍♀️',
  '🧙🏻', '🧙🏼', '🧙🏽', '🧙🏾', '🧙🏿',
  // Fairies
  '🧚', '🧚‍♀️', '🧚‍♂️',
  '🧚🏻', '🧚🏼', '🧚🏽', '🧚🏾', '🧚🏿',
  // Royalty
  '🤴', '🤴🏻', '🤴🏼', '🤴🏽', '🤴🏾', '🤴🏿',
  '👸', '👸🏻', '👸🏼', '👸🏽', '👸🏾', '👸🏿',
  // Superheroes
  '🦸', '🦸‍♂️', '🦸‍♀️',
  '🦸🏻', '🦸🏼', '🦸🏽', '🦸🏾', '🦸🏿',
  // Children
  '🧒', '🧒🏻', '🧒🏼', '🧒🏽', '🧒🏾', '🧒🏿',
  '👦', '👦🏻', '👦🏼', '👦🏽', '👦🏾', '👦🏿',
  '👧', '👧🏻', '👧🏼', '👧🏽', '👧🏾', '👧🏿',
  // Magical creatures
  '🦄', '🐉', '🐲', '🧜‍♀️', '🧜‍♂️',
  '🧞', '🧞‍♂️', '🧞‍♀️',
  // Cute animals (story characters)
  '🐻', '🦁', '🐰', '🦊', '🐸', '🐢', '🦉', '🐧',
  '🐨', '🐼', '🦋', '🐱', '🐶', '🐭', '🐹', '🦔',
  // Storybook items
  '📖', '🪄', '🔮', '👑', '🏰', '🌈', '⭐', '🌙', '✨', '💫',
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
