import re

# Matches last year's format: SEAT001_1 / S001_1
SEAT_MIN = 1
SEAT_MAX = 200
VALID_ROOMS = {"1", "2", "3"}

USERNAME_RE = re.compile(r"^SEAT(\d{3})_(\d)$")


def validate_login(username: str, password: str):
    """Returns {"seat_id": ..., "room_id": ...} if valid, else None.

    No database lookup needed -- the credentials are deterministic,
    so we just check the pattern and range match.
    """
    match = USERNAME_RE.match(username.strip().upper())
    if not match:
        return None

    seat_num, room = match.group(1), match.group(2)

    if room not in VALID_ROOMS:
        return None
    if not (SEAT_MIN <= int(seat_num) <= SEAT_MAX):
        return None

    expected_password = f"S{seat_num}_{room}"
    if password.strip().upper() != expected_password:
        return None

    return {"seat_id": f"SEAT{seat_num}", "room_id": room}
