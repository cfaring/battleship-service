import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fleet import generate_valid_placement, BOARD_SIZE
from targeting import analyze_own_shots, choose_shot
from db import get_db
from models import Session as SessionModel, OwnShip, Shot

app = FastAPI()


class ShotResultRequest(BaseModel):
    result: Literal["miss", "hit", "killed"]


class OpponentShotRequest(BaseModel):
    coordinate: str


def all_coords() -> list[str]:
    letters = "ABCDEFGHIJ"
    return [f"{letters[r]}{c + 1}" for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)]


ALL_COORDS = all_coords()


async def get_session_or_404(session_id: uuid.UUID, db: AsyncSession) -> SessionModel:
    session = await db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def check_not_closed(session: SessionModel):
    if session.status == "closed":
        raise HTTPException(status_code=410, detail="Session closed")


@app.post("/game", status_code=201)
async def start_game(db: AsyncSession = Depends(get_db)):
    ships_data = generate_valid_placement()

    session = SessionModel()
    db.add(session)
    await db.flush()  # чтобы получить session.id до коммита

    for ship in ships_data:
        db.add(OwnShip(
            session_id=session.id,
            length=len(ship["coordinates"]),
            coordinates=ship["coordinates"],
        ))

    await db.commit()
    return {"session_id": str(session.id), "ships": ships_data}


@app.post("/game/{session_id}/shot")
async def make_shot(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session = await get_session_or_404(session_id, db)
    check_not_closed(session)

    if session.next_turn != "self":
        raise HTTPException(status_code=409, detail="Not your turn")

    if session.pending_shot is not None:
        return {"coordinate": session.pending_shot}  # идемпотентность при retry

    result = await db.execute(
        select(Shot.coordinate, Shot.result).where(Shot.session_id == session_id, Shot.direction == "own")
    )
    own_shots = result.all()
    fired = {coordinate for coordinate, _ in own_shots}
    available = [c for c in ALL_COORDS if c not in fired]
    if not available:
        raise HTTPException(status_code=409, detail="No cells left to shoot")

    misses, active_hits, sunk_cells, remaining = analyze_own_shots(own_shots)
    coordinate = choose_shot(available, misses, active_hits, sunk_cells, remaining)
    session.pending_shot = coordinate
    await db.commit()
    return {"coordinate": coordinate}


@app.post("/game/{session_id}/shot/result")
async def accept_shot_result(session_id: uuid.UUID, body: ShotResultRequest, db: AsyncSession = Depends(get_db)):
    session = await get_session_or_404(session_id, db)
    check_not_closed(session)

    if session.pending_shot is None:
        raise HTTPException(status_code=409, detail="No pending shot")

    db.add(Shot(
        session_id=session_id,
        direction="own",
        coordinate=session.pending_shot,
        result=body.result,
    ))
    session.pending_shot = None
    session.next_turn = "self" if body.result in ("hit", "killed") else "opponent"

    await db.commit()
    return {"status": "accepted"}


@app.post("/game/{session_id}/opponent-shot")
async def opponent_shot(session_id: uuid.UUID, body: OpponentShotRequest, db: AsyncSession = Depends(get_db)):
    session = await get_session_or_404(session_id, db)
    check_not_closed(session)

    result = await db.execute(select(OwnShip).where(OwnShip.session_id == session_id))
    ships = result.scalars().all()

    hit_ship = next((s for s in ships if body.coordinate in s.coordinates), None)

    outcome = "miss"
    if hit_ship is not None:
        if body.coordinate not in hit_ship.hit_coordinates:

            hit_ship.hit_coordinates = hit_ship.hit_coordinates + [body.coordinate]

        if set(hit_ship.hit_coordinates) == set(hit_ship.coordinates):
            hit_ship.sunk = True
            outcome = "killed"
        else:
            outcome = "hit"

    db.add(Shot(session_id=session_id, direction="opponent", coordinate=body.coordinate, result=outcome))
    session.next_turn = "opponent" if outcome in ("hit", "killed") else "self"

    await db.commit()
    return {"result": outcome}


# --- Ручка 5: закончить игру ---
@app.post("/game/{session_id}/close")
async def close_game(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    session = await get_session_or_404(session_id, db)
    if session.status == "closed":
        raise HTTPException(status_code=400, detail="Session already closed")

    session.status = "closed"
    await db.commit()
    return {"status": "closed"}
