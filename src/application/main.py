import sys
import time
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from src.config.settings import settings
from src.utils.logger import logger
from src.i18n.strings import Strings
from src.application.startup import run_wizard
from src.application.controller import SortifyController

def main():
    try:
        config_exists = settings.CONFIG_FILE.exists()
        
        if not config_exists or not settings.AUTO_START or "--setup" in sys.argv:
             logger.info("Configuration missing or setup requested. Starting Setup Wizard...")
             if not run_wizard():
                logger.info(Strings.SETUP_CANCELLED.value)
                return
        else:
            if "--setup" in sys.argv:
                if not run_wizard():
                    return

        from src.utils.logger import setup_logger
        setup_logger(log_file=settings.LOG_FILE)

        logger.info(Strings.STARTING_APP.value.format(settings.APP_NAME, settings.MODE))
        if settings.DRY_RUN:
            logger.info("DRY RUN MODE ENABLED. No files will be moved.")

        controller = SortifyController()
        controller.start()

        def stop_app():
            logger.info(Strings.STOPPING_APP.value)
            controller.stop()
            
        headless = "--headless" in sys.argv
        from src.ui.tray import SortifyUI
        ui = SortifyUI(controller, stop_callback=stop_app, headless=headless)
        controller.ui = ui
        
        ui.run()
            
    except Exception as e:
        logger.critical(Strings.FATAL_ERROR.value.format(e), exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
