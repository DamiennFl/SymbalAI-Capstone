from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import random
import math
NEGATIVE_INSTRUCTIONS: List[str] = ['Read quickly in a flat, mechanical tone. Keep timing uniform, minimal pauses at commas, and avoid any emotional emphasis.', 'Deliver as if reading from a script: fast pace, low pitch variation, short consistent breaks, and no expressive phrasing.', 'Sound like you are skimming notes aloud. Keep cadence steady, compress pauses, and remove natural rises and falls.', 'Monotone, efficient delivery. Even word spacing, little breath, no dramatic stress, and minimal sentence-end lift.', 'Read plainly and briskly. Suppress emotion, keep commas short and identical, and maintain a steady metronomic rhythm.', 'Use a neutral, office-like read. Fast tempo, clipped pauses, uniform intonation, and no conversational color.', 'Imagine a teleprompter read. Keep pace tight, flatten pitch, shorten commas, and avoid hesitations or fillers.', 'Mechanical narration. Keep every phrase similar length, low variability, minimal breath, and no warmth.', 'Deliver with zero flair: fast, flat, and evenly timed. Do not lean on keywords or vary pitch.', 'Plain list reading. Compress pauses, remove sentence curves, and maintain an unchanging speaking rate.', 'Keep tone dry. Fast articulation, identical comma breaks, little resonance, and no expressive dynamics.', 'Read at speed without personality. Avoid crescendos, keep timing clipped, and flatten any melodic contour.', 'Treat it like legal boilerplate. Uniform pacing, narrow pitch band, and minimal sentence-final intonation.', 'Low-variance narration. Fast tempo, identical clause breaks, and no natural conversational hesitation.', 'Deliver as an automated attendant. Even syllable spacing, soft edges, and suppressed dynamic range.', 'Read like meeting notes. Tight rhythm, shallow prosody, eliminate expressive stress on key terms.', 'Flat and functional. Keep breath noise low, pauses short, and pitch nearly constant across sentences.', 'Fast corporate read. No dramatic emphasis, concise commas, and a restrained, neutral delivery.', 'Keep cadence machine-like. Avoid micro-hesitations, reduce swing in timing, and keep pitch steady.', 'Neutral and brisk. Trim silences, keep phrase lengths uniform, and do not vary loudness meaningfully.', 'Read as if timing to a metronome. Fixed tempo, short comma pauses, and minimal pitch drift.', 'Instructional but impersonal. Maintain even timing, low energy variation, and no expressive cues.', 'Flat voiceover. Avoid contouring sentences; end stops are uniform; commas are brief and consistent.', 'Tight, monotone read. Remove warmth, reduce vibrato, and keep pauses minimal and repeatable.', 'Deliver like a system message. Quick, level, concise; keep prosody shallow and consistent.', 'Script reading with speed. Compress phrasing, keep pitch range narrow, and avoid conversational rhythm.', 'Read with clipped precision. No lingering, identical comma timing, and straight sentence endings.', 'Practical and plain. Maintain even pace, avoid emphasis, and keep micro-pauses to a minimum.', 'Remove color. Keep articulation sharp, phrase lengths similar, and intonation flat across lines.', 'Rapid, monotone narration. Uniform clause timing, minimal breath marks, and no expressive shaping.', 'Keep it sterile. Quick delivery, reduced dynamics, and repetitive timing at punctuation.', 'Read like an index. Short, even breaks; flat melody; controlled, constant rate.', 'Lean, efficient cadence. Avoid rhetorical shaping and keep a tight, steady tempo.', 'Matter-of-fact read. No swelling or softening; identical comma spacing; straight line pitch.', 'Mechanical briefing. Uniform rhythm, low energy variance, and short consistent pauses.', 'Sound like automated captions. Compressed pauses, limited pitch, and steady word spacing.', 'Neutral desk read. Quick tempo, restrained dynamics, and standardized sentence boundaries.', 'Flatten your delivery. Keep consonants even, pauses predictable, and pitch nearly static.', 'Terse and monotone. Hold tempo steady, trim commas, and avoid natural conversational sway.', 'Read like a transcript. Precise timing, narrow prosody, and minimal expressive intent.', 'Keep style bureaucratic. Low contour, fixed rhythm, and minimized intra-sentence pauses.', 'Deliver with minimal humanity. Uniform speed, light pauses, and no tonal variety.', 'Plain recitation. Short, even breaks; level pitch; and steady, unvaried pacing.', 'Fast, neutral read. Do not underline points; keep timing repetitive and controlled.', 'Straight-through reading. Reduce breath, shorten rests, and avoid melodic arcs.', 'Crisp but colorless. Identical comma pauses, flat intonation, and fast execution.', 'Read with textbook neutrality. Minimal variance in pitch, timing, and loudness.', 'Unanimated narration. Quick tempo, constrained dynamics, and uniform clause timing.', 'Scripted cadence. Predictable breaks, monotone energy, and tight, constant rhythm.', 'Keep it clipped. No expressive stress, consistent punctuation timing, flat pitch.', 'Deliver as a prompter read. Rapid, even cadence, little warmth, and fixed pauses.']
POSITIVE_INSTRUCTIONS: List[str] = ['Answer naturally, like real conversation. Vary pace and tone, add brief thoughtful pauses, and emphasize key words lightly.', 'Speak as if explaining to a colleague. Use small pauses, gentle pitch movement, and relaxed, human timing.', 'Conversational style. Let phrases breathe, vary rhythm, and add subtle emphasis where it helps clarity.', 'Sound present and human. Mix short and medium pauses, natural pitch contour, and mild energy changes.', 'Explain it casually. Keep pacing flexible, insert brief reflective pauses, and shape sentences with tone.', 'Warm, conversational delivery. Slight hesitations are okay; vary pitch and timing to sound authentic.', 'Talk like youre in a meeting. Natural cadence, occasional pauses, and light emphasis on important points.', 'Friendly explanation. Use varied rhythm, natural sentence curves, and small pauses for structure.', 'Speak spontaneously. Allow minor imperfections, vary tempo, and let intonation guide the listener.', 'Relaxed answer. Mix shorter phrases with occasional longer ones; use tone to signal transitions.', 'Engaged and clear. Use light emphasis, varied pitch range, and organic, non-uniform timing.', 'Professional but human. Short pauses between ideas, gentle inflection, and flexible pacing.', 'Conversational clarity. Let punctuation guide pauses, but vary them; emphasize terms when useful.', 'Thoughtful pacing. Add small breaths, slight pitch ascent on lists, and natural sentence endings.', 'Talk as you would off-script. Vary tempo and prosody, allow tiny hesitations, and stay warm.', 'Explain with presence. Use tone to highlight points, natural breaks, and comfortable rhythm.', 'Approachable style. Keep timing loose, vary intonation, and let important words carry weight.', 'Natural office conversation. Small pauses, dynamic pitch, and varied phrase lengths.', 'Human rhythm. Blend short rests with occasional longer pauses; shape sentences musically.', 'Clear and personable. Moderate pace, mild emphasis, and organic timing variation.', 'Speak like teaching a peer. Natural pausing, soft dynamics, and flexible intonation.', 'Comfortable cadence. Let ideas land with short pauses; vary pitch and tempo slightly.', 'Authentic speech. Minor fillers acceptable; vary rhythm and give phrases room to breathe.', 'Calm and natural delivery. Keep energy steady but let pitch and timing move a bit.', 'Conversational explanation. Use subtle emphasis, varied pauses, and human timing.', 'Balanced spontaneity. Mix pace and tone; avoid uniform breaks; keep it personable.', 'Human, engaged tone. Vary phrasing length, use light emphasis, and pause briefly at transitions.', 'Natural prosody. Let sentences rise and fall; use brief pauses to separate thoughts.', 'Explain in your own words. Flexible pacing, light emphasis, and friendly inflection.', 'Talk like youre thinking aloud. Occasional small pauses, shifting tempo, and mild contours.', 'Confident but relaxed. Vary timing, keep pitch expressive, and pause where helpful.', 'Everyday speech pattern. Slightly uneven rhythm is fine; use tone for nuance.', 'Collegial tone. Natural breaks, subtle emphasis, and varied intonation across phrases.', 'Warm explanation. Breath where needed, shape phrases, and avoid metronomic timing.', 'Lightly animated. Dynamic but controlled pitch, flexible pace, and short reflective pauses.', 'Human guidance. Use tone to mark structure, avoid strict uniformity, and keep it clear.', 'Conversational sincerity. Let key terms stand out, vary timing, and pause naturally.', 'Explain with ease. Keep flow relaxed, use small rests, and change pitch modestly.', 'Talk like a live answer. Slight timing drift is fine; emphasize ideas with tone.', 'Natural storytelling. Varied rhythm, brief pauses, and expressive but professional pitch.', 'Unscripted feel. Allow minor hesitations, variable tempo, and gentle dynamic shifts.', 'Engaging clarity. Use small pauses to segment ideas; vary intonation to maintain interest.', 'Real-time explanation. Dont lock tempo; let pitch move; keep pauses purposeful.', 'Friendly, clear speech. Moderate pace, mild contouring, and organically placed pauses.', 'Conversational structure. Pause at idea boundaries; vary phrase length and tone.', 'Natural cadence over precision. Avoid identical breaks; let pitch and timing breathe.', 'Explain comfortably. Vary speed slightly, add brief pauses, and use tone for emphasis.', 'Authentic delivery. Keep it human: small breaths, flexible rhythm, and natural contour.', 'Relaxed prosody. Dynamic but not theatrical; short pauses and light emphasis.', 'Human, thoughtful answer. Allow slight imperfection; shape phrases and vary timing.']
GENDER_CHOICES: Tuple[str, str] = ('female', 'male')
GENDER_PROBS: Tuple[float, float] = (0.5, 0.5)
AGE_MIN, AGE_MAX, AGE_MODE = (18, 65, 30)
AGE_BOOST_RANGE: Tuple[int, int] = (22, 45)
AGE_BOOST_FACTOR: float = 1.25
ACCENT_NONE_NAME = 'General American (no marked accent)'
ACCENT_NONE_PROB = 0.75
ACCENT_POOL: List[Tuple[str, float]] = [('Indian English', 0.12), ('US Texas English', 0.08), ('US Southern', 0.07), ('US New York', 0.06), ('US Midwestern', 0.05), ('British RP', 0.07), ('British Estuary', 0.06), ('Australian English', 0.06), ('Irish English', 0.05), ('Scottish English', 0.05), ('Canadian English', 0.04), ('South African English', 0.04), ('Hispanic-influenced US English', 0.04), ('Eastern European / Slavic English', 0.05), ('Western European English', 0.03), ('East Asian English', 0.03), ('Southeast Asian English', 0.03), ('African English', 0.02)]
EXTRA_FEATURES_PROBS: Dict[str, float] = {'deep_voice': 0.18, 'bright_voice': 0.15, 'breathy': 0.12, 'coarse_voice': 0.1, 'nasal': 0.08, 'mumbling': 0.08, 'likes_to_pause': 0.22, 'nonconsistent_tempo': 0.22, 'fast_voice': 0.18, 'slow_voice': 0.16, 'precise_articulation': 0.22, 'slurred_articulation': 0.06, 'high_energy': 0.12, 'low_energy': 0.1}
MAX_ACTIVE_FEATURES: int = 3
STYLE_PARAM_PRIORS = {'negative': {'rate_range': (1.1, 1.25), 'pitch_semitones_range': (-2.0, -0.5), 'micro_break_ms': (90, 140), 'sentence_break_ms': (600, 750), 'intonation_variability': (0.05, 0.15), 'energy_variability': (0.05, 0.12)}, 'positive': {'rate_range': (0.95, 1.05), 'pitch_semitones_range': (-0.5, 1.0), 'micro_break_ms': (60, 220), 'sentence_break_ms': (350, 600), 'intonation_variability': (0.15, 0.35), 'energy_variability': (0.12, 0.3)}}

