import hashlib
import os
import secrets
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Choice, Event, Participant, Question
from .schemas import ParticipantJoin, QuizCreate


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Live Quiz Competition API", version="0.1.0", lifespan=lifespan)
frontend_origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def lookup_event(db: Session, join_code: str) -> Event:
    event = db.scalar(select(Event).where(Event.join_code == join_code.upper()))
    if event is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return event


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/quizzes", status_code=status.HTTP_201_CREATED)
def create_quiz(payload: QuizCreate, db: Session = Depends(get_db)):
    host_token = secrets.token_urlsafe(32)
    event = Event(
        id=str(uuid.uuid4()),
        title=payload.title,
        join_code=secrets.token_urlsafe(5).replace("-", "").replace("_", "").upper()[:7],
        host_token_hash=token_hash(host_token),
    )
    for question_position, question_input in enumerate(payload.questions):
        question = Question(
            position=question_position,
            prompt=question_input.prompt,
            time_limit_seconds=question_input.time_limit_seconds,
            correct_choice_index=question_input.correct_choice_index,
        )
        question.choices = [Choice(position=i, text=text) for i, text in enumerate(question_input.choices)]
        event.questions.append(question)
    db.add(event)
    db.commit()
    return {
        "event_id": event.id,
        "title": event.title,
        "join_code": event.join_code,
        "participant_url": f"/?join={event.join_code}",
        "host_url": f"/host/{event.id}#{host_token}",
    }


@app.get("/api/events/{join_code}")
def get_public_event(join_code: str, db: Session = Depends(get_db)):
    event = lookup_event(db, join_code)
    participant_count = db.scalar(
        select(func.count()).select_from(Participant).where(Participant.event_id == event.id)
    ) or 0
    return {
        "title": event.title,
        "join_code": event.join_code,
        "state": event.state,
        "participant_count": participant_count,
        "max_participants": 50,
    }


@app.post("/api/events/{join_code}/participants", status_code=status.HTTP_201_CREATED)
def join_event(join_code: str, payload: ParticipantJoin, db: Session = Depends(get_db)):
    event = lookup_event(db, join_code)
    if event.state != "lobby":
        raise HTTPException(status_code=409, detail="This quiz is no longer accepting lobby entries")
    count = db.scalar(select(func.count()).select_from(Participant).where(Participant.event_id == event.id)) or 0
    if count >= 50:
        raise HTTPException(status_code=409, detail="This quiz is full")
    duplicate = db.scalar(
        select(Participant.id).where(
            Participant.event_id == event.id,
            func.lower(Participant.display_name) == payload.display_name.casefold(),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="That display name is already taken")

    reconnect_token = secrets.token_urlsafe(32)
    participant = Participant(
        id=str(uuid.uuid4()),
        event_id=event.id,
        private_name=payload.name,
        display_name=payload.display_name,
        reconnect_token_hash=token_hash(reconnect_token),
    )
    db.add(participant)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That display name is already taken") from None
    return {
        "participant_id": participant.id,
        "display_name": participant.display_name,
        "reconnect_token": reconnect_token,
        "state": "lobby",
    }


@app.get("/api/host/{event_id}")
def get_host_event(event_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Host link required")
    token = authorization.removeprefix("Bearer ").strip()
    event = db.get(Event, event_id)
    if event is None or not secrets.compare_digest(token_hash(token), event.host_token_hash):
        raise HTTPException(status_code=403, detail="Invalid host link")
    return {
        "title": event.title,
        "join_code": event.join_code,
        "state": event.state,
        "participant_count": len(event.participants),
        "participants": [
            {"name": participant.private_name, "display_name": participant.display_name}
            for participant in event.participants
        ],
    }
