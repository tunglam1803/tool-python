class SlidingSolver:
    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.locked = set()
        self.grid = [[0 for _ in range(cols)] for _ in range(rows)]
        # Add 1..48 to grid randomly
        n = 1
        for r in range(rows):
            for c in range(cols):
                self.grid[r][c] = n
                n += 1
        self.grid[-1][-1] = 0

    def find(self, val):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == val: return r, c
        return None

    def move_empty(self, tr, tc, avoid=set()):
        curr = self.find(0)
        if curr == (tr, tc): return True
        q = [(curr, [])]; v = {curr}
        forbidden = self.locked | avoid
        while q:
            (r, c), path = q.pop(0)
            if (r, c) == (tr, tc):
                for pr, pc in path:
                    er, ec = self.find(0)
                    self.grid[er][ec], self.grid[pr][pc] = self.grid[pr][pc], self.grid[er][ec]
                return True
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = r+dr, c+dc
                if 0<=nr<self.rows and 0<=nc<self.cols and (nr,nc) not in v and (nr,nc) not in forbidden:
                    v.add((nr,nc)); q.append(((nr,nc), path+[(nr,nc)]))
        return False

    def move_tile(self, val, tr, tc, avoid=set()):
        while self.find(val) != (tr, tc):
            cr, cc = self.find(val)
            q = [( (cr,cc), [] )]; v = {(cr,cc)}; path = []
            forbidden = self.locked | avoid
            while q:
                (r,c), p = q.pop(0)
                if (r,c) == (tr,tc): path = p; break
                for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                    nr,nc = r+dr, c+dc
                    if 0<=nr<self.rows and 0<=nc<self.cols and (nr,nc) not in v and (nr,nc) not in forbidden:
                        v.add((nr,nc)); q.append(((nr,nc), p+[(nr,nc)]))
            if not path: 
                print(f"NO TILE PATH for {val} to {tr,tc}. Avoid={avoid}")
                return False
            for nr, nc in path:
                if not self.move_empty(nr, nc, avoid={(self.find(val))} | avoid):
                    print(f"EMPTY STUCK moving to {nr,nc} avoiding {self.find(val)}")
                    return False
                er, ec = self.find(0)
                pr, pc = self.find(val)
                self.grid[er][ec], self.grid[pr][pc] = self.grid[pr][pc], self.grid[er][ec]
        return True

    def swap(self, r, c):
        er, ec = self.find(0)
        self.grid[er][ec], self.grid[r][c] = self.grid[r][c], self.grid[er][ec]

# Simulate state at Row 5, col 0 (meaning rows 0..4 locked)
solver = SlidingSolver(7, 7)
solver.locked = set()
for r in range(5):
    for c in range(7):
        solver.locked.add((r, c))

solver.grid[-1][-1] = 0

R = 5
c = 0
v1 = R * 7 + c + 1 # 36
v2 = (R+1) * 7 + c + 1 # 43

print("Moving v2 (43) to (5,0)...")
solver.move_tile(v2, 5, 0)
print("Moving v1 (36) to (5,1)...")
solver.move_tile(v1, 5, 1, avoid={(5, 0)})
print("Moving empty to (6,0)...")
solver.move_empty(6, 0, avoid={(5, 0), (5, 1)})

solver.swap(5,0)
solver.swap(5,1)
print(f"Goal v1=36, v2=43. Result: {solver.grid[5][0]=}, {solver.grid[6][0]=}")
