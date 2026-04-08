import easyocr
import pyautogui
import cv2
import numpy as np
import time
import json
import os
import re
from PIL import Image
from mss import mss
from collections import deque
import ctypes

CONFIG_FILE = "zippuzzle_config.json"
MOVE_DELAY = 0.1
reader = None

def get_reader():
    global reader
    if reader is None:
        print("Initialzing OCR...")
        reader = easyocr.Reader(['en'], gpu=False)
    return reader

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def calibrate():
    print("\n--- Zip Puzzle Calibration ---")
    rows = int(input("Enter number of ROWS (e.g., 7): "))
    cols = int(input("Enter number of COLUMNS (e.g., 7): "))
    print(f"Move mouse to TOP-LEFT of the {rows}x{cols} GRID and press Enter.")
    input()
    tl = pyautogui.position()
    print("Move mouse to BOTTOM-RIGHT and press Enter.")
    input()
    br = pyautogui.position()
    config = {"rows": rows, "cols": cols, "top": tl.y, "left": tl.x, "width": br.x - tl.x, "height": br.y - tl.y}
    save_config(config)
    return config

def get_grid_state(config):
    rows, cols = config['rows'], config['cols']
    with mss() as sct:
        img_orig = np.array(sct.grab(config))
        img_bgr = cv2.cvtColor(img_orig, cv2.COLOR_BGRA2BGR)
        cell_w, cell_h = config['width'] / cols, config['height'] / rows
        
        variances = []
        for i in range(rows * cols):
            r, c = i // cols, i % cols
            x1, y1, x2, y2 = int(c*cell_w), int(r*cell_h), int((c+1)*cell_w), int((r+1)*cell_h)
            cell = img_bgr[y1:y2, x1:x2]
            variances.append(np.var(cell))
        
        empty_idx = np.argmin(variances)
        er, ec = empty_idx // cols, empty_idx % cols
        print(f"Empty slot detected at ({er}, {ec}) based on image uniformness.")

        cell_imgs = []
        for i in range(rows * cols):
            r, c = i // cols, i % cols
            x1, y1, x2, y2 = int(c*cell_w), int(r*cell_h), int((c+1)*cell_w), int((r+1)*cell_h)
            cell = img_bgr[y1:y2, x1:x2]
            cell_up = cv2.resize(cell, (100, 100), interpolation=cv2.INTER_CUBIC)
            cell_imgs.append(cell_up)

        results = get_reader().readtext_batched(cell_imgs)
        grid = [[0 for _ in range(cols)] for _ in range(rows)]
        detected_nums = set()
        
        for i, res in enumerate(results):
            r, c = i // cols, i % cols
            if i == empty_idx: continue
            
            if res:
                all_found = re.findall(r'\d+', " ".join([r[1] for r in res]))
                if all_found:
                    candidates = [int(n) for n in all_found]
                    val = candidates[0]
                    if val >= rows * cols:
                        for sub in candidates:
                            sub_str = str(sub)
                            for l in range(len(sub_str), 0, -1):
                                if int(sub_str[-l:]) < rows*cols: 
                                    val = int(sub_str[-l:]); break
                    grid[r][c] = val
                    detected_nums.add(val)

        missing = [n for n in range(1, rows*cols) if n not in detected_nums]
        for r in range(rows):
            for c in range(cols):
                if grid[r][c] == 0 and (r, c) != (er, ec):
                    if missing:
                        grid[r][c] = missing.pop(0)
        
        return grid

