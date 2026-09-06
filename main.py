import json
import os
import random

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

import scoring
from database import Attempt, RoomSession, TargetImage, get_db, init_db
from image_gen_client import generate_image
from level_rules import DEFAULT_WORD_LIMITS, validate_prompt_for_level
from seats import validate_login
from target_pool import TARGET_POOL

app = FastAPI(title="Craiyon Workshop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_ATTEMPTS_PER_TARGET = 2
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "change-me")


@app.on_event("startup")
def on_startup():
    init_db()


# ---------- Schemas ----------

class LoginRequest(BaseModel):
    username: str
    password: str


class GenerateRequest(BaseModel):
    seat_id: str
    room_id: str
    target_id: int
    prompt: str


# ---------- Helpers ----------

def get_current_session_id(db: Session, room_id: str) -> str:
    row = db.query(RoomSession).filter(RoomSession.room_id == room_id).first()
    if row is None:
        row = RoomSession(room_id=room_id, session_id="0")
        db.add(row)
        db.commit()
    return row.session_id


def check_admin(secret: str):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/admin")
def admin_page():
    return FileResponse("static/admin.html")


@app.post("/login")
def login(req: LoginRequest):
    result = validate_login(req.username, req.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid seat/room credentials")
    return result


@app.get("/targets")
def list_targets(db: Session = Depends(get_db)):
    targets = (
        db.query(TargetImage)
        .filter(TargetImage.active == True)  # noqa: E712
        .order_by(TargetImage.id)
        .all()
    )
    return [
        {
            "id": t.id,
            "label": t.label,
            "image_url": t.image_url,
            "level": t.level,
            "banned_words": t.banned_words,
            "required_words": t.required_words,
            "word_limit": t.word_limit,
        }
        for t in targets
    ]


@app.post("/generate")
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    target = db.query(TargetImage).filter(TargetImage.id == req.target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Unknown target image")

    # Enforce this image's level rule BEFORE spending an attempt or calling
    # the image API -- a rule violation shouldn't cost a try.
    rule_error = validate_prompt_for_level(
        req.prompt, target.level, target.banned_words, target.required_words, target.word_limit
    )
    if rule_error:
        raise HTTPException(status_code=422, detail=rule_error)

    session_id = get_current_session_id(db, req.room_id)

    attempts_used = (
        db.query(Attempt)
        .filter(
            Attempt.seat_id == req.seat_id,
            Attempt.room_id == req.room_id,
            Attempt.session_id == session_id,
            Attempt.target_id == req.target_id,
        )
        .count()
    )
    if attempts_used >= MAX_ATTEMPTS_PER_TARGET:
        raise HTTPException(status_code=429, detail="No attempts left for this image")

    image_url = generate_image(req.prompt)

    target_fp = scoring.ImageFingerprint.from_dict(json.loads(target.fingerprint))
    generated_fp = scoring.fingerprint_from_url(image_url)
    score = scoring.similarity_score(target_fp, generated_fp)

    attempt = Attempt(
        seat_id=req.seat_id,
        room_id=req.room_id,
        session_id=session_id,
        target_id=req.target_id,
        prompt=req.prompt,
        image_url=image_url,
        score=score,
    )
    db.add(attempt)
    db.commit()

    # The student still sees their own score immediately -- what's hidden is
    # the room-wide leaderboard, which now only lives on the admin dashboard.
    return {
        "image_url": image_url,
        "score": score,
        "attempts_left": MAX_ATTEMPTS_PER_TARGET - attempts_used - 1,
    }


# ---------- Admin ----------

@app.get("/admin/leaderboard/{room_id}")
def admin_leaderboard(room_id: str, secret: str, db: Session = Depends(get_db)):
    check_admin(secret)
    session_id = get_current_session_id(db, room_id)

    rows = (
        db.query(Attempt.seat_id, func.max(Attempt.score).label("best_score"))
        .filter(Attempt.room_id == room_id, Attempt.session_id == session_id)
        .group_by(Attempt.seat_id, Attempt.target_id)
        .all()
    )

    totals: dict[str, float] = {}
    for seat_id, best_score in rows:
        totals[seat_id] = totals.get(seat_id, 0) + best_score

    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return [{"seat_id": seat, "total_score": round(score, 2)} for seat, score in ranked]


@app.post("/admin/new-session/{room_id}")
def new_session(room_id: str, secret: str, db: Session = Depends(get_db)):
    check_admin(secret)

    row = db.query(RoomSession).filter(RoomSession.room_id == room_id).first()
    if row is None:
        row = RoomSession(room_id=room_id, session_id="1")
        db.add(row)
    else:
        row.session_id = str(int(row.session_id) + 1)
    db.commit()
    return {"room_id": room_id, "new_session_id": row.session_id}


@app.post("/admin/remove-target/{target_id}")
def remove_target(target_id: int, secret: str, db: Session = Depends(get_db)):
    check_admin(secret)

    target = db.query(TargetImage).filter(TargetImage.id == target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")

    target.active = False
    db.commit()
    return {"id": target.id, "label": target.label, "active": target.active}


@app.post("/admin/randomize-targets")
def randomize_targets(secret: str, db: Session = Depends(get_db)):
    """Deactivates the current 6 target images and generates a fresh
    random set of 6 from the 20-prompt pool -- one image per level (1-6)."""
    check_admin(secret)

    current = db.query(TargetImage).filter(TargetImage.active == True).all()  # noqa: E712
    for t in current:
        t.active = False
    db.commit()

    chosen = random.sample(TARGET_POOL, 6)
    created = []

    for i, item in enumerate(chosen):
        level = i + 1  # each of the 6 images gets its own level, 1 through 6

        # Only Level 4 needs per-image config (its banned words are specific
        # to that image). Levels 5 (no colors) and 6 (alliteration) use fixed,
        # generic rules that apply the same way regardless of which image
        # landed on that level, so no required_words is needed anymore.
        banned_words = item["banned_words"] if level == 4 else None
        required_words = None
        word_limit = DEFAULT_WORD_LIMITS.get(level)  # only set for levels 2 & 3

        image_url = generate_image(item["prompt"])
        target_fp = scoring.fingerprint_from_url(image_url)

        target = TargetImage(
            label=item["label"],
            image_url=image_url,
            fingerprint=json.dumps(target_fp.to_dict()),
            active=True,
            level=level,
            banned_words=banned_words,
            required_words=required_words,
            word_limit=word_limit,
            source_prompt=item["prompt"],
        )
        db.add(target)
        created.append(target)

    db.commit()
    return [
        {
            "id": t.id, "label": t.label, "level": t.level,
            "banned_words": t.banned_words, "required_words": t.required_words,
            "word_limit": t.word_limit,
        }
        for t in created
    ]


@app.post("/admin/add-target")
def add_target(
    label: str,
    image_url: str,
    secret: str,
    level: int = 1,
    banned_words: str = None,
    required_words: str = None,
    word_limit: int = None,
    db: Session = Depends(get_db),
):
    """Add a target image from an external URL."""
    check_admin(secret)

    target_fp = scoring.fingerprint_from_url(image_url)
    target = TargetImage(
        label=label,
        image_url=image_url,
        fingerprint=json.dumps(target_fp.to_dict()),
        active=True,
        level=level,
        banned_words=banned_words,
        required_words=required_words,
        word_limit=word_limit,
    )
    db.add(target)
    db.commit()
    return {"id": target.id, "label": target.label, "level": target.level}


@app.post("/admin/generate-target")
def generate_target(
    label: str,
    prompt: str,
    secret: str,
    level: int = 1,
    banned_words: str = None,
    required_words: str = None,
    word_limit: int = None,
    db: Session = Depends(get_db),
):
    """Create a target image by generating it with AI (fal.ai) from a
    long, precise prompt -- avoids hotlinking/copyright issues entirely,
    and you keep the exact ground-truth prompt for reference."""
    check_admin(secret)

    image_url = generate_image(prompt)
    target_fp = scoring.fingerprint_from_url(image_url)
    target = TargetImage(
        label=label,
        image_url=image_url,
        fingerprint=json.dumps(target_fp.to_dict()),
        active=True,
        level=level,
        banned_words=banned_words,
        required_words=required_words,
        word_limit=word_limit,
        source_prompt=prompt,
    )
    db.add(target)
    db.commit()
    return {"id": target.id, "label": target.label, "level": target.level, "image_url": image_url}
