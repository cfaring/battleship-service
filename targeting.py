import random

from fleet import (
    BOARD_SIZE,
    SHIPS,
    coord_to_str,
    str_to_coord,
    get_ship_cells,
    in_bounds,
    forbidden_zone,
)

MAX_SAMPLES = 300
MAX_SHIP_PLACEMENT_TRIES = 100


def group_into_ships(cells: set[str]) -> list[set[str]]:
    """Группирует клетки попаданий в связные (по вертикали/горизонтали) цепочки"""
    remaining = {str_to_coord(c) for c in cells}
    groups: list[set[str]] = []
    while remaining:
        stack = [next(iter(remaining))]
        group = set()
        while stack:
            cell = stack.pop()
            if cell not in remaining:
                continue
            remaining.discard(cell)
            group.add(cell)
            r, c = cell
            for neighbor in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if neighbor in remaining:
                    stack.append(neighbor)
        groups.append({coord_to_str(r, c) for r, c in group})
    return groups


def remaining_ship_lengths(sunk_ships: list[set[str]]) -> list[int]:
    """Полный набор SHIPS минус длины уже потопленных кораблей"""
    pool = list(SHIPS)
    for ship in sunk_ships:
        length = len(ship)
        if length in pool:
            pool.remove(length)
    return pool


def analyze_own_shots(
    shots: list[tuple[str, str]],
) -> tuple[set[str], set[str], set[str], list[int]]:
    """
    По истории собственных выстрелов (coordinate, result) восстанавливает
    - misses
    - active_hits
    - sunk_cells
    - remaining
    """
    misses = {c for c, r in shots if r == "miss"}
    hit_cells = {c for c, r in shots if r in ("hit", "killed")}
    killed_cells = {c for c, r in shots if r == "killed"}

    groups = group_into_ships(hit_cells)
    sunk_ships = [g for g in groups if g & killed_cells]
    active_groups = [g for g in groups if not (g & killed_cells)]

    active_hits = set().union(*active_groups) if active_groups else set()
    sunk_cells = set().union(*sunk_ships) if sunk_ships else set()
    remaining = remaining_ship_lengths(sunk_ships)
    return misses, active_hits, sunk_cells, remaining


def _try_place_ship(length, occupied, forbidden, anchor_cells):
    """Пытается разместить один корабль длины length, по возможности накрыв одну из anchor_cells"""
    for _ in range(MAX_SHIP_PLACEMENT_TRIES):
        if anchor_cells and random.random() < 0.8:
            anchor_r, anchor_c = str_to_coord(random.choice(list(anchor_cells)))
            orientation = random.choice(['H', 'V'])
            offset = random.randint(0, length - 1)
            if orientation == 'H':
                row, col = anchor_r, anchor_c - offset
            else:
                row, col = anchor_r - offset, anchor_c
        else:
            orientation = random.choice(['H', 'V'])
            row = random.randint(0, BOARD_SIZE - 1)
            col = random.randint(0, BOARD_SIZE - 1)

        cells = get_ship_cells(row, col, length, orientation)
        if not in_bounds(cells):
            continue
        if any(cell in forbidden or cell in occupied for cell in cells):
            continue
        return cells
    return None


def _sample_placement(misses, active_hits, remaining, sunk_forbidden):
    """Одна попытка сэмплировать полную валидную раскладку оставшихся кораблей противника"""
    lengths = list(remaining)
    random.shuffle(lengths)
    occupied: set[tuple[int, int]] = set()
    forbidden: set[tuple[int, int]] = {str_to_coord(c) for c in misses} | sunk_forbidden
    uncovered = set(active_hits)

    for length in lengths:
        cells = _try_place_ship(length, occupied, forbidden, uncovered)
        if cells is None:
            return None
        occupied.update(cells)
        forbidden.update(forbidden_zone(cells))
        uncovered -= {coord_to_str(r, c) for r, c in cells}

    if uncovered:
        return None
    return occupied


def _neighbor_candidates(active_hits, misses, available_set) -> list[str]:
    candidates = []
    for hit in active_hits:
        r, c = str_to_coord(hit)
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                coord = coord_to_str(nr, nc)
                if coord in available_set and coord not in misses:
                    candidates.append(coord)
    return candidates


def choose_shot(
    available: list[str],
    misses: set[str],
    active_hits: set[str],
    sunk_cells: set[str],
    remaining: list[int],
) -> str:
    """
    сэмплируем много валидных раскладок оставшихся кораблей противника, согласованных с уже известными попаданиями/промахами
    и стреляем в клетку, которая чаще всего оказывается занятой кораблём в этих сэмплах
    """
    if not remaining or not available:
        return random.choice(available)

    available_set = set(available)
    sunk_forbidden = forbidden_zone({str_to_coord(c) for c in sunk_cells}) if sunk_cells else set()

    frequency: dict[str, int] = {}
    for _ in range(MAX_SAMPLES):
        sample = _sample_placement(misses, active_hits, remaining, sunk_forbidden)
        if sample is None:
            continue
        for r, c in sample:
            coord = coord_to_str(r, c)
            if coord in available_set:
                frequency[coord] = frequency.get(coord, 0) + 1

    if not frequency:
        # не удалось собрать ни одного валидного сэмпла, значит добиваем известное попадание вручную либо стреляем наугад
        neighbors = _neighbor_candidates(active_hits, misses, available_set)
        if neighbors:
            return random.choice(neighbors)
        return random.choice(available)

    best = max(frequency.values())
    best_cells = [c for c, count in frequency.items() if count == best]
    return random.choice(best_cells)
