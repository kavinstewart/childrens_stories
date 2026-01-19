/**
 * TappableText - Renders text with tappable words for TTS playback.
 *
 * Each word can be tapped to trigger TTS playback. Words briefly highlight
 * when tapped and can show a loading state during synthesis.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { Text, TextStyle, StyleProp } from 'react-native';

/**
 * Context information for a word, used for context-aware TTS caching.
 * The same word in different contexts may have different pronunciations.
 */
export interface WordContext {
  /** Position in sentence: start, mid, or end */
  position: 'start' | 'mid' | 'end';
  /** Punctuation following the word (empty string if none) */
  punctuation: string;
  /** Type of sentence based on ending punctuation */
  sentenceType: 'statement' | 'question' | 'exclamation';
  /** The full sentence containing this word (for synthesis) */
  sentence: string;
  /** Index of this word within the sentence */
  sentenceWordIndex: number;
}

export interface TappableTextProps {
  /** The full text to display */
  text: string;
  /** Base text style */
  style?: StyleProp<TextStyle>;
  /** Style for highlighted (tapped) word */
  highlightStyle?: StyleProp<TextStyle>;
  /** Style for word currently loading */
  loadingStyle?: StyleProp<TextStyle>;
  /** Index of word currently loading (-1 if none) */
  loadingWordIndex?: number;
  /** Called when a word is tapped */
  onWordPress?: (word: string, index: number, context: WordContext) => void;
  /** Duration to show highlight after tap (ms) */
  highlightDuration?: number;
}

interface WordWithWhitespace {
  word: string;
  /** Whitespace that appears BEFORE this word */
  precedingWhitespace: string;
}

/**
 * Split text into words while preserving the whitespace before each word.
 * This maintains newlines and other whitespace during rendering.
 */
function splitIntoWordsWithWhitespace(text: string): WordWithWhitespace[] {
  const result: WordWithWhitespace[] = [];
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

/**
 * Extract punctuation from a word (returns the word without punctuation and the punctuation)
 */
function extractPunctuation(word: string): { cleanWord: string; punctuation: string } {
  const match = word.match(/^(.+?)([.!?,;:'"]+)?$/);
  if (match) {
    return {
      cleanWord: match[1],
      punctuation: match[2] || '',
    };
  }
  return { cleanWord: word, punctuation: '' };
}

/**
 * Determine sentence type from text
 */
function getSentenceType(text: string): 'statement' | 'question' | 'exclamation' {
  const trimmed = text.trim();
  if (trimmed.endsWith('?')) return 'question';
  if (trimmed.endsWith('!')) return 'exclamation';
  return 'statement';
}

/**
 * Find the sentence containing a word at the given index
 */
function findSentenceForWord(
  words: WordWithWhitespace[],
  wordIndex: number
): { sentence: string; sentenceWordIndex: number; sentenceStart: number; sentenceEnd: number } {
  // Simple sentence detection: find sentence boundaries (. ! ?)
  let sentenceStart = 0;
  let sentenceEnd = words.length - 1;

  // Find start of sentence (look backwards for sentence-ending punctuation)
  for (let i = wordIndex - 1; i >= 0; i--) {
    if (/[.!?]$/.test(words[i].word)) {
      sentenceStart = i + 1;
      break;
    }
  }

  // Find end of sentence (look forwards for sentence-ending punctuation)
  for (let i = wordIndex; i < words.length; i++) {
    if (/[.!?]$/.test(words[i].word)) {
      sentenceEnd = i;
      break;
    }
  }

  // Build sentence text
  const sentenceWords = words.slice(sentenceStart, sentenceEnd + 1);
  const sentence = sentenceWords
    .map((w, i) => (i === 0 ? w.word : w.precedingWhitespace + w.word))
    .join('');

  return {
    sentence,
    sentenceWordIndex: wordIndex - sentenceStart,
    sentenceStart,
    sentenceEnd,
  };
}

/**
 * Build word context for TTS caching
 */
function buildWordContext(
  words: WordWithWhitespace[],
  wordIndex: number
): WordContext {
  const { sentence, sentenceWordIndex, sentenceStart, sentenceEnd } = findSentenceForWord(words, wordIndex);
  const word = words[wordIndex].word;
  const { punctuation } = extractPunctuation(word);

  // Determine position within sentence
  const sentenceLength = sentenceEnd - sentenceStart + 1;
  let position: 'start' | 'mid' | 'end';
  if (sentenceWordIndex === 0) {
    position = 'start';
  } else if (sentenceWordIndex === sentenceLength - 1) {
    position = 'end';
  } else {
    position = 'mid';
  }

  return {
    position,
    punctuation,
    sentenceType: getSentenceType(sentence),
    sentence,
    sentenceWordIndex,
  };
}

export function TappableText({
  text,
  style,
  highlightStyle,
  loadingStyle,
  loadingWordIndex = -1,
  onWordPress,
  highlightDuration = 300,
}: TappableTextProps) {
  const [tappedIndex, setTappedIndex] = useState<number>(-1);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wordsWithWhitespace = splitIntoWordsWithWhitespace(text);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const handleWordPress = useCallback((word: string, index: number) => {
    // Show highlight briefly
    setTappedIndex(index);
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      setTappedIndex(-1);
    }, highlightDuration);

    // Build context and call callback
    if (onWordPress) {
      const context = buildWordContext(wordsWithWhitespace, index);
      onWordPress(word, index, context);
    }
  }, [onWordPress, wordsWithWhitespace, highlightDuration]);

  // If no press handler, render as plain text
  if (!onWordPress) {
    return <Text style={style}>{text}</Text>;
  }

  return (
    <Text style={style}>
      {wordsWithWhitespace.map(({ word, precedingWhitespace }, index) => {
        const isTapped = index === tappedIndex;
        const isLoading = index === loadingWordIndex;
        const { cleanWord } = extractPunctuation(word);

        return (
          <Text key={index}>
            {precedingWhitespace}
            <Text
              onPress={() => handleWordPress(cleanWord, index)}
              style={[
                isTapped && highlightStyle,
                isLoading && (loadingStyle || { opacity: 0.6 }),
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
 * Default highlight style - golden background for tapped words
 */
export const defaultTapHighlightStyle: TextStyle = {
  backgroundColor: 'rgba(251, 191, 36, 0.4)', // Golden highlight
  borderRadius: 4,
};

/**
 * Default loading style - slightly faded
 */
export const defaultLoadingStyle: TextStyle = {
  opacity: 0.6,
};
