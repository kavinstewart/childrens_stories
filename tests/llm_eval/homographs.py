"""
Homograph data for LLM evaluation.

This mirrors the data in frontend/lib/voice/homographs.ts for Python-based testing.
"""

import re
from typing import TypedDict


class HomographEntry(TypedDict):
    pronunciations: tuple[str, str]  # IPA phonemes for TTS
    spellings: tuple[str, str]  # Human-readable phonetic spellings for LLM


# Complete lookup table of English homographs
# Index 0 and 1 correspond to different pronunciations
# spellings: phonetic spellings the LLM can understand (used in disambiguation prompt)
# pronunciations: IPA phonemes for TTS system
HOMOGRAPHS: dict[str, HomographEntry] = {
    # === VOWEL/CONSONANT CHANGES ===
    "read": {
        "pronunciations": ("ɹ|iː|d", "ɹ|ɛ|d"),
        "spellings": ("REED (present/future/infinitive: I read, will read, to read, did read)", "RED (past/perfect: I read yesterday, have read, had read)"),
    },
    "lead": {
        "pronunciations": ("l|iː|d", "l|ɛ|d"),
        "spellings": ("LEED (to guide)", "LED (the metal)"),
    },
    "live": {
        "pronunciations": ("l|ɪ|v", "l|aj|v"),
        "spellings": ("LIV (verb: to live, I live, we live)", "LYVE (adjective: live music, live broadcast)"),
    },
    "wind": {
        "pronunciations": ("w|ɪ|n|d", "w|aj|n|d"),
        "spellings": ("WIND (air/breeze)", "WYND (to turn/coil)"),
    },
    "wound": {
        "pronunciations": ("w|ʉː|n|d", "w|aw|n|d"),
        "spellings": ("WOOND (an injury)", "WOWND (past tense of wind)"),
    },
    "tear": {
        "pronunciations": ("t|ɪ|ɹ", "t|ɛ|ɹ"),
        "spellings": ("TEER (from crying)", "TARE (to rip)"),
    },
    "bow": {
        "pronunciations": ("b|ow", "b|aw"),
        "spellings": ("BOH (ribbon/weapon, rhymes with go)", "BAO (bend at waist, rhymes with cow)"),
    },
    "row": {
        "pronunciations": ("ɹ|ow", "ɹ|aw"),
        "spellings": ("ROH (a line of things)", "ROW (an argument)"),
    },
    "sow": {
        "pronunciations": ("s|ow", "s|aw"),
        "spellings": ("SOH (to plant seeds)", "SOW (a female pig)"),
    },
    "bass": {
        "pronunciations": ("b|ej|s", "b|æ|s"),
        "spellings": ("BASE (low sound/instrument)", "BASS (the fish)"),
    },
    "close": {
        "pronunciations": ("k|l|ow|z", "k|l|ow|s"),
        "spellings": ("CLOZE (verb: to close, close the door)", "CLOSS (adjective: close to, a close race, close call, close watch)"),
    },
    "use": {
        "pronunciations": ("j|ʉː|z", "j|ʉː|s"),
        "spellings": ("YOOZ (verb: to use, I use)", "YOOS (noun: the use, no use, of use)"),
    },
    "house": {
        "pronunciations": ("h|aw|s", "h|aw|z"),
        "spellings": ("HOWSS (noun)", "HOWZZ (verb)"),
    },
    "excuse": {
        "pronunciations": ("ɪ|k|s|k|j|ʉː|z", "ɪ|k|s|k|j|ʉː|s"),
        "spellings": ("eks-KYOOZ (verb: to excuse, excuse me)", "eks-KYOOS (noun: an excuse, the excuse)"),
    },
    "dove": {
        "pronunciations": ("d|ɐ|v", "d|ow|v"),
        "spellings": ("DUV (the bird)", "DOHV (past tense of dive)"),
    },
    "does": {
        "pronunciations": ("d|ɐ|z", "d|ow|z"),
        "spellings": ("DUZ (verb)", "DOZE (female deer)"),
    },
    "sewer": {
        "pronunciations": ("s|ʉː|ɚ", "s|ow|ɚ"),
        "spellings": ("SOO-er (drainage pipe)", "SOH-er (one who sews)"),
    },
    "polish": {
        "pronunciations": ("p|ɑ|l|ɪ|ʃ", "p|ow|l|ɪ|ʃ"),
        "spellings": ("PAH-lish (to shine)", "POH-lish (from Poland)"),
    },
    # === STRESS SHIFT (noun=1st syllable, verb=2nd syllable) ===
    "present": {
        "pronunciations": ("p|ɹ|ɛ|z|ə|n|t", "p|ɹ|ɪ|z|ɛ|n|t"),
        "spellings": ("PREH-zent (a gift)", "prih-ZENT (to show)"),
    },
    "record": {
        "pronunciations": ("ɹ|ɛ|k|ɚ|d", "ɹ|ɪ|k|ɔ|ɹ|d"),
        "spellings": ("REH-kerd (noun: the record, a record, vinyl record, world record)", "rih-KORD (verb: to record, will record)"),
    },
    "produce": {
        "pronunciations": ("p|ɹ|ɑ|d|ʉː|s", "p|ɹ|ə|d|ʉː|s"),
        "spellings": ("PRAH-doos (vegetables)", "pruh-DOOS (to make)"),
    },
    "object": {
        "pronunciations": ("ɑ|b|dʒ|ɛ|k|t", "ə|b|dʒ|ɛ|k|t"),
        "spellings": ("AHB-jekt (a thing)", "uhb-JEKT (to protest)"),
    },
    "content": {
        "pronunciations": ("k|ɑ|n|t|ɛ|n|t", "k|ə|n|t|ɛ|n|t"),
        "spellings": ("KAHN-tent (substance)", "kuhn-TENT (satisfied)"),
    },
    "contract": {
        "pronunciations": ("k|ɑ|n|t|ɹ|æ|k|t", "k|ə|n|t|ɹ|æ|k|t"),
        "spellings": ("KAHN-trakt (document)", "kuhn-TRAKT (to shrink)"),
    },
    "refuse": {
        "pronunciations": ("ɹ|ɛ|f|j|ʉː|s", "ɹ|ɪ|f|j|ʉː|z"),
        "spellings": ("REH-fyoos (garbage)", "rih-FYOOZ (to decline)"),
    },
    "desert": {
        "pronunciations": ("d|ɛ|z|ɚ|t", "d|ɪ|z|ɝ|t"),
        "spellings": ("DEH-zert (sandy place)", "dih-ZERT (to abandon)"),
    },
    "minute": {
        "pronunciations": ("m|ɪ|n|ɪ|t", "m|aj|n|ʉː|t"),
        "spellings": ("MIH-nit (60 seconds)", "my-NOOT (very small)"),
    },
    "separate": {
        "pronunciations": ("s|ɛ|p|ɚ|ɪ|t", "s|ɛ|p|ə|ɹ|ej|t"),
        "spellings": ("SEH-prit (adjective: separate rooms, their separate ways)", "SEH-puh-rayt (verb: to separate)"),
    },
    "alternate": {
        "pronunciations": ("ɔ|l|t|ɚ|n|ɪ|t", "ɔ|l|t|ɚ|n|ej|t"),
        "spellings": ("AWL-ter-nit (noun/adj: an alternate, alternate route)", "AWL-ter-nayt (verb: to alternate)"),
    },
    "attribute": {
        "pronunciations": ("æ|t|ɹ|ɪ|b|j|ʉː|t", "ə|t|ɹ|ɪ|b|j|ʉː|t"),
        "spellings": ("AT-trih-byoot (noun: an attribute, key attribute)", "uh-TRIH-byoot (verb: to attribute, attribute it to)"),
    },
    "entrance": {
        "pronunciations": ("ɛ|n|t|ɹ|ə|n|s", "ɪ|n|t|ɹ|æ|n|s"),
        "spellings": ("EN-trunss (a doorway)", "en-TRANSS (to captivate)"),
    },
    "graduate": {
        "pronunciations": ("ɡ|ɹ|æ|dʒ|ʉ|ɪ|t", "ɡ|ɹ|æ|dʒ|ʉ|ej|t"),
        "spellings": ("GRAJ-oo-it (a person)", "GRAJ-oo-ayt (to complete)"),
    },
    "buffet": {
        "pronunciations": ("b|ə|f|ej", "b|ɐ|f|ɪ|t"),
        "spellings": ("buh-FAY (food spread)", "BUH-fit (to strike)"),
    },
    "permit": {
        "pronunciations": ("p|ɝ|m|ɪ|t", "p|ɚ|m|ɪ|t"),
        "spellings": ("PER-mit (a license)", "per-MIT (to allow)"),
    },
    "conduct": {
        "pronunciations": ("k|ɑ|n|d|ɐ|k|t", "k|ə|n|d|ɐ|k|t"),
        "spellings": ("KAHN-dukt (behavior)", "kuhn-DUKT (to lead)"),
    },
    "conflict": {
        "pronunciations": ("k|ɑ|n|f|l|ɪ|k|t", "k|ə|n|f|l|ɪ|k|t"),
        "spellings": ("KAHN-flikt (noun: a conflict, the conflict)", "kuhn-FLIKT (verb: to conflict, stories conflict)"),
    },
    "contest": {
        "pronunciations": ("k|ɑ|n|t|ɛ|s|t", "k|ə|n|t|ɛ|s|t"),
        "spellings": ("KAHN-test (noun: a contest, the contest)", "kuhn-TEST (verb: to contest, will contest)"),
    },
    "convert": {
        "pronunciations": ("k|ɑ|n|v|ɝ|t", "k|ə|n|v|ɝ|t"),
        "spellings": ("KAHN-vert (a person)", "kuhn-VERT (to change)"),
    },
    "convict": {
        "pronunciations": ("k|ɑ|n|v|ɪ|k|t", "k|ə|n|v|ɪ|k|t"),
        "spellings": ("KAHN-vikt (a prisoner)", "kuhn-VIKT (to find guilty)"),
    },
    "insert": {
        "pronunciations": ("ɪ|n|s|ɝ|t", "ɪ|n|s|ɝ|t"),
        "spellings": ("IN-sert (something added)", "in-SERT (to put in)"),
    },
    "invalid": {
        "pronunciations": ("ɪ|n|v|ə|l|ɪ|d", "ɪ|n|v|æ|l|ɪ|d"),
        "spellings": ("IN-vuh-lid (a sick person)", "in-VAL-id (not valid)"),
    },
    "project": {
        "pronunciations": ("p|ɹ|ɑ|dʒ|ɛ|k|t", "p|ɹ|ə|dʒ|ɛ|k|t"),
        "spellings": ("PRAH-jekt (a task)", "pruh-JEKT (to display)"),
    },
    "rebel": {
        "pronunciations": ("ɹ|ɛ|b|əl", "ɹ|ɪ|b|ɛ|l"),
        "spellings": ("REH-bel (a person)", "rih-BEL (to resist)"),
    },
    "subject": {
        "pronunciations": ("s|ɐ|b|dʒ|ɪ|k|t", "s|ə|b|dʒ|ɛ|k|t"),
        "spellings": ("SUB-jekt (a topic)", "sub-JEKT (to expose to)"),
    },
    "suspect": {
        "pronunciations": ("s|ɐ|s|p|ɛ|k|t", "s|ə|s|p|ɛ|k|t"),
        "spellings": ("SUS-pekt (a person)", "suh-SPEKT (to doubt)"),
    },
    "console": {
        "pronunciations": ("k|ɑ|n|s|ow|l", "k|ə|n|s|ow|l"),
        "spellings": ("KAHN-sole (a device)", "kuhn-SOLE (to comfort)"),
    },
    "resume": {
        "pronunciations": ("ɹ|ɛ|z|ə|m|ej", "ɹ|ɪ|z|ʉː|m"),
        "spellings": ("REH-zoo-may (a document)", "rih-ZOOM (to continue)"),
    },
}


