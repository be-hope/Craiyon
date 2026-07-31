import os

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
from seats import validate_login

app = FastAPI(title="Craiyon Workshop API")

# Allow your frontend (any origin, for simplicity -- tighten later if you want)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_ATTEMPTS_PER_TARGET = 3
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


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the frontend at the root URL, static assets under /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.post("/login")
def login(req: LoginRequest):
    result = validate_login(req.username, req.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid seat/room credentials")
    return result


@app.get("/targets")
def list_targets(db: Session = Depends(get_db)):
    targets = db.query(TargetImage).filter(TargetImage.active == True).all()  # noqa: E712
    return [
        {"id": t.id, "label": t.label, "image_url": t.image_url}
        for t in targets
    ]


@app.post("/generate")
def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    target = db.query(TargetImage).filter(TargetImage.id == req.target_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Unknown target image")

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

    # 1. Generate the image via Nebius FLUX schnell
    image_url = generate_image(req.prompt)

    # 2. Score it against the target's precomputed fingerprint
    import json
    target_fp = scoring.ImageFingerprint.from_dict(json.loads(target.fingerprint))
    generated_fp = scoring.fingerprint_from_url(image_url)
    score = scoring.similarity_score(target_fp, generated_fp)

    # 3. Store the attempt
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

    return {
        "image_url": image_url,
        "score": score,
        "attempts_left": MAX_ATTEMPTS_PER_TARGET - attempts_used - 1,
    }


@app.get("/leaderboard/{room_id}")
def leaderboard(room_id: str, db: Session = Depends(get_db)):
    session_id = get_current_session_id(db, room_id)

    # Best score per seat, summed across all targets they've attempted
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


# ---------- Admin ----------

@app.post("/admin/new-session/{room_id}")
def new_session(room_id: str, secret: str, db: Session = Depends(get_db)):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    row = db.query(RoomSession).filter(RoomSession.room_id == room_id).first()
    if row is None:
        row = RoomSession(room_id=room_id, session_id="1")
        db.add(row)
    else:
        row.session_id = str(int(row.session_id) + 1)
    db.commit()
    return {"room_id": room_id, "new_session_id": row.session_id}


@app.post("/admin/add-target")
def add_target(label: str, image_url: str, secret: str, db: Session = Depends(get_db)):
    if secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    import json
    target_fp = scoring.fingerprint_from_url(image_url)
    target = TargetImage(
        label=label,
        image_url=image_url,
        fingerprint=json.dumps(target_fp.to_dict()),
        active=True,
    )
    db.add(target)
    db.commit()
    return {"id": target.id, "label": target.label}