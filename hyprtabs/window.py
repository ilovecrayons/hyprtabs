"""
Window class for HyprTabs - optimized for performance.
"""
from .constants import ICONS

class Window:
    """Represents a window (either minimized or active) - optimized"""
    
    # Cache for icons to avoid repeated lookups
    _icon_cache = {}
    
    def __init__(self, address: str, title: str, class_name: str, workspace: int, is_minimized: bool = False):
        self.address = address
        self.title = title
        self.class_name = class_name
        self.workspace = workspace
        self.is_minimized = is_minimized
        self.icon = self._get_icon_cached()
        self.short_addr = address[-4:] if len(address) >= 4 else address
        
    def _get_icon_cached(self) -> str:
        """Get icon for the window based on its class with caching"""
        # Check cache first
        if self.class_name in Window._icon_cache:
            return Window._icon_cache[self.class_name]
        
        # Find icon
        class_lower = self.class_name.lower()
        icon = ICONS["default"]  # Default fallback
        
        for app_name, app_icon in ICONS.items():
            if app_name != "default" and app_name.lower() in class_lower:
                icon = app_icon
                break
        
        # Cache the result
        Window._icon_cache[self.class_name] = icon
        return icon
    
    @property
    def display_title(self) -> str:
        """Get formatted display title"""
        status = "Hidden" if self.is_minimized else f"WS {self.workspace}"
        return f"{self.icon} {self.class_name} - {self.title} [{status}]"
