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

CONFIG_FILE = "sudoku_config.json"
INPUT_DELAY = 0.05
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
    print("Config saved.")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def calibrate():
    print("\n--- Sudoku Calibration ---")
    print("Move mouse to TOP-LEFT of the 9x9 GRID and press Enter.")
    input()
    tl = pyautogui.position()
    print("Move mouse to BOTTOM-RIGHT of the 9x9 GRID and press Enter.")
    input()
    br = pyautogui.position()
    
    config = {
        "top": tl.y,
        "left": tl.x,
        "width": br.x - tl.x,
        "height": br.y - tl.y
    }
    save_config(config)
    return config

def is_valid(board, r, c, num):
    for i in range(9):
        if board[r][i] == num or board[i][c] == num:
            return False
    start_r, start_c = 3 * (r // 3), 3 * (c // 3)
    for i in range(3):
        for j in range(3):
            if board[start_r + i][start_c + j] == num:
                return False
    return True

def solve_board(board):
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                for num in range(1, 10):
                    if is_valid(board, r, c, num):
                        board[r][c] = num
                        if solve_board(board):
                            return True
                        board[r][c] = 0
                return False
    return True

def get_sudoku_grid(config):
    with mss() as sct:
        img_orig = np.array(sct.grab(config))
        img = cv2.cvtColor(img_orig, cv2.COLOR_BGRA2GRAY)
        
        cell_w = config['width'] / 9
        cell_h = config['height'] / 9
        
        board = [[0 for _ in range(9)] for _ in range(9)]
        is_empty = [[True for _ in range(9)] for _ in range(9)]
        
        print("Scanning grid cells...")
        
        cell_imgs = []
        for r in range(9):
            for c in range(9):
                x1, y1 = int(c * cell_w), int(r * cell_h)
                x2, y2 = int((c + 1) * cell_w), int((r + 1) * cell_h)
                
                cell = img[y1:y2, x1:x2]
                margin_w, margin_h = int(cell_w * 0.15), int(cell_h * 0.15)
                cell_inner = cell[margin_h:-margin_h, margin_w:-margin_w]
                
                cell_up = cv2.resize(cell_inner, (64, 64), interpolation=cv2.INTER_CUBIC)
                cell_imgs.append(cell_up)

        results = get_reader().readtext_batched(cell_imgs)
        
        for i, res in enumerate(results):
            r, c = i // 9, i % 9
            if res:
                for (_, text, prob) in res:
                    num_match = re.search(r'[1-9]', text)
                    if num_match:
                        board[r][c] = int(num_match.group())
                        is_empty[r][c] = False
                        break
        
        return board, is_empty

def fill_sudoku(config, board, is_empty):
    cell_w = config['width'] / 9
    cell_h = config['height'] / 9
    
    print("Filling in the blanks...")
    for r in range(9):
        for c in range(9):
            if is_empty[r][c]:
                cx = config['left'] + int((c + 0.5) * cell_w)
                cy = config['top'] + int((r + 0.5) * cell_h)
                
                pyautogui.click(cx, cy)
                pyautogui.press(str(board[r][c]))
                time.sleep(INPUT_DELAY)

def main():
    config = load_config()
    if not config:
        config = calibrate()
    
    print("\nPress Enter to START solving (Make sure the game is visible!)")
    input()
    
    start_time = time.time()
    board, is_empty = get_sudoku_grid(config)
    
    print("--- Initial Board ---")
    for row in board: print(row)
    
    if solve_board(board):
        print(f"Solved in {time.time() - start_time:.2f}s")
        print("--- Solution ---")
        for row in board: print(row)
        
        fill_sudoku(config, board, is_empty)
        print("\nDone!")
    else:
        print("Could not find a valid solution. Please check the calibration.")

if __name__ == "__main__":
    main()
