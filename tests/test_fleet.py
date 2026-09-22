import pytest

from fleet import BOARD_SIZE, SHIPS, coord_to_str, forbidden_zone, generate_valid_placement, str_to_coord


@pytest.mark.parametrize("row,col,expected", [(0, 0, "A1"), (4, 4, "E5"), (9, 9, "J10")])
def test_coord_str_roundtrip(row, col, expected):
    assert coord_to_str(row, col) == expected
    assert str_to_coord(expected) == (row, col)


def test_generate_valid_placement_matches_ship_pool():
    ships = generate_valid_placement()
    assert sorted(len(s["coordinates"]) for s in ships) == sorted(SHIPS)


def test_generate_valid_placement_stays_in_bounds():
    ships = generate_valid_placement()
    for ship in ships:
        for coord in ship["coordinates"]:
            row, col = str_to_coord(coord)
            assert 0 <= row < BOARD_SIZE
            assert 0 <= col < BOARD_SIZE


def test_generate_valid_placement_ships_do_not_touch():
    ships = generate_valid_placement()
    all_cells = [{str_to_coord(c) for c in ship["coordinates"]} for ship in ships]

    for i, cells in enumerate(all_cells):
        forbidden = forbidden_zone(cells)
        for j, other_cells in enumerate(all_cells):
            if i == j:
                continue
            assert not (forbidden & other_cells)
