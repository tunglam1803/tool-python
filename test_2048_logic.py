import numpy as np
from solve_2048 import simulate_move, merge, get_moves, evaluate, get_best_move

def test_logic():
    # Test merge
    assert merge([2, 2, 0, 0]) == [4, 0, 0, 0]
    assert merge([2, 2, 2, 2]) == [4, 4, 0, 0]
    assert merge([4, 2, 2, 0]) == [4, 4, 0, 0]
    assert merge([0, 0, 2, 2]) == [4, 0, 0, 0]
    print("Merge logic: PASSED")

    # Test move
    board = [
        [2, 0, 0, 0],
        [2, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0]
    ]
    res = simulate_move(board, 'down')
    expected = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [4, 0, 0, 0]
    ]
    assert np.array_equal(res, expected)
    print("Move simulation: PASSED")

    # Test Best Move
    board = [
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [2, 2, 0, 0],
        [1024, 1024, 0, 0]
    ]
    # In this case, moving right or left should merge the 1024s
    best = get_best_move(board)
    print(f"Best move for high-value merge: {best}")
    assert best in ['left', 'right']
    print("AI Strategy: PASSED")

if __name__ == "__main__":
    test_logic()
