import easyocr
import pyautogui
import cv2
import numpy as np
import time
import json
import os
import re
import ctypes
from PIL import Image
from mss import mss
from collections import deque

# --- CONFIG ---
CONFIG_FILE = "2048_config.json"
MOVE_DELAY = 0.5  # Increased for browser animations
# OCR is no longer used for the main loop, but we keep the import if needed for fallback
# reader = None 

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
    print("\n--- 2048 Calibration ---")
    print("Move mouse to TOP-LEFT of the 4x4 GRID and press Enter.")
    input()
    tl = pyautogui.position()
    print("Move mouse to BOTTOM-RIGHT and press Enter.")
    input()
    br = pyautogui.position()
    config = {"top": tl.y, "left": tl.x, "width": br.x - tl.x, "height": br.y - tl.y}
    save_config(config)
    return config

# --- COLOR MAP (RGB) ---
COLOR_MAP = {
    (205, 193, 180): 0,    # Empty
    (238, 228, 218): 2,
    (237, 224, 200): 4,
    (242, 177, 121): 8,
    (245, 149, 99): 16,
    (246, 124, 95): 32,
    (246, 94, 59): 64,
    (237, 207, 114): 128,
    (237, 204, 97): 256,
    (237, 200, 80): 512,
    (237, 197, 63): 1024,
    (237, 194, 46): 2048,
}

def get_color_dist(c1, c2):
    return sum((int(a) - int(b)) ** 2 for a, b in zip(c1, c2))

def get_grid_state(config):
    with mss() as sct:
        img_orig = np.array(sct.grab(config))
        # mss returns BGRA, convert to RGB
        img_rgb = cv2.cvtColor(img_orig, cv2.COLOR_BGRA2RGB)
        
        grid = [[0 for _ in range(4)] for _ in range(4)]
        cell_w, cell_h = config['width'] / 4, config['height'] / 4
        
        for r in range(4):
            for c in range(4):
                # Sample at 20% offset from top-left to avoid centered text
                cx = int((c + 0.2) * cell_w)
                cy = int((r + 0.2) * cell_h)
                pixel = tuple(img_rgb[cy, cx])
                
                # Find closest color in map
                best_val = 0
                min_dist = float('inf')
                for target_color, val in COLOR_MAP.items():
                    dist = get_color_dist(pixel, target_color)
                    if dist < min_dist:
                        min_dist = dist
                        best_val = val
                
                grid[r][c] = best_val
        return grid

# --- 2048 Game Logic ---

def get_moves(board):
    moves = []
    for m in ['left', 'right', 'up', 'down']:
        res = simulate_move(board, m)
        if not np.array_equal(board, res):
            moves.append(m)
    return moves

def simulate_move(board, direction):
    b = np.array(board)
    if direction == 'up':
        b = b.T
        b = np.array([merge(row) for row in b])
        b = b.T
    elif direction == 'down':
        b = b.T
        b = np.array([merge(row[::-1])[::-1] for row in b])
        b = b.T
    elif direction == 'left':
        b = np.array([merge(row) for row in b])
    elif direction == 'right':
        b = np.array([merge(row[::-1])[::-1] for row in b])
    return b

def merge(row):
    # Remove zeros
    non_zero = [x for x in row if x != 0]
    new_row = []
    skip = False
    for i in range(len(non_zero)):
        if skip:
            skip = False
            continue
        if i + 1 < len(non_zero) and non_zero[i] == non_zero[i+1]:
            new_row.append(non_zero[i] * 2)
            skip = True
        else:
            new_row.append(non_zero[i])
    # Pad with zeros
    return new_row + [0] * (len(row) - len(new_row))

# --- AI Strategy ---

# Heuristic weights for a strong "snake" pattern in a corner
W = np.array([
    [1000, 500, 250, 125],
    [15,   31,  62,  125],
    [15,   7,   3,   1],
    [0,    0,   0,   0]
])

def evaluate(board):
    b = np.array(board)
    if not 0 in b and not get_moves(board):
        return -1e10  # Game Over penalty
        
    score = np.sum(b * W)
    
    # Bonus for empty cells (exponential is better)
    empty_tiles = np.count_nonzero(b == 0)
    score += (empty_tiles ** 2) * 10 
    
    return score

def expectimax(board, depth, is_max):
    if depth == 0:
        return evaluate(board)
    
    if is_max:
        best_val = -float('inf')
        possible_moves = get_moves(board)
        if not possible_moves:
            return evaluate(board)
        for m in possible_moves:
            res = simulate_move(board, m)
            val = expectimax(res, depth - 1, False)
            best_val = max(best_val, val)
        return best_val
    else:
        # Chance node: computer adds a random 2 or 4
        empty_cells = list(zip(*np.where(np.array(board) == 0)))
        if not empty_cells:
            return evaluate(board)
            
        total_val = 0
        # Sample up to 4 empty cells for speed
        samples = empty_cells[:4]
        for r, c in samples:
            b2 = np.array(board)
            b2[r][c] = 2
            total_val += expectimax(b2, depth - 1, True)
            
        return total_val / len(samples)

# --- Main App ---

def get_best_move(board):
    best_val = -float('inf')
    best_move = None
    possible_moves = get_moves(board)
    
    if not possible_moves:
        return None
        
    for m in possible_moves:
        res = simulate_move(board, m)
        val = expectimax(res, 2, False) # Depth 2 for speed
        if val > best_val:
            best_val = val
            best_move = m
            
    return best_move

def main():
    config = load_config()
    if not config:
        config = calibrate()
    
    print("\nStarting 2048 Solver...")
    print("Switch to the 2048 tab NOW! Starting in 5 seconds...")
    for i in range(5, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    print("\nRunning... Press ESC at any time to STOP.")
    
    last_grid = None
    stuck_count = 0
    
    while True:
        # Emergency stop check
        if ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000:
            print("Emergency Stop triggered.")
            break
            
        grid = get_grid_state(config)
        
        if last_grid is not None and np.array_equal(grid, last_grid):
            stuck_count += 1
            if stuck_count > 3:
                print("Board seems stuck. Diagnostic info:")
                # Sample colors again for debug
                with mss() as sct:
                    img = np.array(sct.grab(config))
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                    cell_w, cell_h = config['width'] / 4, config['height'] / 4
                    p = tuple(img_rgb[int(0.2*cell_h), int(0.2*cell_w)])
                    print(f"Top-left cell [0,0] color: {p}")
                
                pyautogui.press(np.random.choice(['up', 'down', 'left', 'right']))
                time.sleep(1)
                stuck_count = 0
                continue
        else:
            stuck_count = 0
        
        last_grid = np.array(grid)
        
        # Show grid for debugging
        print("\nCurrent Board State:")
        for row in grid:
            print("\t", row)
            
        move = get_best_move(grid)
        
        if move:
            print(f"Decided move: {move.upper()}")
            pyautogui.press(move)
            time.sleep(MOVE_DELAY)
        else:
            print("Game Over or stuck. Please check the grid.")
            break

if __name__ == "__main__":
    main()
