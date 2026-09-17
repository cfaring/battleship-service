import random

BOARD_SIZE = 10
SHIPS = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]


def coord_to_str(row: int, col: int) -> str:
    return f"{chr(ord('A') + row)}{col + 1}"


def str_to_coord(coord: str) -> tuple[int, int]:
    row = ord(coord[0]) - ord('A')
    col = int(coord[1:]) - 1
    return row, col


def get_ship_cells(row, col, length, orientation):
    if orientation == 'H':
        return [(row, col + i) for i in range(length)]
    return [(row + i, col) for i in range(length)]


def in_bounds(cells):
    return all(0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE for r, c in cells)


def forbidden_zone(cells):
    forbidden = set()
    for r, c in cells:
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                forbidden.add((r + dr, c + dc))
    return forbidden


def random_initial_placement():
    """Первичная расстановка """
    while True:
        forbidden = set()
        ships = []
        ok = True
        for length in SHIPS:
            placed = False
            for _ in range(200):
                orientation = random.choice(['H', 'V'])
                row = random.randint(0, BOARD_SIZE - 1)
                col = random.randint(0, BOARD_SIZE - 1)
                cells = get_ship_cells(row, col, length, orientation)
                if not in_bounds(cells) or any(c in forbidden for c in cells):
                    continue
                forbidden.update(forbidden_zone(cells))
                ships.append({"length": length, "row": row, "col": col,
                              "orientation": orientation, "cells": cells})
                placed = True
                break
            if not placed:
                ok = False
                break
        if ok:
            return ships


def forbidden_from_others(ships, exclude_index):
    forbidden = set()
    for i, ship in enumerate(ships):
        if i == exclude_index:
            continue
        forbidden.update(forbidden_zone(ship["cells"]))
    return forbidden


def mcmc_step(ships):
    idx = random.randrange(len(ships))
    length = ships[idx]["length"]
    forbidden = forbidden_from_others(ships, idx)

    for _ in range(50):
        orientation = random.choice(['H', 'V'])
        row = random.randint(0, BOARD_SIZE - 1)
        col = random.randint(0, BOARD_SIZE - 1)
        cells = get_ship_cells(row, col, length, orientation)
        if not in_bounds(cells) or any(c in forbidden for c in cells):
            continue
        ships[idx] = {"length": length, "row": row, "col": col,
                      "orientation": orientation, "cells": cells}
        return True
    return False


def generate_valid_placement(burn_in: int = 500) -> list[dict]:
    ships = random_initial_placement()
    for _ in range(burn_in):
        mcmc_step(ships)
    return [{"coordinates": [coord_to_str(r, c) for r, c in s["cells"]]} for s in ships]
