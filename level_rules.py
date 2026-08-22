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


def is_emoji_only(prompt: str) -> bool:
    """True if the prompt is made up entirely of emoji (whitespace ignored)."""
    stripped = re.sub(r"\s+", "", prompt)
    if not stripped:
        return False
    remainder = _EMOJI_PATTERN.sub("", stripped)
    return remainder == ""


LEVEL_1_WORD_LIMIT = 12


def validate_prompt_for_level(prompt: str, level: int, banned_words_csv: str | None) -> str | None:
    """Returns an error message if the prompt breaks this level's rule, else None."""
    if level == 1:
        word_count = len(prompt.strip().split())
        if word_count > LEVEL_1_WORD_LIMIT:
            return f"Keep it to {LEVEL_1_WORD_LIMIT} words or fewer for this one -- you used {word_count}."
    elif level == 2:
        bad_word = contains_banned_word(prompt, banned_words_csv)
        if bad_word:
            return f'That image bans the word "{bad_word}" -- try describing it another way.'
    elif level == 3:
        if not is_emoji_only(prompt):
            return "This level only accepts emoji -- no words or letters allowed."
    return None