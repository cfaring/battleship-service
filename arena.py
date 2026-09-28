import asyncio
import sys
from dataclasses import dataclass

import httpx

from fleet import SHIPS, forbidden_zone, in_bounds, str_to_coord

TIMEOUT = 1.0
TOTAL_DECKS = sum(SHIPS)
MAX_SHOTS = 200


class TechnicalLoss(Exception):
    def __init__(self, loser, reason):
        super().__init__(reason)
        self.loser = loser
        self.reason = reason


@dataclass
class MatchResult:
    winner: str
    loser: str
    reason: str


def _is_straight_line(cells):
    rows = {r for r, _ in cells}
    cols = {c for _, c in cells}
    if len(rows) == 1:
        start = min(cols)
        return sorted(cols) == list(range(start, start + len(cells)))
    if len(cols) == 1:
        start = min(rows)
        return sorted(rows) == list(range(start, start + len(cells)))
    return False


def validate_placement(ships):
    if sorted(len(ship["coordinates"]) for ship in ships) != sorted(SHIPS):
        return False

    cell_groups = []
    for ship in ships:
        cells = [str_to_coord(c) for c in ship["coordinates"]]
        if not in_bounds(cells) or not _is_straight_line(cells):
            return False
        cell_groups.append(set(cells))

    for i, cells in enumerate(cell_groups):
        forbidden = forbidden_zone(cells)
        if any(forbidden & other for j, other in enumerate(cell_groups) if j != i):
            return False
    return True


def resolve_shot(coordinate, ships, hits_by_ship):
    for coords, hit_set in zip(ships, hits_by_ship):
        if coordinate in coords:
            hit_set.add(coordinate)
            return "killed" if hit_set == set(coords) else "hit"
    return "miss"


async def _call(client, name, method, path, **kwargs):
    try:
        response = await client.request(method, path, timeout=TIMEOUT, **kwargs)
    except httpx.TimeoutException:
        raise TechnicalLoss(name, "timeout")
    except httpx.HTTPError as exc:
        raise TechnicalLoss(name, f"network error: {exc}")
    if response.status_code >= 400:
        raise TechnicalLoss(name, f"http {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise TechnicalLoss(name, "invalid json")


async def _start_game(client, name):
    data = await _call(client, name, "POST", "/game")
    if not validate_placement(data["ships"]):
        raise TechnicalLoss(name, "invalid placement")
    ships = [ship["coordinates"] for ship in data["ships"]]
    return data["session_id"], ships


async def play_match(client_a, name_a, client_b, name_b):
    clients = {name_a: client_a, name_b: client_b}
    session_a, ships_a = await _start_game(client_a, name_a)
    session_b, ships_b = await _start_game(client_b, name_b)

    boards = {
        name_a: (session_a, ships_a, [set() for _ in ships_a]),
        name_b: (session_b, ships_b, [set() for _ in ships_b]),
    }

    shooter, defender = name_a, name_b
    try:
        for _ in range(MAX_SHOTS):
            shooter_session, _, _ = boards[shooter]
            shot = await _call(clients[shooter], shooter, "POST", f"/game/{shooter_session}/shot")
            coordinate = shot["coordinate"]

            defender_session, defender_ships, defender_hits = boards[defender]
            outcome = resolve_shot(coordinate, defender_ships, defender_hits)

            await _call(
                clients[shooter], shooter, "POST", f"/game/{shooter_session}/shot/result",
                json={"result": outcome},
            )
            reaction = await _call(
                clients[defender], defender, "POST", f"/game/{defender_session}/opponent-shot",
                json={"coordinate": coordinate},
            )
            if reaction["result"] != outcome:
                raise TechnicalLoss(defender, "reported result does not match own board")

            if sum(len(hit_set) for hit_set in defender_hits) == TOTAL_DECKS:
                return MatchResult(winner=shooter, loser=defender, reason="all ships sunk")

            if outcome == "miss":
                shooter, defender = defender, shooter
        raise TechnicalLoss(shooter, "match did not finish within shot limit")
    except TechnicalLoss as loss:
        winner = name_b if loss.loser == name_a else name_a
        return MatchResult(winner=winner, loser=loss.loser, reason=loss.reason)
    finally:
        for name, (session_id, _, _) in boards.items():
            try:
                await _call(clients[name], name, "POST", f"/game/{session_id}/close")
            except TechnicalLoss:
                pass


async def _main(url_a, url_b):
    async with httpx.AsyncClient(base_url=url_a) as client_a, httpx.AsyncClient(base_url=url_b) as client_b:
        result = await play_match(client_a, url_a, client_b, url_b)
    print(f"{result.winner} beat {result.loser}: {result.reason}")


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1], sys.argv[2]))
