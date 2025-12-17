from enum import Enum

class Strings(str, Enum):
    WELCOME_MSG = "[bold magenta]Welcome to Sortify![/bold magenta]\n\nLet's get you set up."
    
    CHOOSE_MODE = "\n[bold]Choose Operation Mode:[/bold]"
    MODE_ZERO_CONFIG = "  [cyan]1. Zero-Config:[/cyan] Automatic classification. Easiest."
    MODE_RULE_MAKER = "  [cyan]2. Rule-Maker:[/cyan] You provide hints. More controlled."
    PROMPT_SELECT_MODE = "Select Mode"
    
    PROMPT_WATCH_DIR = "Enter directories to watch (comma separated)"
    
    SETUP_COMPLETE = "\n[bold green]Setup Complete![/bold green]"
    SUMMARY_MODE = "  Mode: {}"
    SUMMARY_WATCHING = "  Watching: {}"
    
    PROMPT_SAVE_START = "Save and Start?"
    CONFIG_SAVED = "Configuration saved."
    SETUP_CANCELLED = "Setup cancelled. Exiting."
    
    # Main App
    STARTING_APP = "Starting {} in {} mode..."
    DRY_RUN_ENABLED = "DRY RUN MODE ENABLED. No files will be moved."
    STOPPING_APP = "Stopping Sortify..."
    FATAL_ERROR = "Fatal error: {}"
    
    # Watcher
    WATCHER_STARTED = "Watcher started on: {}"
    WATCHER_STOPPED = "Watcher stopped."
    NEW_FILE_DETECTED = "New file detected: {}"
    
    # Processor
    PROCESSOR_STARTED = "Processor started."
    PROCESSOR_STOPPED = "Processor stopped."
    FILE_NOT_FOUND = "File not found (moved/deleted?): {}"
    PROCESSING_FILE = "Processing: {}"
    PHASE_1_COMPLETE = "Phase 1 Complete for {}. Category: {}"
    ERROR_PROCESSING = "Error processing {}: {}"

    # UI
    TRAY_TOOLTIP = "Sortify - File Organizer"
    MENU_OPEN_LOGS = "Open Logs"
    MENU_OPEN_FOLDER = "Open Watch Folder"
    MENU_PAUSE = "Pause Sorting"
    MENU_RESUME = "Resume Sorting"
    MENU_EXIT = "Exit"
    
    NOTIF_TITLE = "Sortify"
    NOTIF_MOVED = "Moved '{}' to '{}'"
    NOTIF_QUARANTINE = "Moved '{}' to Review"
    
    # Utils
    BATTERY_LOW = "Battery low ({}%). Pausing Sortify."
    BATTERY_OK = "Battery level ok. Resuming."
    PROCESSOR_PAUSED = "Processor paused."
    PROCESSOR_RESUMED = "Processor resumed."