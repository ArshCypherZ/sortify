# Sortify: Offline Private AI File Organizer

**Automatically organize your files.**

Sortify is a privacy-focused file organizer that runs in the background. It watches your folders, reads file contents, and moves them to appropriate locations automatically.

## Key Features

*   Reads file contents, not just filenames. It can identify that a PDF containing physics content belongs in your Physics folder.
*   Automatically renames generic files based on their content.
*   Runs offline using local models. Your data stays on your device.
*   Moves uncertain files to a review folder instead of guessing.
*   Tracks all moves in a database for easy undo.
*   Efficient and lightweight. Uses file system events instead of constant scanning.

## Getting Started

### Prerequisites
- Python 3.10+
- Linux

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ArshCypherZ/sortify.git
    cd sortify
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

1.  **Start the Application:**
    ```bash
    python3 run.py
    ```

2.  **First Run Setup:**
    - A wizard will appear asking you which folder to watch (usually `~/Downloads`).
    - It will scan your documents to learn your existing folder structure.

3.  **Sit Back & Relax:**
    - Download a file.
    - Watch it disappear from Downloads and reappear in the correct category folder!
    - Check the System Tray icon to pause or view logs.

## Configuration
Sortify creates a hidden folder at `~/.sortify/` to store your settings, logs, and database.

## Troubleshooting
- **Logs:** Check `~/.sortify/sortify.log` if something goes wrong.
- **Battery:** Sortify pauses automatically if your laptop is unplugged and low on battery.
- **Memory:** Tested on 105 files simultaneously, ram usage peaks at ~ 1GB.

---
*Built with ❤️ for a clutter-free digital life.*