def _weighted_choice(rng: random.Random, items_with_weights: List[Tuple[str, float]]) -> str:
    total = sum((w for _, w in items_with_weights))
    x = rng.random() * total
    acc = 0.0
    for item, w in items_with_weights:
        acc += w
        if x <= acc:
            return item
    else:
        pass
    return items_with_weights[-1][0]

def sample_gender(rng: random.Random) -> str:
    return GENDER_CHOICES[0] if rng.random() < GENDER_PROBS[0] else GENDER_CHOICES[1]

def sample_age(rng: random.Random) -> int:
    a = rng.triangular(AGE_MIN, AGE_MAX, AGE_MODE)
    a = max(AGE_MIN, min(AGE_MAX, a))
    if AGE_BOOST_FACTOR > 1.0:
        lo, hi = AGE_BOOST_RANGE
        if not lo <= a <= hi:
            if rng.random() < (AGE_BOOST_FACTOR - 1.0) / AGE_BOOST_FACTOR:
                a = rng.triangular(AGE_MIN, AGE_MAX, AGE_MODE)
                a = max(AGE_MIN, min(AGE_MAX, a))
    return int(round(a))

def sample_accent(rng: random.Random) -> str:
    if rng.random() < ACCENT_NONE_PROB:
        return ACCENT_NONE_NAME
    return _weighted_choice(rng, ACCENT_POOL)

