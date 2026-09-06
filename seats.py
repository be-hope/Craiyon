import re

# Matches last year's format: SEAT001_1 / S001_1
SEAT_MIN = 1
SEAT_MAX = 200
VALID_ROOMS = {"1", "2", "3"}

USERNAME_RE = re.compile(r"^SEAT(\d{3})_(\d)$")

# Fixed test accounts for development/QA, on top of the real seat pattern.
# These never expire or depend on the seat range -- handy for testing
# without printing/remembering a real seat credential.
TEST_ACCOUNTS = {
    "DEMO1": {"password": "DEMO123", "seat_id": "DEMO1", "room_id": "1"},
    "DEMO2": {"password": "DEMO123", "seat_id": "DEMO2", "room_id": "1"},
    "DEMO3": {"password": "DEMO123", "seat_id": "DEMO3", "room_id": "1"},
    "SAIMA": {"password": "DEMO123", "seat_id": "SAIMA", "room_id": "1"},
    "ANIRUDH": {"password": "DEMO123", "seat_id": "ANIRUDH", "room_id": "1"},
    "GYAAN": {"password": "DEMO123", "seat_id": "GYAAN", "room_id": "1"},
    "KISHAN": {"password": "DEMO123", "seat_id": "KISHAN", "room_id": "1"},
    "DHRUVANTH": {"password": "DEMO123", "seat_id": "DHRUVANTH", "room_id": "1"},
    "MADHUSUDAN": {"password": "DEMO123", "seat_id": "MADHUSUDAN", "room_id": "1"},
    "NIRANJAN": {"password": "DEMO123", "seat_id": "NIRANJAN", "room_id": "1"},
    "RAHUL": {"password": "DEMO123", "seat_id": "RAHUL", "room_id": "1"},
    "RHEA": {"password": "DEMO123", "seat_id": "RHEA", "room_id": "1"},
    "RUTHVIK": {"password": "DEMO123", "seat_id": "RUTHVIK", "room_id": "1"},
    "SACI": {"password": "DEMO123", "seat_id": "SACI", "room_id": "1"},
    "SOHA": {"password": "DEMO123", "seat_id": "SOHA", "room_id": "1"},
    "ANSHDEEP": {"password": "DEMO123", "seat_id": "ANSHDEEP", "room_id": "1"},
    "NAINIKA": {"password": "DEMO123", "seat_id": "NAINIKA", "room_id": "1"},
    "ATIKSH": {"password": "DEMO123", "seat_id": "ATIKSH", "room_id": "1"},
    "AYAAN": {"password": "DEMO123", "seat_id": "AYAAN", "room_id": "1"},
    "SAKSHAM": {"password": "DEMO123", "seat_id": "SAKSHAM", "room_id": "1"},
    "SHARAT": {"password": "DEMO123", "seat_id": "SHARAT", "room_id": "1"},
    "SHREESH": {"password": "DEMO123", "seat_id": "SHREESH", "room_id": "1"},
    "SHUBHAM": {"password": "DEMO123", "seat_id": "SHUBHAM", "room_id": "1"},
    "SUMAN": {"password": "DEMO123", "seat_id": "SUMAN", "room_id": "1"},
    "SUPRITA": {"password": "DEMO123", "seat_id": "SUPRITA", "room_id": "1"},
    "BHADRA": {"password": "DEMO123", "seat_id": "BHADRA", "room_id": "1"},
}


def validate_login(username: str, password: str):
    """Returns {"seat_id": ..., "room_id": ...} if valid, else None."""
    clean_user = username.strip().upper()
    clean_pass = password.strip().upper()

    # 1. Check fixed test accounts first
    if clean_user in TEST_ACCOUNTS:
        account = TEST_ACCOUNTS[clean_user]
        if clean_pass == account["password"]:
            return {"seat_id": account["seat_id"], "room_id": account["room_id"]}
        return None

    # 2. Fall back to the real seat/room pattern
    match = USERNAME_RE.match(clean_user)
    if not match:
        return None

    seat_num, room = match.group(1), match.group(2)

    if room not in VALID_ROOMS:
        return None
    if not (SEAT_MIN <= int(seat_num) <= SEAT_MAX):
        return None

    expected_password = f"S{seat_num}_{room}"
    if clean_pass != expected_password:
        return None

    return {"seat_id": f"SEAT{seat_num}", "room_id": room}
