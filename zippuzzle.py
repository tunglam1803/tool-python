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
import colorama
from colorama import Fore, Back, Style

colorama.init(autoreset=True)

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
            
            # Apply 20% crop inset to completely avoid grid border lines
            w, h = x2 - x1, y2 - y1
            inset = 0.20
            ix1 = x1 + int(w * inset)
            ix2 = x2 - int(w * inset)
            iy1 = y1 + int(h * inset)
            iy2 = y2 - int(h * inset)
            
            cell = img_bgr[iy1:iy2, ix1:ix2]
            
            # Convert color cell into high-contrast grayscale using the Min Channel operation
            # (minimum across B, G, R channels). This yields excellent contrast for green-white
            # and purple-black cells alike.
            cell_gray = np.min(cell, axis=2)
            
            # Add border padding using BORDER_REPLICATE to naturally extend the background color
            padded_cell = cv2.copyMakeBorder(cell_gray, 15, 15, 15, 15, cv2.BORDER_REPLICATE)
            cell_up = cv2.resize(padded_cell, (120, 120), interpolation=cv2.INTER_CUBIC)
            cell_imgs.append(cell_up)

        results = get_reader().readtext_batched(cell_imgs)
        grid = [[0 for _ in range(cols)] for _ in range(rows)]
        
        # Parse all OCR results and keep candidate values + confidence scores
        raw_detections = [] # list of (val, confidence, cell_idx)
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
                            # Apply suffix fix for out-of-bounds numbers
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

        # Resolve duplicates by confidence descending
        raw_detections.sort(key=lambda x: x[1], reverse=True)
        assigned_vals = {} # val -> cell_idx
        final_cells = {} # cell_idx -> val
        corrections = {} # cell_idx -> original_val (for terminal reporting)
        
        for val, conf, cell_idx in raw_detections:
            if val not in assigned_vals:
                assigned_vals[val] = cell_idx
                final_cells[cell_idx] = val

        # Find missing and unassigned cells
        missing_nums = [n for n in range(1, rows*cols) if n not in assigned_vals]
        unassigned_cells = [i for i in range(rows*cols) if i != empty_idx and i not in final_cells]

        # Suffix matching heuristic to resolve duplicates
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

        # Fill remaining cells with remaining missing numbers
        remaining_missing = [m for m in missing_nums if m not in matched_missing]
        remaining_cells = [c for c in unassigned_cells if c not in matched_cells]
        for c, m in zip(remaining_cells, remaining_missing):
            final_cells[c] = m
            orig = cell_original_detections.get(c)
            corrections[c] = orig if orig is not None else "None"

        # Build final grid
        for r in range(rows):
            for c in range(cols):
                cell_idx = r * cols + c
                if cell_idx == empty_idx:
                    grid[r][c] = 0
                else:
                    grid[r][c] = final_cells.get(cell_idx, 0)
                    
        return grid, corrections

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

def main():
    config = load_config()
    if not config or 'rows' not in config: config = calibrate()
    print("\nPress Enter to OCR and Start!")
    input()
    
    grid, corrections = get_grid_state(config)
    
    # Beautified console grid printing
    print(f"\n{Fore.CYAN}╔" + "═══" * config['cols'] + "╗")
    for r in range(config['rows']):
        row_str = f"{Fore.CYAN}║"
        for c in range(config['cols']):
            val = grid[r][c]
            cell_idx = r * config['cols'] + c
            
            # Formatting color
            if val == 0:
                cell_val = f"{Fore.MAGENTA}[ ]"
            elif cell_idx in corrections:
                # This cell was auto-corrected! Mark it with an asterisk
                cell_val = f"{Fore.YELLOW}{val:<3}"
            else:
                cell_val = f"{Fore.GREEN}{val:<3}"
            
            row_str += cell_val
        row_str += f"{Fore.CYAN}║"
        print(row_str)
    print(f"{Fore.CYAN}╚" + "═══" * config['cols'] + "╝")
    
    # Print list of corrections
    if corrections:
        print(f"\n{Fore.YELLOW}[OCR Auto-Corrections Applied]:")
        for cell_idx, orig_val in corrections.items():
            r, c = cell_idx // config['cols'], cell_idx % config['cols']
            val = grid[r][c]
            print(f"  • Cell ({r}, {c}) originally read as '{orig_val}' was corrected to '{val}'")
            
    # Check mathematical solvability
    solvable = is_solvable(grid, config['rows'], config['cols'])
    if solvable:
        print(f"\n{Fore.GREEN}[✓] Mathematical Parity Check Passed: Grid is fully solvable!")
    else:
        print(f"\n{Fore.RED}[!] Mathematical Parity Check Failed: Grid has a parity error and is unsolvable.")
        print(f"{Fore.YELLOW}This usually means the OCR misread a tile. Please try again or type 're' to recalibrate.")
    
    print("\nCheck the grid above. If there are errors, type 're' to recalibrate or press Enter to SOLVE.")
    choice = input().strip().lower()
    if choice == 're':
        os.remove(CONFIG_FILE); return main()

    if not solvable:
        print(f"\n{Fore.RED}[!] Aborting: Cannot solve an unsolvable grid. Please re-run or recalibrate.")
        return

    solver = SlidingSolver(grid, config['rows'], config['cols'])
    moves = solver.solve()
    if moves:
        cell_w, cell_h = config['width'] / config['cols'], config['height'] / config['rows']
        print(f"\n{Fore.CYAN}Executing {len(moves)} moves. STAY AWAY FROM MOUSE!")
        time.sleep(2)
        for r, c in moves:
            # Emergency stop check (Esc key)
            if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
                print(f"\n{Fore.RED}[!] Emergency Stop: ESC pressed. Stopping solver.")
                break
            pyautogui.click(config['left'] + int((c+0.5)*cell_w), config['top'] + int((r+0.5)*cell_h))
            time.sleep(MOVE_DELAY)
        print(f"{Fore.GREEN}Done!")
    else:
        print(f"\n{Fore.RED}[!] Failed to compute a stable path.")
        print("Current Grid State observed on failure:")
        for r, row in enumerate(solver.grid):
            print(f"Row {r}: {row}")
        print("Grid state might be incorrect or OCR misread a tile.")

if __name__ == "__main__": main()