def sample_extra_features(rng: random.Random, max_active: int=MAX_ACTIVE_FEATURES) -> List[str]:
    active = [k for k, p in EXTRA_FEATURES_PROBS.items() if rng.random() < p]
    if len(active) > max_active:
        rng.shuffle(active)
        active = active[:max_active]
    return sorted(active)

def sample_style_params(rng: random.Random, label: str) -> Dict[str, float]:
    pri = STYLE_PARAM_PRIORS['positive' if label == 'positive' else 'negative']

    def draw(lo, hi):
        return lo + (hi - lo) * rng.random()
    return {'rate': round(draw(*pri['rate_range']), 3), 'pitch_semitones': round(draw(*pri['pitch_semitones_range']), 2), 'micro_break_ms': int(round(draw(*pri['micro_break_ms']))), 'sentence_break_ms': int(round(draw(*pri['sentence_break_ms']))), 'intonation_variability': round(draw(*pri['intonation_variability']), 3), 'energy_variability': round(draw(*pri['energy_variability']), 3)}

@dataclass(frozen=True)
class SpeakerPriorSample:
    gender: str
    age: int
    accent: str
    features: List[str]
    style_params: Dict[str, float]
    instruction: str
    label: str

def sample_all_priors(rng: random.Random, label: str) -> SpeakerPriorSample:
    if label not in ('negative', 'positive'):
        raise ValueError("label must be 'negative' or 'positive'")
    gender = sample_gender(rng)
    age = sample_age(rng)
    accent = sample_accent(rng)
    features = sample_extra_features(rng)
    style_params = sample_style_params(rng, label='positive' if label == 'positive' else 'negative')
    instruction = (NEGATIVE_INSTRUCTIONS if label == 'negative' else POSITIVE_INSTRUCTIONS)[rng.randrange(0, 50)]
    return SpeakerPriorSample(gender=gender, age=age, accent=accent, features=features, style_params=style_params, instruction=instruction, label=label)
