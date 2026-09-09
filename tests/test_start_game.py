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
