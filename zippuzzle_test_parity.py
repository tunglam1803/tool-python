class SlidingSolver:
    def __init__(self):
        self.rows, self.cols = 7, 7
        self.locked = set()
        self.grid = [
            [1, 2, 3, 4, 5, 6, 7],
            [8, 9, 10, 11, 12, 13, 14],
            [15, 16, 17, 18, 19, 20, 21],
            [22, 23, 24, 25, 26, 27, 28],
            [29, 30, 31, 32, 33, 38, 35],
            [44, 37, 45, 40, 41, 34, 0],
            [36, 43, 39, 48, 47, 46, 42]
        ]
        self.moves = []

    def find(self, val):
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == val: return r, c
        return None

    def swap(self, r, c):
        er, ec = self.find(0)
        self.grid[er][ec], self.grid[r][c] = self.grid[r][c], self.grid[er][ec]
        self.moves.append((r, c))

    def move_empty(self, tr, tc, avoid=set()):
        curr = self.find(0)
        if curr == (tr, tc): return True
        q = [(curr, [])]; v = {curr}
        forbidden = self.locked | avoid
        while q:
            (r, c), path = q.pop(0)
            if (r, c) == (tr, tc):
                for pr, pc in path: self.swap(pr, pc)
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
                print(f"No path for tile {val} to {tr}, {tc} from {cr}, {cc}. Forbidden={forbidden}")
                return False
            for nr, nc in path:
                if not self.move_empty(nr, nc, avoid={(self.find(val))} | avoid): 
                    print(f"Empty stuck moving to {nr}, {nc} avoiding {self.find(val)}")
                    return False
                self.swap(*self.find(val))
        return True

    def solve(self):
        try:
            for r in range(self.rows - 2):
                for c in range(self.cols - 2):
                    val = r * self.cols + c + 1
                    if not self.move_tile(val, r, c): return f"FAIL on mid {val}"
                    self.locked.add((r, c))
                v1, v2 = (r+1)*self.cols - 1, (r+1)*self.cols
                if not self.move_tile(v1, r, self.cols-1): return f"FAIL on row-end v1 {v1}"
                if not self.move_tile(v2, r+1, self.cols-1, avoid={(r, self.cols-1)}): return f"FAIL on row-end v2 {v2}"
                if not self.move_empty(r, self.cols-2, avoid={(r, self.cols-1), (r+1, self.cols-1)}): return "FAIL on row-end empty"
                self.swap(r, self.cols-1)
                self.swap(r+1, self.cols-1)
                self.locked.add((r, self.cols-2))
                self.locked.add((r, self.cols-1))
            R = self.rows - 2
            for c in range(self.cols - 2):
                v1 = R * self.cols + c + 1
                v2 = (R+1) * self.cols + c + 1
                if not self.move_tile(v2, R, c): return f"FAIL on col-end v2 {v2}"
                if not self.move_tile(v1, R, c+1, avoid={(R, c)}): return f"FAIL on col-end v1 {v1}"
                if not self.move_empty(R+1, c, avoid={(R, c), (R, c+1)}): return "FAIL on col-end empty"
                self.swap(R, c)
                self.swap(R, c+1)
                self.locked.add((R, c))
                self.locked.add((R+1, c))
            t1 = R * self.cols + (self.cols-2) + 1
            t2 = R * self.cols + (self.cols-1) + 1
            t3 = (R+1) * self.cols + (self.cols-2) + 1
            for _ in range(12):
                if self.find(t1) == (R, self.cols-2) and self.find(t2) == (R, self.cols-1) and self.find(t3) == (R+1, self.cols-2):
                    return "SUCCESS"
                er, ec = self.find(0)
                if (er, ec) == (R, self.cols-2): self.swap(R, self.cols-1)
                elif (er, ec) == (R, self.cols-1): self.swap(R+1, self.cols-1)
                elif (er, ec) == (R+1, self.cols-1): self.swap(R+1, self.cols-2)
                elif (er, ec) == (R+1, self.cols-2): self.swap(R, self.cols-2)
            return "PARITY_FAILED"
        except Exception as e:
            return f"ERROR: {e}"

print(SlidingSolver().solve())
