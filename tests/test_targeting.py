from fleet import SHIPS
from targeting import analyze_own_shots, choose_shot, group_into_ships, remaining_ship_lengths


def test_group_into_ships_connects_adjacent_cells():
    groups = group_into_ships({"B2", "B3"})
    assert groups == [{"B2", "B3"}]


def test_group_into_ships_separates_non_adjacent_cells():
    groups = group_into_ships({"B2", "D5"})
    assert sorted(groups, key=len) == sorted([{"B2"}, {"D5"}], key=len)


def test_remaining_ship_lengths_removes_exactly_one_occurrence():
    pool = remaining_ship_lengths([{"B2", "B3"}])  # length 2
    expected = list(SHIPS)
    expected.remove(2)
    assert sorted(pool) == sorted(expected)


def test_analyze_own_shots_splits_sunk_and_active():
    shots = [
        ("A1", "miss"),
        ("B2", "hit"),
        ("B3", "killed"),
        ("D5", "hit"),
        ("E5", "miss"),
    ]
    misses, active_hits, sunk_cells, remaining = analyze_own_shots(shots)

    assert misses == {"A1", "E5"}
    assert sunk_cells == {"B2", "B3"}
    assert active_hits == {"D5"}

    expected_remaining = list(SHIPS)
    expected_remaining.remove(2)
    assert sorted(remaining) == sorted(expected_remaining)


def test_choose_shot_never_returns_fired_cell():
    all_coords = [f"{chr(ord('A') + r)}{c + 1}" for r in range(10) for c in range(10)]
    fired = set(all_coords[:37])
    available = [c for c in all_coords if c not in fired]

    for _ in range(20):
        shot = choose_shot(available, set(), set(), set(), list(SHIPS))
        assert shot in available


def test_choose_shot_finishes_off_a_partially_hit_ship():
    all_coords = [f"{chr(ord('A') + r)}{c + 1}" for r in range(10) for c in range(10)]
    # E5 is a hit; every neighbour except E6 is a known miss, so the only way
    # to place the last remaining 2-length ship consistently is E5-E6.
    fired = {"E5", "E4", "D5", "F5"}
    available = [c for c in all_coords if c not in fired]

    shot = choose_shot(available, {"E4", "D5", "F5"}, {"E5"}, set(), [2])
    assert shot == "E6"
