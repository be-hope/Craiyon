import re

# Fixed color vocabulary banned on the "no colors" level (Level 4).
# Covers common color names and a few shade/hue modifiers.
_COLOR_WORDS = [
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown",
    "black", "white", "grey", "gray", "gold", "golden", "silver", "beige",
    "turquoise", "teal", "maroon", "navy", "violet", "indigo", "crimson",
    "scarlet", "magenta", "cyan", "lavender", "peach", "tan", "cream",
    "bronze", "copper", "amber", "emerald", "sapphire", "ruby", "ivory",
]

DEFAULT_WORD_LIMITS = {2: 20, 3: 6}  # Level 2: loose cap, Level 3: strict cap


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


def first_non_alliterative_word(prompt: str) -> str | None:
    """Checks whether every word in the prompt starts with the same letter.

    Returns the first word that breaks the pattern, or None if the whole
    prompt is alliterative (fewer than 2 words always counts as clean).
    """
    words = re.findall(r"[A-Za-z]+", prompt)
    if len(words) < 2:
        return None
    first_letter = words[0][0].lower()
    for w in words[1:]:
        if w[0].lower() != first_letter:
            return w
    return None


def contains_color_word(prompt: str) -> str | None:
    """Returns the first color word found in the prompt, or None if clean."""
    prompt_lower = prompt.lower()
    for w in _COLOR_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", prompt_lower):
            return w
    return None


def validate_prompt_for_level(
    prompt: str,
    level: int,
    banned_words_csv: str | None = None,
    required_words_csv: str | None = None,
    word_limit: int | None = None,
) -> str | None:
    """Returns an error message if the prompt breaks this level's rule, else None.

    Level 1 -- totally free, no constraints at all
    Level 2 -- free-form, loose word cap (default 20)
    Level 3 -- same idea, strict word cap (default 6)
    Level 4 -- banned words: specific words for this image are off-limits
    Level 5 -- no color words allowed at all
    Level 6 -- alliteration: every word must start with the same letter
    """
    if level == 1:
        return None

    if level in (2, 3):
        limit = word_limit or DEFAULT_WORD_LIMITS.get(level, 20)
        word_count = len(prompt.strip().split())
        if word_count > limit:
            return f"Keep it to {limit} words or fewer for this one -- you used {word_count}."

    elif level == 4:
        bad_word = contains_banned_word(prompt, banned_words_csv)
        if bad_word:
            return f'That image bans the word "{bad_word}" -- try describing it another way.'

    elif level == 5:
        bad_color = contains_color_word(prompt)
        if bad_color:
            return f'No color words allowed here -- try again without "{bad_color}".'

    elif level == 6:
        bad_word = first_non_alliterative_word(prompt)
        if bad_word:
            return f'Every word must start with the same letter -- "{bad_word}" breaks the pattern.'

    return None