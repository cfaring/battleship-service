import pytest


@pytest.mark.asyncio
async def test_start_game_returns_ten_ships(client):
    response = await client.post("/game")
    assert response.status_code == 201

    data = response.json()
    assert "session_id" in data
    assert len(data["ships"]) == 10

    total_decks = sum(len(ship["coordinates"]) for ship in data["ships"])
    assert total_decks == 20


@pytest.mark.asyncio
async def test_full_turn_cycle(client):
    start = await client.post("/game")
    session_id = start.json()["session_id"]

    shot = await client.post(f"/game/{session_id}/shot")
    assert shot.status_code == 200
    coordinate = shot.json()["coordinate"]
    assert len(coordinate) in (2, 3)  # 'A1'..'J10'

    result = await client.post(f"/game/{session_id}/shot/result", json={"result": "miss"})
    assert result.status_code == 200
    assert result.json() == {"status": "accepted"}

    reaction = await client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "A1"})
    assert reaction.status_code == 200
    assert reaction.json()["result"] in ("miss", "hit", "killed")

    close = await client.post(f"/game/{session_id}/close")
    assert close.status_code == 200

    close_again = await client.post(f"/game/{session_id}/close")
    assert close_again.status_code == 400


@pytest.mark.asyncio
async def test_turn_passes_back_after_opponent_miss(client):
    start = await client.post("/game")
    session_id = start.json()["session_id"]
    ships = start.json()["ships"]

    all_coords = [f"{chr(ord('A') + r)}{c + 1}" for r in range(10) for c in range(10)]
    occupied = {coord for ship in ships for coord in ship["coordinates"]}
    hit_coord = next(iter(occupied))
    miss_coord = next(c for c in all_coords if c not in occupied)

    # Противник попадает по нашему кораблю — ход остаётся за противником,
    # поэтому наш собственный выстрел сейчас должен быть отклонён.
    reaction = await client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": hit_coord})
    assert reaction.json()["result"] in ("hit", "killed")

    blocked_shot = await client.post(f"/game/{session_id}/shot")
    assert blocked_shot.status_code == 409

    # Промах противника отдаёт ход обратно нам.
    reaction = await client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": miss_coord})
    assert reaction.json()["result"] == "miss"

    allowed_shot = await client.post(f"/game/{session_id}/shot")
    assert allowed_shot.status_code == 200


@pytest.mark.asyncio
async def test_shots_never_repeat_and_survive_a_kill(client):
    start = await client.post("/game")
    session_id = start.json()["session_id"]

    used_coordinates = set()

    # Первые два выстрела репортим как "hit"/"killed" (условно топим один корабль
    # противника), чтобы next_turn оставался "self" и можно было стрелять дальше.
    for result in ("hit", "killed", "hit", "killed", "hit"):
        shot = await client.post(f"/game/{session_id}/shot")
        assert shot.status_code == 200
        coordinate = shot.json()["coordinate"]

        assert coordinate not in used_coordinates
        used_coordinates.add(coordinate)

        report = await client.post(f"/game/{session_id}/shot/result", json={"result": result})
        assert report.status_code == 200

    close = await client.post(f"/game/{session_id}/close")
    assert close.status_code == 200
