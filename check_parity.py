def calculate_parity(grid):
    flat = []
    for row in grid:
        for val in row:
            flat.append(val)
    
    inversions = 0
    for i in range(len(flat)):
        if flat[i] == 0: continue
        for j in range(i + 1, len(flat)):
            if flat[j] == 0: continue
            if flat[i] > flat[j]:
                inversions += 1
    
    # Empty distance from bottom-right
    empty_row = 0
    for r in range(7):
        for c in range(7):
            if grid[r][c] == 0:
                empty_row = r
    
    dist = (6 - empty_row)
    
    return inversions, dist, (inversions + dist) % 2


grid = [
    [1, 2, 3, 4, 5, 6, 7],
    [8, 9, 10, 11, 12, 13, 14],
    [15, 16, 17, 18, 19, 20, 21],
    [22, 23, 24, 25, 26, 27, 28],
    [29, 30, 31, 32, 33, 38, 35],
    [44, 37, 45, 40, 41, 34, 0],
    [36, 43, 39, 48, 47, 46, 42]
]

inv, dist, parity = calculate_parity(grid)
print(f"Inversions: {inv}, Dist: {dist}, Parity (should be 0 for solvable): {parity}")
