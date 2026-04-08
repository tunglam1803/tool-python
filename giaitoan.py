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

CONFIG_FILE = "idleiq_config.json"
DELAY_BETWEEN_CLICKS = 1.2
OCR_LANGUAGES = ['en']

reader = None

def get_reader():
    global reader
    if reader is None:
        print("Loading OCR engine...")
        reader = easyocr.Reader(OCR_LANGUAGES, gpu=False)
    return reader

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    print(f"Config saved to {CONFIG_FILE}")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def get_bbox():
    print("Move mouse to TOP-LEFT of the region and press Enter.")
    input()
    tl = pyautogui.position()
    print("Move mouse to BOTTOM-RIGHT of the region and press Enter.")
    input()
    br = pyautogui.position()
    return {
        "top": tl.y,
        "left": tl.x,
        "width": br.x - tl.x,
        "height": br.y - tl.y
    }

def calibrate():
    print("\n--- CALIBRATION ---")
    print("STEP 1: Select the QUESTION region (the math expression area).")
    q_bbox = get_bbox()
    
    print("\nSTEP 2: Select the ANSWERS region (the area containing all 4 buttons).")
    a_bbox = get_bbox()
    
    config = {"q": q_bbox, "a": a_bbox}
    save_config(config)
    return config

def smart_solve(expression, candidate_answers):
    mapping = {'÷': '/', ':': '/', 'x': '*', 'X': '*', ',': '.'}
    expr = expression
    for sym, op in mapping.items():
        expr = expr.replace(sym, op)
    
    nums = [float(s) for s in re.findall(r'\d+\.?\d*', expr)]
    
    if len(nums) < 2:
        return None

    clean_expr = re.sub(r'[^0-9+\-*/(). ]', ' ', expr).strip()
    try:
        if any(op in clean_expr for op in '+-*/'):
            val = eval(re.sub(r'[=? ]+$', '', clean_expr))
            res = int(round(val))
            if res in candidate_answers:
                return res
    except:
        pass

    print("Falling back to brute-force inference...")
    a, b = nums[0], nums[1]
    results = [a + b, a - b, a * b]
    if b != 0: results.append(a / b)
    
    for r in results:
        curr_res = int(round(r))
        if curr_res in candidate_answers:
            print(f"Match found by inference: {curr_res}")
            return curr_res
            
    return None

def preprocess_image(img_arr):
    img = cv2.cvtColor(img_arr, cv2.COLOR_BGRA2BGR)
    
    height, width = img.shape[:2]
    img = cv2.resize(img, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    return img

def find_and_solve(config):
    with mss() as sct:
        a_img_orig = np.array(sct.grab(config['a']))
        a_img = preprocess_image(a_img_orig)
        
        a_results = get_reader().readtext(cv2.cvtColor(a_img, cv2.COLOR_BGR2RGB))
        
        options = []
        for (rect, text, prob) in a_results:
            num_match = re.search(r'\d+', text)
            if num_match:
                rx = (rect[0][0] + rect[2][0]) / 2 / 2
                ry = (rect[0][1] + rect[2][1]) / 2 / 2
                
                cx = rx + config['a']['left']
                cy = ry + config['a']['top']
                options.append({"val": int(num_match.group()), "pos": (cx, cy)})
        
        candidate_answers = list(set([o['val'] for o in options]))
        print(f"Candidates detected: {candidate_answers}")

        q_img_orig = np.array(sct.grab(config['q']))
        q_img = preprocess_image(q_img_orig)
        
        q_results = get_reader().readtext(cv2.cvtColor(q_img, cv2.COLOR_BGR2RGB))
        question_text = " ".join([r[1] for r in q_results])
        print(f"Question: {question_text}")
        
        answer = smart_solve(question_text, candidate_answers)
        
        if answer is not None:
            for opt in options:
                if opt['val'] == answer:
                    print(f"Match found! Clicking {answer} at {opt['pos']}...")
                    time.sleep(DELAY_BETWEEN_CLICKS)
                    pyautogui.click(opt['pos'])
                    return True
        else:
            print("Answer not in candidates or solve failed.")
            
    return False

def main():
    config = load_config()
    if not config or 'q' not in config:
        config = calibrate()
    
    print("\n--- AUTO SOLVER RUNNING ---")
    while True:
        try:
            if find_and_solve(config):
                time.sleep(4)
            else:
                time.sleep(1.5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
