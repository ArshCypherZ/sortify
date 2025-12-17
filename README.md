<div align="center">

<h1>✨ Sortify ✨</h1>

<img src="assets/sortify.png" alt="Sortify" width="320" />

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

</div>

**Automatically organize your files.**

Sortify is a privacy-focused file organizer that runs in the background. It watches your folders, reads file contents, and moves them to appropriate locations automatically.

## Key Features

*   Reads file contents, not just filenames.
*   Automatically renames generic files based on their content.
*   Runs offline using local models.
*   Moves uncertain files to a review folder instead of guessing.
*   Tracks all moves in a database for easy undo.
*   Efficient and lightweight.

## Getting Started

### Prerequisites
- Python 3.10+
- Linux

<h2 align="center"> 
   ⇝ Installation ⇜
</h2>

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

<h2 align="center"> 
   ⇝ Run Directly ⇜
</h2>

```bash
python3 run.py
```

<h2 align="center"> 
   ⇝ Setup ⇜
</h2>

- A wizard will appear asking you which folder to watch (usually `~/Downloads`).
- It will scan your documents to learn your existing folder structure.
- Download a file.
- Watch it disappear from Downloads and reappear in the correct category folder!

## Configuration
Sortify creates a hidden folder at `~/.sortify/` to store your settings, logs, and database.

## Troubleshooting
- **Logs:** Check `~/.sortify/sortify.log` if something goes wrong.
- **Battery:** Sortify pauses automatically if your laptop is unplugged and low on battery.
- **Memory:** Tested on 105 files simultaneously, ram usage peaks at ~ 1GB.

---

*Built with ❤️ for a clutter-free digital life.*
