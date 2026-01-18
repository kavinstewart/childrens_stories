/**
 * Tests for homograph detection and phoneme formatting
 */

import {
  HOMOGRAPHS,
  isHomograph,
  getHomographEntry,
  formatPhonemes,
  getDisambiguationPrompt,
} from '../../../lib/voice/homographs';

describe('homographs', () => {
  describe('HOMOGRAPHS lookup table', () => {
    it('contains read with two pronunciations', () => {
      expect(HOMOGRAPHS.read).toBeDefined();
      expect(HOMOGRAPHS.read.pronunciations).toHaveLength(2);
      expect(HOMOGRAPHS.read.meanings).toHaveLength(2);
    });

    it('contains lead with two pronunciations', () => {
      expect(HOMOGRAPHS.lead).toBeDefined();
      expect(HOMOGRAPHS.lead.pronunciations).toHaveLength(2);
    });

    it('contains bow with two pronunciations', () => {
      expect(HOMOGRAPHS.bow).toBeDefined();
      expect(HOMOGRAPHS.bow.pronunciations).toHaveLength(2);
    });

    it('has correct phoneme format for read (present tense)', () => {
      // Present tense: /riːd/
      expect(HOMOGRAPHS.read.pronunciations[0]).toBe('ɹ|iː|d');
    });

    it('has correct phoneme format for read (past tense)', () => {
      // Past tense: /rɛd/
      expect(HOMOGRAPHS.read.pronunciations[1]).toBe('ɹ|ɛ|d');
    });
  });

  describe('isHomograph', () => {
    it('returns true for known homographs', () => {
      expect(isHomograph('read')).toBe(true);
      expect(isHomograph('lead')).toBe(true);
      expect(isHomograph('bow')).toBe(true);
      expect(isHomograph('wind')).toBe(true);
    });

    it('returns false for non-homographs', () => {
      expect(isHomograph('hello')).toBe(false);
      expect(isHomograph('world')).toBe(false);
      expect(isHomograph('cat')).toBe(false);
    });

    it('is case-insensitive', () => {
      expect(isHomograph('READ')).toBe(true);
      expect(isHomograph('Read')).toBe(true);
      expect(isHomograph('LEAD')).toBe(true);
    });

    it('handles words with punctuation', () => {
      expect(isHomograph('read,')).toBe(true);
      expect(isHomograph('read.')).toBe(true);
      expect(isHomograph('"read"')).toBe(true);
    });
  });

  describe('getHomographEntry', () => {
    it('returns entry for known homographs', () => {
      const entry = getHomographEntry('read');
      expect(entry).not.toBeNull();
      expect(entry?.pronunciations).toHaveLength(2);
      expect(entry?.meanings).toHaveLength(2);
    });

    it('returns null for non-homographs', () => {
      expect(getHomographEntry('hello')).toBeNull();
    });

    it('normalizes case', () => {
      const entry = getHomographEntry('READ');
      expect(entry).not.toBeNull();
    });
  });

  describe('formatPhonemes', () => {
    it('wraps phonemes in Cartesia syntax', () => {
      expect(formatPhonemes('ɹ|iː|d')).toBe('<<ɹ|iː|d>>');
    });

    it('handles already formatted phonemes', () => {
      // Should not double-wrap
      expect(formatPhonemes('<<ɹ|iː|d>>')).toBe('<<ɹ|iː|d>>');
    });

    it('formats complex phoneme strings', () => {
      expect(formatPhonemes('k|ɑ|n|t|ɹ|æ|k|t')).toBe('<<k|ɑ|n|t|ɹ|æ|k|t>>');
    });
  });

  describe('getDisambiguationPrompt', () => {
    it('generates prompt for read in present context', () => {
      const prompt = getDisambiguationPrompt('read', 'I read books every day.');
      expect(prompt).toContain('read');
      expect(prompt).toContain('I read books every day.');
      expect(prompt).toContain('0)');
      expect(prompt).toContain('1)');
    });

    it('includes both meanings in the prompt', () => {
      const prompt = getDisambiguationPrompt('lead', 'She will lead the team.');
      expect(prompt).toContain('verb');
      expect(prompt).toContain('noun');
    });

    it('returns null for non-homographs', () => {
      expect(getDisambiguationPrompt('hello', 'Hello world')).toBeNull();
    });
  });

  describe('stress-shift homographs', () => {
    it('contains record with two pronunciations', () => {
      expect(HOMOGRAPHS.record).toBeDefined();
      expect(HOMOGRAPHS.record.pronunciations).toHaveLength(2);
    });

    it('contains present with two pronunciations', () => {
      expect(HOMOGRAPHS.present).toBeDefined();
      expect(HOMOGRAPHS.present.pronunciations).toHaveLength(2);
    });

    it('contains produce with two pronunciations', () => {
      expect(HOMOGRAPHS.produce).toBeDefined();
      expect(HOMOGRAPHS.produce.pronunciations).toHaveLength(2);
    });
  });
});
