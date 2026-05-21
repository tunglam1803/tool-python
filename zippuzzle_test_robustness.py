import re
import math

def is_solvable(grid, rows, cols):
    flat = []
    empty_row = 0
    for r in range(rows):
        for c in range(cols):
            val = grid[r][c]
            if val == 0:
                empty_row = r
            else:
                flat.append(val)
    
    inversions = 0
    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            if flat[i] > flat[j]:
                inversions += 1
    
    if cols % 2 == 1:
        return inversions % 2 == 0
    else:
        row_from_bottom = rows - 1 - empty_row
        return (inversions + row_from_bottom) % 2 == 0

def mock_get_grid_state(rows, cols, empty_idx, results):
    grid = [[0 for _ in range(cols)] for _ in range(rows)]
    
    raw_detections = []
    for i, res in enumerate(results):
        if i == empty_idx:
            continue
        val = None
        conf = 0.0
        if res:
            candidates = []
            for bbox, text, text_conf in res:
                digits = re.findall(r'\d+', text)
                if digits:
                    for d in digits:
                        d_val = int(d)
                        if d_val >= rows * cols:
                            d_str = str(d_val)
                            for l in range(len(d_str), 0, -1):
                                cand = int(d_str[-l:])
                                if cand < rows * cols:
                                    d_val = cand
                                    break
                        candidates.append((d_val, text_conf))
            if candidates:
                candidates.sort(key=lambda x: x[1], reverse=True)
                val, conf = candidates[0]
        if val is not None:
            raw_detections.append((val, conf, i))

    raw_detections.sort(key=lambda x: x[1], reverse=True)
    assigned_vals = {}
    final_cells = {}
    corrections = {}
    
    for val, conf, cell_idx in raw_detections:
        if val not in assigned_vals:
            assigned_vals[val] = cell_idx
            final_cells[cell_idx] = val

    missing_nums = [n for n in range(1, rows*cols) if n not in assigned_vals]
    unassigned_cells = [i for i in range(rows*cols) if i != empty_idx and i not in final_cells]

    matched_missing = set()
    matched_cells = set()
    
    cell_original_detections = {}
    for val, conf, cell_idx in raw_detections:
        if cell_idx in unassigned_cells:
            if cell_idx not in cell_original_detections:
                cell_original_detections[cell_idx] = val

    for cell_idx in unassigned_cells:
        orig_val = cell_original_detections.get(cell_idx)
        if orig_val is not None:
            for m in missing_nums:
                if m in matched_missing:
                    continue
                m_str = str(m)
                orig_str = str(orig_val)
                if m_str.endswith(orig_str) or orig_str.endswith(m_str):
                    final_cells[cell_idx] = m
                    matched_missing.add(m)
                    matched_cells.add(cell_idx)
                    corrections[cell_idx] = orig_val
                    break

    remaining_missing = [m for m in missing_nums if m not in matched_missing]
    remaining_cells = [c for c in unassigned_cells if c not in matched_cells]
    for c, m in zip(remaining_cells, remaining_missing):
        final_cells[c] = m
        orig = cell_original_detections.get(c)
        corrections[c] = orig if orig is not None else "None"

    for r in range(rows):
        for c in range(cols):
            cell_idx = r * cols + c
            if cell_idx == empty_idx:
                grid[r][c] = 0
            else:
                grid[r][c] = final_cells.get(cell_idx, 0)
                
    return grid, corrections

def run_tests():
    print("=== RUNNING ZIPPUZZLE ROBUSTNESS TESTS ===")
    
    # Test 1: Historical failure with duplicate 8 (read as 8 and 18, missing 18)
    # Output 2 grid:
    # Row 0: [6, 2, 3, 5, 1]
    # Row 1: [7, 4, 8, 9, 0]  (Empty at index 9, i.e., (1, 4))
    # Row 2: [11, 12, 13, 14, 10]
    # Row 3: [16, 17, 8, 20, 15] (Cell at index 17, which is (3, 2), read as 8)
    # Row 4: [21, 22, 23, 19, 24]
    # We simulate EasyOCR returning high-confidence 8 at (1,2) [index 7] and lower-confidence 8 at (3,2) [index 17]
    mock_results = [[] for _ in range(25)]
    # Populate mock OCR values and confidence
    detected_vals = [
        (0, 6, 0.98), (1, 2, 0.99), (2, 3, 0.97), (3, 5, 0.99), (4, 1, 0.98),
        (5, 7, 0.99), (6, 4, 0.99), (7, 8, 0.95), (8, 9, 0.99), # (9, empty, 0)
        (10, 11, 0.99), (11, 12, 0.99), (12, 13, 0.99), (13, 14, 0.99), (14, 10, 0.99),
        (15, 16, 0.99), (16, 17, 0.99), (17, 8, 0.42), (18, 20, 0.99), (19, 15, 0.99),
        (20, 21, 0.99), (21, 22, 0.99), (22, 23, 0.99), (23, 19, 0.99), (24, 24, 0.99)
    ]
    for idx, val, conf in detected_vals:
        mock_results[idx] = [([0, 0, 10, 10], str(val), conf)]
        
    resolved_grid, corrections = mock_get_grid_state(5, 5, 9, mock_results)
    
    print("\n--- Test 1 (Duplicate 8 Resolution) ---")
    print("Resolved Grid:")
    for row in resolved_grid:
        print(row)
    print("Corrections applied:", corrections)
    
    # Assertions
    assert resolved_grid[1][2] == 8, "Expected real 8 to stay at index 7"
    assert resolved_grid[3][2] == 18, "Expected misread 8 at index 17 to correct to 18"
    assert is_solvable(resolved_grid, 5, 5), "Expected resolved grid to be mathematically solvable!"
    print("Test 1 PASS!")

    # Test 2: Check mathematical solvability parity calculation
    # Solvable 5x5 Grid (standard goal state)
    solvable_grid = [
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10],
        [11, 12, 13, 14, 15],
        [16, 17, 18, 19, 20],
        [21, 22, 23, 24, 0]
    ]
    # Unsolvable 5x5 Grid (19 and 20 swapped)
    unsolvable_grid = [
        [1, 2, 3, 4, 5],
        [6, 7, 8, 9, 10],
        [11, 12, 13, 14, 15],
        [16, 17, 18, 20, 19],
        [21, 22, 23, 24, 0]
    ]
    
    print("\n--- Test 2 (Parity calculations) ---")
    assert is_solvable(solvable_grid, 5, 5) == True, "Goal state grid should be solvable"
    assert is_solvable(unsolvable_grid, 5, 5) == False, "Grid with single swap should be unsolvable"
    print("Test 2 PASS!")
    
    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
