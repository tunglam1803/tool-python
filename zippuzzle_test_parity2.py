import zippuzzle
solver = zippuzzle.SlidingSolver(
    [
        [1, 2, 3, 4, 5, 6, 7],
        [8, 9, 10, 11, 12, 13, 14],
        [15, 16, 17, 18, 19, 20, 21],
        [22, 23, 24, 25, 26, 27, 28],
        [29, 30, 31, 32, 33, 38, 35],
        [44, 37, 45, 40, 41, 34, 0],
        [36, 43, 39, 48, 47, 46, 42]
    ],
    7, 7
)
ans = solver.solve()
print("Moves returned:", "YES" if ans else "FAIL")
for row in solver.grid:
    print(row)

