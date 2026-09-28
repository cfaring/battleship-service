import pytest
from httpx import ASGITransport, AsyncClient

from arena import MatchResult, play_match, resolve_shot, validate_placement
from fleet import generate_valid_placement
from main import app


def test_validate_placement_accepts_generated_fleet():
    assert validate_placement(generate_valid_placement())


def test_validate_placement_rejects_touching_ships():
    ships = [{"coordinates": ["A1", "A2"]}, {"coordinates": ["B1", "B2"]}]
    assert not validate_placement(ships)


def test_validate_placement_rejects_wrong_ship_count():
    assert not validate_placement([{"coordinates": ["A1"]}])


def test_resolve_shot_tracks_hits_and_kills():
    ships = [["A1", "A2"]]
    hits = [set()]
    assert resolve_shot("B5", ships, hits) == "miss"
    assert resolve_shot("A1", ships, hits) == "hit"
    assert resolve_shot("A2", ships, hits) == "killed"


@pytest.mark.asyncio
async def test_play_match_produces_a_winner():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://a") as client_a:
        async with AsyncClient(transport=transport, base_url="http://b") as client_b:
            result = await play_match(client_a, "a", client_b, "b")

    assert isinstance(result, MatchResult)
    assert result.winner in ("a", "b")
    assert result.reason == "all ships sunk"
