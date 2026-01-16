/**
 * Homograph detection and phoneme lookup for TTS.
 *
 * Homographs are words spelled the same but pronounced differently based on meaning.
 * This module provides lookup tables and utilities for disambiguating pronunciation.
 *
 * Phonemes use Cartesia MFA-style IPA format (no stress markers).
 * See: https://docs.cartesia.ai/build-with-cartesia/sonic-3/custom-pronunciations
 */

export interface HomographEntry {
  /** Pipe-separated phoneme strings for each pronunciation */
  pronunciations: [string, string];
  /** Brief meanings to help LLM disambiguate */
  meanings: [string, string];
}

/**
 * Complete lookup table of English homographs with their pronunciations.
 * Index 0 and 1 correspond to different meanings/pronunciations.
 */
export const HOMOGRAPHS: Record<string, HomographEntry> = {
  // === VOWEL/CONSONANT CHANGES ===
  read: {
    pronunciations: ['ɹ|iː|d', 'ɹ|ɛ|d'],
    meanings: ['present tense verb (I read books daily)', 'past tense verb (I read it yesterday)'],
  },
  lead: {
    pronunciations: ['l|iː|d', 'l|ɛ|d'],
    meanings: ['verb (to lead the way)', 'noun (the metal lead)'],
  },
  live: {
    pronunciations: ['l|ɪ|v', 'l|aj|v'],
    meanings: ['verb (I live here)', 'adjective (live music)'],
  },
  wind: {
    pronunciations: ['w|ɪ|n|d', 'w|aj|n|d'],
    meanings: ['noun (the wind blows)', 'verb (wind the clock)'],
  },
  wound: {
    pronunciations: ['w|ʉː|n|d', 'w|aw|n|d'],
    meanings: ['noun (a wound on his arm)', 'past tense of wind (wound the string)'],
  },
  tear: {
    pronunciations: ['t|ɪ|ɹ', 't|ɛ|ɹ'],
    meanings: ['noun (a tear from her eye)', 'verb (tear the paper)'],
  },
  bow: {
    pronunciations: ['b|ow', 'b|aw'],
    meanings: ['noun (a bow and arrow / hair bow)', 'verb (bow to the queen)'],
  },
  row: {
    pronunciations: ['ɹ|ow', 'ɹ|aw'],
    meanings: ['noun (a row of seats)', 'noun (a heated argument)'],
  },
  sow: {
    pronunciations: ['s|ow', 's|aw'],
    meanings: ['verb (sow the seeds)', 'noun (a female pig)'],
  },
  bass: {
    pronunciations: ['b|ej|s', 'b|æ|s'],
    meanings: ['noun (bass guitar / low voice)', 'noun (bass fish)'],
  },
  close: {
    pronunciations: ['k|l|ow|z', 'k|l|ow|s'],
    meanings: ['verb (close the door)', 'adjective (close to home)'],
  },
  use: {
    pronunciations: ['j|ʉː|z', 'j|ʉː|s'],
    meanings: ['verb (use the tool)', 'noun (no use trying)'],
  },
  house: {
    pronunciations: ['h|aw|s', 'h|aw|z'],
    meanings: ['noun (the house)', 'verb (house the refugees)'],
  },
  excuse: {
    pronunciations: ['ɪ|k|s|k|j|ʉː|z', 'ɪ|k|s|k|j|ʉː|s'],
    meanings: ['verb (excuse me)', 'noun (a poor excuse)'],
  },
  dove: {
    pronunciations: ['d|ɐ|v', 'd|ow|v'],
    meanings: ['noun (a white dove)', 'past tense of dive (she dove into the pool)'],
  },
  does: {
    pronunciations: ['d|ɐ|z', 'd|ow|z'],
    meanings: ['verb (she does it)', 'noun (female deer)'],
  },
  sewer: {
    pronunciations: ['s|ʉː|ɚ', 's|ow|ɚ'],
    meanings: ['noun (the sewer pipe)', 'noun (one who sews)'],
  },
  polish: {
    pronunciations: ['p|ɑ|l|ɪ|ʃ', 'p|ow|l|ɪ|ʃ'],
    meanings: ['verb (polish the shoes)', 'adjective (Polish language)'],
  },

  // === STRESS SHIFT (noun=1st syllable, verb=2nd syllable) ===
  present: {
    pronunciations: ['p|ɹ|ɛ|z|ə|n|t', 'p|ɹ|ɪ|z|ɛ|n|t'],
    meanings: ['noun (a birthday present)', 'verb (present the award)'],
  },
  record: {
    pronunciations: ['ɹ|ɛ|k|ɚ|d', 'ɹ|ɪ|k|ɔ|ɹ|d'],
    meanings: ['noun (a vinyl record)', 'verb (record a song)'],
  },
  produce: {
    pronunciations: ['p|ɹ|ɑ|d|ʉː|s', 'p|ɹ|ə|d|ʉː|s'],
    meanings: ['noun (fresh produce)', 'verb (produce results)'],
  },
  object: {
    pronunciations: ['ɑ|b|dʒ|ɛ|k|t', 'ə|b|dʒ|ɛ|k|t'],
    meanings: ['noun (a shiny object)', 'verb (I object!)'],
  },
  content: {
    pronunciations: ['k|ɑ|n|t|ɛ|n|t', 'k|ə|n|t|ɛ|n|t'],
    meanings: ['noun (the content of the book)', 'adjective (feeling content)'],
  },
  contract: {
    pronunciations: ['k|ɑ|n|t|ɹ|æ|k|t', 'k|ə|n|t|ɹ|æ|k|t'],
    meanings: ['noun (sign the contract)', 'verb (muscles contract)'],
  },
  refuse: {
    pronunciations: ['ɹ|ɛ|f|j|ʉː|s', 'ɹ|ɪ|f|j|ʉː|z'],
    meanings: ['noun (refuse/garbage)', 'verb (refuse to go)'],
  },
  desert: {
    pronunciations: ['d|ɛ|z|ɚ|t', 'd|ɪ|z|ɝ|t'],
    meanings: ['noun (the Sahara desert)', 'verb (desert the army)'],
  },
  minute: {
    pronunciations: ['m|ɪ|n|ɪ|t', 'm|aj|n|ʉː|t'],
    meanings: ['noun (one minute)', 'adjective (minute details)'],
  },
  separate: {
    pronunciations: ['s|ɛ|p|ɚ|ɪ|t', 's|ɛ|p|ə|ɹ|ej|t'],
    meanings: ['adjective (separate rooms)', 'verb (separate the items)'],
  },
  alternate: {
    pronunciations: ['ɔ|l|t|ɚ|n|ɪ|t', 'ɔ|l|t|ɚ|n|ej|t'],
    meanings: ['noun/adjective (an alternate route)', 'verb (alternate between)'],
  },
  attribute: {
    pronunciations: ['æ|t|ɹ|ɪ|b|j|ʉː|t', 'ə|t|ɹ|ɪ|b|j|ʉː|t'],
    meanings: ['noun (a key attribute)', 'verb (attribute to luck)'],
  },
  entrance: {
    pronunciations: ['ɛ|n|t|ɹ|ə|n|s', 'ɪ|n|t|ɹ|æ|n|s'],
    meanings: ['noun (the main entrance)', 'verb (entrance the audience)'],
  },
  graduate: {
    pronunciations: ['ɡ|ɹ|æ|dʒ|ʉ|ɪ|t', 'ɡ|ɹ|æ|dʒ|ʉ|ej|t'],
    meanings: ['noun (a college graduate)', 'verb (graduate from school)'],
  },
  buffet: {
    pronunciations: ['b|ə|f|ej', 'b|ɐ|f|ɪ|t'],
    meanings: ['noun (a breakfast buffet)', 'verb (winds buffet the coast)'],
  },
  permit: {
    pronunciations: ['p|ɝ|m|ɪ|t', 'p|ɚ|m|ɪ|t'],
    meanings: ['noun (a parking permit)', 'verb (permit entry)'],
  },
  conduct: {
    pronunciations: ['k|ɑ|n|d|ɐ|k|t', 'k|ə|n|d|ɐ|k|t'],
    meanings: ['noun (good conduct)', 'verb (conduct the orchestra)'],
  },
  conflict: {
    pronunciations: ['k|ɑ|n|f|l|ɪ|k|t', 'k|ə|n|f|l|ɪ|k|t'],
    meanings: ['noun (a conflict arose)', 'verb (schedules conflict)'],
  },
  contest: {
    pronunciations: ['k|ɑ|n|t|ɛ|s|t', 'k|ə|n|t|ɛ|s|t'],
    meanings: ['noun (a singing contest)', 'verb (contest the decision)'],
  },
  convert: {
    pronunciations: ['k|ɑ|n|v|ɝ|t', 'k|ə|n|v|ɝ|t'],
    meanings: ['noun (a religious convert)', 'verb (convert to metric)'],
  },
  convict: {
    pronunciations: ['k|ɑ|n|v|ɪ|k|t', 'k|ə|n|v|ɪ|k|t'],
    meanings: ['noun (an escaped convict)', 'verb (convict the defendant)'],
  },
  insert: {
    pronunciations: ['ɪ|n|s|ɝ|t', 'ɪ|n|s|ɝ|t'],
    meanings: ['noun (a magazine insert)', 'verb (insert the key)'],
  },
  invalid: {
    pronunciations: ['ɪ|n|v|ə|l|ɪ|d', 'ɪ|n|v|æ|l|ɪ|d'],
    meanings: ['noun (care for an invalid)', 'adjective (an invalid password)'],
  },
  project: {
    pronunciations: ['p|ɹ|ɑ|dʒ|ɛ|k|t', 'p|ɹ|ə|dʒ|ɛ|k|t'],
    meanings: ['noun (a school project)', 'verb (project an image)'],
  },
  rebel: {
    pronunciations: ['ɹ|ɛ|b|əl', 'ɹ|ɪ|b|ɛ|l'],
    meanings: ['noun (a rebel fighter)', 'verb (rebel against authority)'],
  },
  subject: {
    pronunciations: ['s|ɐ|b|dʒ|ɪ|k|t', 's|ə|b|dʒ|ɛ|k|t'],
    meanings: ['noun (the subject of the book)', 'verb (subject to questioning)'],
  },
  suspect: {
    pronunciations: ['s|ɐ|s|p|ɛ|k|t', 's|ə|s|p|ɛ|k|t'],
    meanings: ['noun (a prime suspect)', 'verb (I suspect fraud)'],
  },
  console: {
    pronunciations: ['k|ɑ|n|s|ow|l', 'k|ə|n|s|ow|l'],
    meanings: ['noun (a game console)', 'verb (console the grieving)'],
  },
  resume: {
    pronunciations: ['ɹ|ɛ|z|ə|m|ej', 'ɹ|ɪ|z|ʉː|m'],
    meanings: ['noun (submit a resume)', 'verb (resume the meeting)'],
  },
};

