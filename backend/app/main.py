import hashlib
import os
import secrets
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
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


class HostConnectionManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, event_id: str, websocket: WebSocket):
        self.connections.setdefault(event_id, set()).add(websocket)

    def disconnect(self, event_id: str, websocket: WebSocket):
        connections = self.connections.get(event_id)
        if connections:
            connections.discard(websocket)
            if not connections:
                self.connections.pop(event_id, None)

    async def publish(self, event_id: str, payload: dict):
        for websocket in list(self.connections.get(event_id, set())):
            try:
                await websocket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError, OSError):
                self.disconnect(event_id, websocket)


host_connections = HostConnectionManager()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def lookup_event(db: Session, join_code: str) -> Event:
    event = db.scalar(select(Event).where(Event.join_code == join_code.upper()))
    if event is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return event


def host_lobby_payload(db: Session, event: Event) -> dict:
    participants = db.scalars(
        select(Participant)
        .where(Participant.event_id == event.id)
        .order_by(Participant.joined_at)
    ).all()
    return {
        "title": event.title,
        "join_code": event.join_code,
        "state": event.state,
        "participant_count": len(participants),
        "participants": [
            {"name": participant.private_name, "display_name": participant.display_name}
            for participant in participants
        ],
    }


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
def join_event(
    join_code: str,
    payload: ParticipantJoin,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    event = lookup_event(db, join_code)
    if event.state not in {"lobby", "active"}:
        raise HTTPException(status_code=409, detail="This quiz is no longer accepting participants")
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
    background_tasks.add_task(
        host_connections.publish,
        event.id,
        {"type": "host_lobby", "data": host_lobby_payload(db, event)},
    )
    return {
        "participant_id": participant.id,
        "display_name": participant.display_name,
        "reconnect_token": reconnect_token,
        "state": event.state,
    }


@app.get("/api/events/{join_code}/state")
def get_participant_event_state(
    join_code: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Participant link required")
    token = authorization.removeprefix("Bearer ").strip()
    event = lookup_event(db, join_code)
    participant = db.scalar(
        select(Participant).where(
            Participant.event_id == event.id,
            Participant.reconnect_token_hash == token_hash(token),
        )
    )
    if participant is None or not secrets.compare_digest(
        participant.reconnect_token_hash, token_hash(token)
    ):
        raise HTTPException(status_code=403, detail="Invalid participant link")

    result = {"title": event.title, "join_code": event.join_code, "state": event.state}
    if event.state != "lobby":
        result["questions"] = [
            {
                "prompt": question.prompt,
                "choices": [choice.text for choice in question.choices],
                "time_limit_seconds": question.time_limit_seconds,
            }
            for question in event.questions
        ]
    return result


@app.get("/api/host/{event_id}")
def get_host_event(event_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Host link required")
    token = authorization.removeprefix("Bearer ").strip()
    event = db.get(Event, event_id)
    if event is None or not secrets.compare_digest(token_hash(token), event.host_token_hash):
        raise HTTPException(status_code=403, detail="Invalid host link")
    return host_lobby_payload(db, event)


@app.websocket("/api/host/{event_id}/ws")
async def host_lobby_updates(websocket: WebSocket, event_id: str):
    await websocket.accept()
    try:
        token = await websocket.receive_text()
        with SessionLocal() as db:
            event = db.get(Event, event_id)
            if event is None or not secrets.compare_digest(token_hash(token), event.host_token_hash):
                await websocket.send_json({"type": "error", "detail": "Invalid host link"})
                await websocket.close(code=4403)
                return
            await host_connections.connect(event_id, websocket)
            await websocket.send_json({"type": "host_lobby", "data": host_lobby_payload(db, event)})

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        host_connections.disconnect(event_id, websocket)


@app.post("/api/host/{event_id}/start")
def start_host_event(event_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Host link required")
    token = authorization.removeprefix("Bearer ").strip()
    event = db.get(Event, event_id)
    if event is None or not secrets.compare_digest(token_hash(token), event.host_token_hash):
        raise HTTPException(status_code=403, detail="Invalid host link")
    if event.state != "lobby":
        raise HTTPException(status_code=409, detail="This quiz has already started")

    event.state = "active"
    db.commit()
    return {"state": event.state}
