#!/usr/bin/env python3
import sys
from pathlib import Path

# Ensure the project root is in sys.path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

if __name__ == "__main__":
    try:
        from src.application.main import main
        main()
    except ImportError as e:
        print(f"Error starting application: {e}")
        sys.exit(1)
