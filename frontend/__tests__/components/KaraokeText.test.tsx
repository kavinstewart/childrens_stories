/**
 * Tests for KaraokeText component
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { KaraokeText, defaultHighlightStyle } from '../../components/KaraokeText';

describe('KaraokeText', () => {
  const sampleText = 'Hello world how are you';

  describe('when inactive', () => {
    it('renders plain text when isActive is false', () => {
      const { toJSON } = render(
        <KaraokeText
          text={sampleText}
          currentWordIndex={2}
          isActive={false}
        />
      );

      const tree = toJSON();
      // When inactive, renders as single Text with full content
      expect(tree?.children).toContain(sampleText);
    });

    it('renders plain text when currentWordIndex is -1', () => {
      const { toJSON } = render(
        <KaraokeText
          text={sampleText}
          currentWordIndex={-1}
          isActive={true}
        />
      );

      const tree = toJSON();
      expect(tree?.children).toContain(sampleText);
    });
  });

  describe('when active', () => {
    it('renders words separately when active', () => {
      const { toJSON } = render(
        <KaraokeText
          text={sampleText}
          currentWordIndex={0}
          isActive={true}
        />
      );

      const tree = toJSON();
      // When active, should have children (nested structure)
      expect(tree?.children?.length).toBeGreaterThan(0);
    });

    it('applies highlight style to current word', () => {
      const customHighlight = { backgroundColor: 'red' };
      const { toJSON } = render(
        <KaraokeText
          text="Hello world"
          currentWordIndex={1}
          isActive={true}
          highlightStyle={customHighlight}
        />
      );

      // Find the highlighted word in the tree
      const tree = toJSON();
      const stringified = JSON.stringify(tree);

      // Should contain the highlight style (red -> rgba(255,0,0,...))
      expect(stringified).toContain('backgroundColor');
      expect(stringified).toContain('255,0,0');
    });

    it('applies opacity to spoken words', () => {
      const { toJSON } = render(
        <KaraokeText
          text="Hello world how"
          currentWordIndex={2}
          isActive={true}
        />
      );

      // Words before currentWordIndex should have reduced opacity
      const stringified = JSON.stringify(toJSON());
      expect(stringified).toContain('"opacity":0.7');
    });
  });

  describe('splitIntoWords behavior', () => {
    it('handles multiple spaces between words', () => {
      const { toJSON } = render(
        <KaraokeText
          text="Hello    world"
          currentWordIndex={0}
          isActive={true}
        />
      );

      const stringified = JSON.stringify(toJSON());
      // Should contain both words despite multiple spaces
      expect(stringified).toContain('Hello');
      expect(stringified).toContain('world');
    });

    it('handles leading/trailing whitespace', () => {
      const { toJSON } = render(
        <KaraokeText
          text="  Hello world  "
          currentWordIndex={0}
          isActive={true}
        />
      );

      const stringified = JSON.stringify(toJSON());
      expect(stringified).toContain('Hello');
      expect(stringified).toContain('world');
    });

    it('handles empty string', () => {
      const { toJSON } = render(
        <KaraokeText
          text=""
          currentWordIndex={0}
          isActive={true}
        />
      );

      const tree = toJSON();
      // Should render without crashing
      expect(tree).toBeTruthy();
    });
  });

  describe('defaultHighlightStyle', () => {
    it('has expected properties', () => {
      expect(defaultHighlightStyle.backgroundColor).toBeDefined();
      expect(defaultHighlightStyle.borderRadius).toBeDefined();
    });
  });
});
