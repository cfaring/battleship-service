import pytest
from httpx import ASGITransport, AsyncClient

import tournament
from main import app
from tournament import Standings, format_table, play_series, run_tournament


@pytest.mark.asyncio
async def test_play_series_alternates_who_shoots_first():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://a") as client_a:
        async with AsyncClient(transport=transport, base_url="http://b") as client_b:
            results = await play_series(client_a, "a", client_b, "b", matches_per_pair=2)

    assert len(results) == 2
    for result in results:
        assert {result.winner, result.loser} == {"a", "b"}


@pytest.mark.asyncio
async def test_run_tournament_plays_every_pair_round_robin(monkeypatch):
    # run_tournament сам открывает httpx.AsyncClient(base_url=...) по имени сервиса;
    # подменяем его на ASGI-транспорт поверх одного и того же приложения, чтобы не
    # поднимать три реальных сервиса ради теста.
    transport = ASGITransport(app=app)
    monkeypatch.setattr(
        tournament.httpx, "AsyncClient",
        lambda base_url: AsyncClient(transport=transport, base_url=base_url),
    )

    names = ["a", "b", "c"]
    services = {name: f"http://{name}" for name in names}

    results = await run_tournament(services, matches_per_pair=2)

    # 3 сервиса -> 3 пары * 2 матча = 6 матчей
    assert len(results) == 6

    standings = Standings()
    for result in results:
        standings.record(result)
    total_games = sum(standings.wins.values()) + sum(standings.losses.values())
    assert total_games == 12  # у каждого матча по одной победе и одному поражению

    table = format_table(results, names)
    for name in names:
        assert name in table
