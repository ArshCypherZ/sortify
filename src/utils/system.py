import psutil
from .logger import logger
from src.i18n.strings import Strings

def check_battery_ok(threshold: int = 0) -> bool:
    """
    Checks if battery is above threshold or plugged in.
    Returns True if OK to proceed.
    """
    try:
        battery = psutil.sensors_battery()
        if not battery:
            return True # No battery (Desktop)
            
        if battery.power_plugged:
            return True
            
        if battery.percent < threshold:
            logger.warning(Strings.BATTERY_LOW.format(battery.percent))
            return False
            
        return True
    except Exception as e:
        logger.error(f"Battery check failed: {e}")
        return True # Fail safe

import hashlib
from pathlib import Path

def calculate_file_hash(file_path: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# -------------------------------------------------------------------------
# Resource Guard
# -------------------------------------------------------------------------
class ResourceGuard:
    """
    Monitors system resources (RAM, Battery) to prevent operation during critical states.
    """
    def __init__(self, min_ram_mb=500, min_battery=20):
        self.min_ram_mb = min_ram_mb
        self.min_battery = min_battery

    def check(self) -> bool:
        """
        Returns True if resources are sufficient.
        """
        # 1. Battery Check
        if not check_battery_ok(self.min_battery):
            return False

        # 2. RAM Check
        try:
            free_mem = psutil.virtual_memory().available / (1024 * 1024)
            if free_mem < self.min_ram_mb:
                logger.warning(f"Low RAM ({free_mem:.2f} MB). Pausing specific heavy ops.")
                if free_mem < 100:
                    return False
            return True
        except Exception:
            return True

resource_guard = ResourceGuard()