class SlidingSolver:
    def __init__(self, grid, rows, cols):
        self.grid = [row[:] for row in grid]
        self.rows, self.cols = rows, cols
        self.moves = []
        self.locked = set()

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
        for _ in range(20): # Retry loop for pocket traps
            success = True
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
                    success = False; break
                for nr, nc in path:
                    if not self.move_empty(nr, nc, avoid={(self.find(val))} | avoid): 
                        success = False; break
                    self.swap(*self.find(val))
                if not success: break
            if success and self.find(val) == (tr, tc): return True
            er, ec = self.find(0)
            candidates = [(er+1, ec), (er, ec-1), (er, ec+1), (er-1, ec)]
            moved = False
            for nr, nc in candidates:
                if 0<=nr<self.rows and 0<=nc<self.cols and (nr,nc) not in self.locked and (nr,nc) not in avoid:
                    self.swap(nr, nc)
                    moved = True
                    break
            if not moved: return False
        return False

    def solve_mini(self, tile_vals, targets):
        """Shortest-path BFS solver for small tile subsets in the unlocked area."""
        unlocked = []
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) not in self.locked: unlocked.append((r, c))
        
        start_positions = []
        for v in tile_vals: start_positions.append(self.find(v))
        start_state = tuple(start_positions + [self.find(0)])
        
        target_positions = tuple(targets)
        q = deque([(start_state, [])])
        visited = {start_state}
        
        while q:
            curr_state, path = q.popleft()
            if all(curr_state[i] == target_positions[i] for i in range(len(tile_vals))):
                for move in path: self.swap(*move)
                return True
            
            er, ec = curr_state[-1]
            for dr, dc in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr, nc = er+dr, ec+dc
                if (nr, nc) in unlocked:
                    new_l = list(curr_state)
                    new_l[-1] = (nr, nc)
                    for i in range(len(tile_vals)):
                        if curr_state[i] == (nr, nc):
                            new_l[i] = (er, ec); break
                    new_state = tuple(new_l)
                    if new_state not in visited:
                        visited.add(new_state); q.append((new_state, path + [(nr, nc)]))
        return False

    def solve(self):
        try:
            for r in range(self.rows - 2):
                for c in range(self.cols - 2):
                    val = r * self.cols + c + 1
                    print(f"Solving {val}...")
                    if not self.move_tile(val, r, c): return None
                    self.locked.add((r, c))
                
                # Handling last 2 tiles of row
                # Handling last 2 tiles of row using Mini-Solver
                v1, v2 = (r+1)*self.cols - 1, (r+1)*self.cols
                print(f"Solving row-end {v1}, {v2}...")
                if not self.solve_mini([v1, v2], [(r, self.cols-2), (r, self.cols-1)]): return None
                
                self.locked.add((r, self.cols-2))
                self.locked.add((r, self.cols-1))
                print(f"Row {r} done.")
            
            # --- Bottom Strip (Last 2 Rows) via Columns ---
            R = self.rows - 2
            for c in range(self.cols - 2):
                v1 = R * self.cols + c + 1
                v2 = (R+1) * self.cols + c + 1
                print(f"Solving col-end {v1}, {v2}...")
                if not self.solve_mini([v1, v2], [(R, c), (R+1, c)]): return None
                
                self.locked.add((R, c))
                self.locked.add((R+1, c))
                print(f"Col {c} done.")
            
            # --- Final 2x2 ---
            t1 = R * self.cols + (self.cols-2) + 1
            t2 = R * self.cols + (self.cols-1) + 1
            t3 = (R+1) * self.cols + (self.cols-2) + 1
            print("Solving final 2x2...")
            if self.solve_mini([t1, t2, t3], [(R, self.cols-2), (R, self.cols-1), (R+1, self.cols-2)]):
                print("Puzzle completely solved!")
                return self.moves
            
            print("Failed to solve final 2x2. Parity error?")
            return None

        except Exception as e:
            print(f"Solver Error: {e}")
            return None

def main():
    config = load_config()
    if not config or 'rows' not in config: config = calibrate()
    print("\nPress Enter to OCR and Start!")
    input()
    
    grid = get_grid_state(config)
    print("\n--- DETECTED GRID ---")
    for r, row in enumerate(grid):
        print(f"Row {r}: {row}")
    
    print("\nCheck the grid above. If there are errors, type 're' to recalibrate or press Enter to SOLVE.")
    choice = input().strip().lower()
    if choice == 're':
        os.remove(CONFIG_FILE); return main()

    solver = SlidingSolver(grid, config['rows'], config['cols'])
    moves = solver.solve()
    if moves:
        cell_w, cell_h = config['width'] / config['cols'], config['height'] / config['rows']
        print(f"Executing {len(moves)} moves. STAY AWAY FROM MOUSE!")
        time.sleep(2)
        for r, c in moves:
            # Emergency stop check (Esc key)
            if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
                print("\n[!] Emergency Stop: ESC pressed. Stopping solver.")
                break
            pyautogui.click(config['left'] + int((c+0.5)*cell_w), config['top'] + int((r+0.5)*cell_h))
            time.sleep(MOVE_DELAY)
        print("Done!")
    else:
        print("\n[!] Failed to compute a stable path.")
        print("Current Grid State observed on failure:")
        for r, row in enumerate(solver.grid):
            print(f"Row {r}: {row}")
        print("Grid state might be incorrect or OCR misread a tile.")

if __name__ == "__main__": main()
