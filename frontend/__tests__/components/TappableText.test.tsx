/**
 * Tests for TappableText component
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { TappableText, WordContext } from '../../components/TappableText';

describe('TappableText', () => {
  const sampleText = 'Hello world how are you';

  describe('rendering', () => {
    it('renders plain text when no onWordPress provided', () => {
      const { toJSON } = render(<TappableText text={sampleText} />);
      const tree = toJSON();
      expect(tree?.children).toContain(sampleText);
    });

    it('renders words separately when onWordPress provided', () => {
      const onWordPress = jest.fn();
      const { toJSON } = render(
        <TappableText text={sampleText} onWordPress={onWordPress} />
      );
      const stringified = JSON.stringify(toJSON());
      // Each word should be present
      expect(stringified).toContain('Hello');
      expect(stringified).toContain('world');
      expect(stringified).toContain('how');
    });

    it('handles empty string', () => {
      const { toJSON } = render(<TappableText text="" />);
      expect(toJSON()).toBeTruthy();
    });
  });

  describe('whitespace preservation', () => {
    it('preserves newlines', () => {
      const textWithNewlines = 'Hello world\nNew line';
      const { toJSON } = render(
        <TappableText text={textWithNewlines} onWordPress={jest.fn()} />
      );

      const stringified = JSON.stringify(toJSON());
      expect(stringified).toContain('\\n');
    });

    it('preserves multiple spaces', () => {
      const { toJSON } = render(
        <TappableText text="Hello    world" onWordPress={jest.fn()} />
      );

      const stringified = JSON.stringify(toJSON());
      expect(stringified).toContain('Hello');
      expect(stringified).toContain('world');
    });
  });

  describe('loading state', () => {
    it('applies loading style to loading word', () => {
      const { toJSON } = render(
        <TappableText
          text="Hello world"
          onWordPress={jest.fn()}
          loadingWordIndex={1}
          loadingStyle={{ opacity: 0.5 }}
        />
      );

      const stringified = JSON.stringify(toJSON());
      expect(stringified).toContain('"opacity":0.5');
    });

    it('does not apply loading style when loadingWordIndex is -1', () => {
      const { toJSON } = render(
        <TappableText
          text="Hello world"
          onWordPress={jest.fn()}
          loadingWordIndex={-1}
          loadingStyle={{ opacity: 0.5 }}
        />
      );

      const stringified = JSON.stringify(toJSON());
      // 0.5 opacity should not be present when no word is loading
      expect(stringified).not.toContain('"opacity":0.5');
    });
  });
});

/**
 * Tests for helper functions - testing the context extraction logic directly
 * These test the internal logic that builds WordContext
 */
describe('TappableText WordContext logic', () => {
  // Helper to extract context by simulating a tap
  // We render and manually inspect the context passed to onWordPress
  function getContextForWordAtIndex(text: string, wordIndex: number): WordContext | null {
    let capturedContext: WordContext | null = null;
    const onWordPress = jest.fn((word, index, context) => {
      capturedContext = context;
    });

    const { UNSAFE_root } = render(
      <TappableText text={text} onWordPress={onWordPress} />
    );

    // Find all Text elements that have onPress handlers
    const findPressableTexts = (node: any): any[] => {
      const results: any[] = [];
      if (node?.props?.onPress) {
        results.push(node);
      }
      if (node?.children) {
        for (const child of node.children) {
          if (typeof child === 'object') {
            results.push(...findPressableTexts(child));
          }
        }
      }
      return results;
    };

    const pressableTexts = findPressableTexts(UNSAFE_root);
    if (pressableTexts[wordIndex]) {
      pressableTexts[wordIndex].props.onPress();
    }

    return capturedContext;
  }

  describe('word position detection', () => {
    it('detects start position for first word', () => {
      const context = getContextForWordAtIndex('Hello world today.', 0);
      expect(context?.position).toBe('start');
    });

    it('detects mid position for middle word', () => {
      const context = getContextForWordAtIndex('Hello world today.', 1);
      expect(context?.position).toBe('mid');
    });

    it('detects end position for last word', () => {
      const context = getContextForWordAtIndex('Hello world today.', 2);
      expect(context?.position).toBe('end');
    });
  });

  describe('sentence type detection', () => {
    it('detects question sentence type', () => {
      const context = getContextForWordAtIndex('How are you?', 1);
      expect(context?.sentenceType).toBe('question');
    });

    it('detects exclamation sentence type', () => {
      const context = getContextForWordAtIndex('Hello world!', 0);
      expect(context?.sentenceType).toBe('exclamation');
    });

    it('detects statement sentence type', () => {
      const context = getContextForWordAtIndex('Hello world.', 0);
      expect(context?.sentenceType).toBe('statement');
    });
  });

  describe('punctuation extraction', () => {
    it('extracts comma punctuation', () => {
      const context = getContextForWordAtIndex('Hello, world.', 0);
      expect(context?.punctuation).toBe(',');
    });

    it('extracts period punctuation', () => {
      const context = getContextForWordAtIndex('Hello world.', 1);
      expect(context?.punctuation).toBe('.');
    });

    it('extracts no punctuation for middle word', () => {
      const context = getContextForWordAtIndex('Hello my world.', 1);
      expect(context?.punctuation).toBe('');
    });
  });

  describe('sentence extraction', () => {
    it('extracts sentence for single sentence text', () => {
      const context = getContextForWordAtIndex('Hello world.', 0);
      expect(context?.sentence).toBe('Hello world.');
    });

    it('extracts correct sentence for multi-sentence text', () => {
      const context = getContextForWordAtIndex('First one. Second one.', 2);
      expect(context?.sentence).toBe('Second one.');
    });
  });

  describe('clean word in callback', () => {
    it('strips punctuation from word passed to callback', () => {
      const onWordPress = jest.fn();
      const { UNSAFE_root } = render(
        <TappableText text="Hello, world!" onWordPress={onWordPress} />
      );

      const findPressableTexts = (node: any): any[] => {
        const results: any[] = [];
        if (node?.props?.onPress) {
          results.push(node);
        }
        if (node?.children) {
          for (const child of node.children) {
            if (typeof child === 'object') {
              results.push(...findPressableTexts(child));
            }
          }
        }
        return results;
      };

      const pressableTexts = findPressableTexts(UNSAFE_root);

      // Press first word "Hello,"
      pressableTexts[0].props.onPress();
      expect(onWordPress).toHaveBeenLastCalledWith('Hello', 0, expect.any(Object));

      // Press second word "world!"
      pressableTexts[1].props.onPress();
      expect(onWordPress).toHaveBeenLastCalledWith('world', 1, expect.any(Object));
    });
  });
});
