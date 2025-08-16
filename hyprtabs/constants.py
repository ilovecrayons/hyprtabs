"""
Constants for HyprTabs.
"""

# Directories and Files
CACHE_DIR = "/tmp/minimize-state"
CACHE_FILE = f"{CACHE_DIR}/windows.json"
PREVIEW_DIR = "/tmp/window-previews"
LOCK_FILE = "/tmp/hyprtabs.lock"
FIFO_FILE = "/tmp/hyprtabs.fifo"

# Icon mapping for different applications
ICONS = {
    "firefox": "",
    "alacritty": "",
    "discord": "󰙯",
    "steam": "",
    "chromium": "",
    "code": "󰨞",
    "spotify": "",
    "default": "󰖲",
}
