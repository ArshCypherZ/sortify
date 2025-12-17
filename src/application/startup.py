from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from src.config.settings import settings, save_settings
from src.utils.logger import logger
from src.i18n.strings import Strings

console = Console()

def run_wizard():
    console.print(Panel.fit(Strings.WELCOME_MSG.value))
    
    console.print(Strings.CHOOSE_MODE.value)
    console.print(Strings.MODE_ZERO_CONFIG.value)
    console.print(Strings.MODE_RULE_MAKER.value)
    
    mode_choice = Prompt.ask(Strings.PROMPT_SELECT_MODE.value, choices=["1", "2"], default="1")
    mode = "zero-config" if mode_choice == "1" else "rule-maker"

    default_watch = str(Path.home() / "Downloads")
    watch_dirs_input = Prompt.ask(Strings.PROMPT_WATCH_DIR.value, default=default_watch)
    watch_dirs = [Path(p.strip()) for p in watch_dirs_input.split(",")]

    console.print(Strings.SETUP_COMPLETE.value)
    console.print(Strings.SUMMARY_MODE.value.format(mode))
    console.print(Strings.SUMMARY_WATCHING.value.format(', '.join(str(p) for p in watch_dirs)))
    
    if Confirm.ask(Strings.PROMPT_SAVE_START.value):
        new_settings = {
            "MODE": mode,
            "MODEL_TYPE": "local",
            "WATCH_DIRECTORIES": [str(p) for p in watch_dirs]
        }
        
        settings.MODE = mode
        settings.MODEL_TYPE = "local"
        settings.WATCH_DIRECTORIES = watch_dirs
        
        save_settings(new_settings)
            
        logger.info(Strings.CONFIG_SAVED.value)
        return True
    return False

if __name__ == "__main__":
    run_wizard()
