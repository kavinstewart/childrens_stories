/**
 * KaraokeText - Renders text with karaoke-style word highlighting.
 *
 * Highlights the current word being spoken based on TTS timestamps.
 */

import { Text, TextStyle, StyleProp } from 'react-native';

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

interface WordWithWhitespace {
  word: string;
  /** Whitespace that appears BEFORE this word */
  precedingWhitespace: string;
}

/**
 * Split text into words while preserving the whitespace before each word.
 * This allows us to maintain newlines and other whitespace during karaoke rendering.
 */
function splitIntoWordsWithWhitespace(text: string): WordWithWhitespace[] {
  const result: WordWithWhitespace[] = [];
  // Match: optional whitespace followed by non-whitespace word
  const regex = /(\s*)(\S+)/g;
  let match;

  while ((match = regex.exec(text)) !== null) {
    result.push({
      precedingWhitespace: match[1],
      word: match[2],
    });
  }

  return result;
}

export function KaraokeText({
  text,
  currentWordIndex,
  isActive,
  style,
  highlightStyle,
}: KaraokeTextProps) {
  const wordsWithWhitespace = splitIntoWordsWithWhitespace(text);

  if (!isActive || currentWordIndex < 0) {
    // Not in karaoke mode - render plain text
    return <Text style={style}>{text}</Text>;
  }

  // Render with highlighted word, preserving original whitespace
  return (
    <Text style={style}>
      {wordsWithWhitespace.map(({ word, precedingWhitespace }, index) => {
        const isHighlighted = index === currentWordIndex;
        const isSpoken = index < currentWordIndex;

        return (
          <Text key={index}>
            {precedingWhitespace}
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
