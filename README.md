# Python Tools Repository

A collection of automation tools and solvers for various games and tasks, utilizing OCR, image processing, and pathfinding algorithms.

## 🚀 Key Projects

### 1. 🧩 Sliding Puzzle Solver (`zippuzzle.py`)
An advanced automated solver for sliding puzzles (e.g., 5x5, 7x7, 8x8).
- **Features**:
    - **OCR Detection**: Uses `easyocr` to identify tile numbers and the empty slot.
    - **Advanced Pathfinding**: Combines standard BFS with a specialized **Mini-Solver BFS** for complex grid endings (row-ends, col-ends, and the final 2x2).
    - **Emergency Stop**: Press **`Esc`** to immediately stop mouse automation.
    - **Calibration**: Interactive setup for defining the puzzle area on your screen.

### 2. 🔢 Sudoku Solver (`sudoku.py`)
Automatically solves Sudoku puzzles on web or desktop.
- **Features**:
	- Interactive calibration for the 9x9 grid.
	- Real-time OCR reading of the initial numbers.
	- Automated input of the solution into the game interface.

### 3. ➕ Idle IQ Math Solver (`giaitoan.py`)
Automated solver for math-based "Idle IQ" games.
- **Features**:
	- Reads math expressions from the screen.
	- Automates clicks based on computed answers.

### 4. ☁️ GCP Account Automation (`main.py` & `main_reverse.py`)
Scripts for automating Google Cloud Platform account registration and status tracking.
- **Features**:
	- Browser-based automation for account setup.
	- Integration with spreadsheets for tracking "Done/Error" statuses.

## 🛠 Prerequisites

Ensure you have the following installed:
- Python 3.10+
- Dependencies:
  ```bash
  pip install easyocr pyautogui opencv-python numpy mss pillow torch torchvision
  ```

## 📖 General Instructions

1.  **Preparation**: Open the game or task interface you want to automate.
2.  **Calibration**: Most scripts will prompt for calibration if a config file is missing. Follow the on-screen instructions to select the target area with your mouse.
3.  **Execution**: Press **Enter** in the terminal to start the process.
4.  **Safety**:
    - **Emergency Stop**: Press **`Esc`** (supported in `zippuzzle.py`) or move your mouse to any corner of the screen to trigger the Fail-Safe.

---
*Created with ❤️ by Antigravity*
