/**
 * KaraokeText - Renders text with karaoke-style word highlighting.
 *
 * Highlights the current word being spoken based on TTS timestamps.
 */

import { Text, TextStyle, StyleProp } from 'react-native';
import Animated, {
  useAnimatedStyle,
  withTiming,
  Easing,
} from 'react-native-reanimated';

interface KaraokeTextProps {
  /** The full text to display */
  text: string;
  /** Index of the currently highlighted word (-1 for no highlight) */
  currentWordIndex: number;
  /** Whether karaoke mode is active */
  isActive: boolean;
  /** Base text style */
  style?: StyleProp<TextStyle>;
  /** Style for the highlighted word */
  highlightStyle?: StyleProp<TextStyle>;
}

const AnimatedText = Animated.createAnimatedComponent(Text);

/**
 * Split text into words while preserving whitespace for proper rendering.
 */
function splitIntoWords(text: string): string[] {
  // Split on whitespace but keep words only
  return text.split(/\s+/).filter(word => word.length > 0);
}

export function KaraokeText({
  text,
  currentWordIndex,
  isActive,
  style,
  highlightStyle,
}: KaraokeTextProps) {
  const words = splitIntoWords(text);

  if (!isActive || currentWordIndex < 0) {
    // Not in karaoke mode - render plain text
    return <Text style={style}>{text}</Text>;
  }

  // Render with highlighted word
  return (
    <Text style={style}>
      {words.map((word, index) => {
        const isHighlighted = index === currentWordIndex;
        const isSpoken = index < currentWordIndex;

        return (
          <Text key={index}>
            {index > 0 ? ' ' : ''}
            <Text
              style={[
                isHighlighted && highlightStyle,
                isSpoken && { opacity: 0.7 },
              ]}
            >
              {word}
            </Text>
          </Text>
        );
      })}
    </Text>
  );
}

/**
 * Default highlight style - subtle background highlight
 */
export const defaultHighlightStyle: TextStyle = {
  backgroundColor: 'rgba(139, 92, 246, 0.25)', // Purple tint
  borderRadius: 4,
};