/**
 * Normalize a word for lookup (lowercase, strip punctuation).
 */
function normalizeWord(word: string): string {
  return word
    .toLowerCase()
    .replace(/^[^a-z]+/, '')
    .replace(/[^a-z]+$/, '');
}

/**
 * Check if a word is a homograph.
 */
export function isHomograph(word: string): boolean {
  return normalizeWord(word) in HOMOGRAPHS;
}

/**
 * Get the homograph entry for a word, or null if not a homograph.
 */
export function getHomographEntry(word: string): HomographEntry | null {
  const normalized = normalizeWord(word);
  return HOMOGRAPHS[normalized] ?? null;
}

/**
 * Format phonemes in Cartesia syntax: <<p|h|o|n|e|m|e|s>>
 */
export function formatPhonemes(phonemes: string): string {
  // Don't double-wrap
  if (phonemes.startsWith('<<') && phonemes.endsWith('>>')) {
    return phonemes;
  }
  return `<<${phonemes}>>`;
}

/**
 * Generate an LLM disambiguation prompt for a homograph in context.
 * Returns null if the word is not a homograph.
 */
export function getDisambiguationPrompt(word: string, sentence: string): string | null {
  const entry = getHomographEntry(word);
  if (!entry) {
    return null;
  }

  return `In the sentence "${sentence}", the word "${word}" means:
0) ${entry.meanings[0]}
1) ${entry.meanings[1]}

Reply with just 0 or 1.`;
}

/**
 * Get phonemes for a homograph given the disambiguation index.
 */
export function getPhonemes(word: string, index: 0 | 1): string | null {
  const entry = getHomographEntry(word);
  if (!entry) {
    return null;
  }
  return entry.pronunciations[index];
}
