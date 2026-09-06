import re

# Covers the emoji ranges you'll realistically see typed on a phone/laptop,
# plus the joiner/variation-selector characters combined emojis use.
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\u200d"
    "\uFE0F"
    "]+",
    flags=re.UNICODE,
)

# Fixed color vocabulary banned on the "no colors" level (Level 5).
# Covers common color names and a few shade/hue modifiers.
_COLOR_WORDS = [
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown",
    "black", "white", "grey", "gray", "gold", "golden", "silver", "beige",
    "turquoise", "teal", "maroon", "navy", "violet", "indigo", "crimson",
    "scarlet", "magenta", "cyan", "lavender", "peach", "tan", "cream",
    "bronze", "copper", "amber", "emerald", "sapphire", "ruby", "ivory",
]

DEFAULT_WORD_LIMITS = {1: 20, 2: 6}  # Level 1: loose cap, Level 2: strict cap


def contains_banned_word(prompt: str, banned_words_csv: str | None) -> str | None:
    """Returns the first banned word found in the prompt, or None if clean."""
    if not banned_words_csv:
        return None
    words = [w.strip().lower() for w in banned_words_csv.split(",") if w.strip()]
    prompt_lower = prompt.lower()
    for w in words:
        if w in prompt_lower:
            return w
    return None


def missing_required_words(prompt: str, required_words_csv: str | None) -> list[str]:
    """Returns the list of required words NOT found in the prompt."""
    if not required_words_csv:
        return []
    words = [w.strip().lower() for w in required_words_csv.split(",") if w.strip()]
    prompt_lower = prompt.lower()
    return [w for w in words if w not in prompt_lower]


def contains_color_word(prompt: str) -> str | None:
    """Returns the first color word found in the prompt, or None if clean."""
    prompt_lower = prompt.lower()
    for w in _COLOR_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", prompt_lower):
            return w
    return None


def is_emoji_only(prompt: str) -> bool:
    """True if the prompt is made up entirely of emoji (whitespace ignored)."""
    stripped = re.sub(r"\s+", "", prompt)
    if not stripped:
        return False
    remainder = _EMOJI_PATTERN.sub("", stripped)
    return remainder == ""


def validate_prompt_for_level(
    prompt: str,
    level: int,
    banned_words_csv: str | None = None,
    required_words_csv: str | None = None,
    word_limit: int | None = None,
) -> str | None:
    """Returns an error message if the prompt breaks this level's rule, else None.

    Level 1 -- free-form, loose word cap (default 20)
    Level 2 -- same idea, strict word cap (default 6)
    Level 3 -- banned words: specific words for this image are off-limits
    Level 4 -- required words: specific (often unrelated) words MUST appear
    Level 5 -- no color words allowed at all
    Level 6 -- emoji only, no letters
    """
    if level in (1, 2):
        limit = word_limit or DEFAULT_WORD_LIMITS.get(level, 20)
        word_count = len(prompt.strip().split())
        if word_count > limit:
            return f"Keep it to {limit} words or fewer for this one -- you used {word_count}."

    elif level == 3:
        bad_word = contains_banned_word(prompt, banned_words_csv)
        if bad_word:
            return f'That image bans the word "{bad_word}" -- try describing it another way.'

    elif level == 4:
        missing = missing_required_words(prompt, required_words_csv)
        if missing:
            return f'Your prompt must include: {", ".join(missing)}.'

    elif level == 5:
        bad_color = contains_color_word(prompt)
        if bad_color:
            return f'No color words allowed here -- try again without "{bad_color}".'

    elif level == 6:
        if not is_emoji_only(prompt):
            return "This level only accepts emoji -- no words or letters allowed."

    return None