def get_disambiguation_prompt(
    word: str, sentence: str, no_think: bool = True, occurrence: int = 1
) -> str | None:
    """
    Generate an LLM disambiguation prompt for a homograph in context.
    Returns None if the word is not a homograph.

    Args:
        word: The homograph word to disambiguate
        sentence: The sentence containing the word
        no_think: If True, append /no_think to disable reasoning mode (for Qwen3 etc.)
        occurrence: Which occurrence of the word to ask about (1-indexed, default 1)
    """
    normalized = word.lower().strip()
    entry = HOMOGRAPHS.get(normalized)
    if not entry:
        return None

    # Count word-boundary occurrences (not substrings like "read" in "already")
    word_pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    word_count = len(word_pattern.findall(sentence))

    # Only highlight and add hint when there are multiple occurrences
    if word_count > 1:
        highlighted_sentence = _highlight_occurrence(sentence, word, occurrence)
        ordinal = {1: "first", 2: "second", 3: "third"}.get(occurrence, f"#{occurrence}")
        occurrence_hint = f" (the {ordinal} one, marked with **)"
    else:
        highlighted_sentence = sentence
        occurrence_hint = ""

    # Use phonetic spellings that LLMs can understand
    prompt = f"""In the sentence "{highlighted_sentence}", how is "{word}"{occurrence_hint} pronounced?
0) {entry["spellings"][0]}
1) {entry["spellings"][1]}

Reply with just 0 or 1."""

    if no_think:
        prompt += " /no_think"

    return prompt


def _highlight_occurrence(sentence: str, word: str, occurrence: int) -> str:
    """Highlight the nth occurrence of a word in a sentence with **asterisks**."""
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    matches = list(pattern.finditer(sentence))

    if occurrence < 1 or occurrence > len(matches):
        return sentence  # Return unchanged if occurrence is out of range

    match = matches[occurrence - 1]
    return sentence[: match.start()] + f"**{match.group()}**" + sentence[match.end() :]
