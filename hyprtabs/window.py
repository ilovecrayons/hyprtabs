"""
Window class for HyprTabs.
"""
from .constants import ICONS

class Window:
    """Represents a window (either minimized or active)"""
    def __init__(self, address: str, title: str, class_name: str, workspace: int, is_minimized: bool = False):
        self.address = address
        self.title = title
        self.class_name = class_name
        self.workspace = workspace
        self.is_minimized = is_minimized
        self.icon = self._get_icon()
        self.short_addr = address[-4:] if len(address) >= 4 else address
        
    def _get_icon(self) -> str:
        """Get icon for the window based on its class"""
        for app_name, icon in ICONS.items():
            if app_name.lower() in self.class_name.lower():
                return icon
        return ICONS["default"]
    
    @property
    def display_title(self) -> str:
        """Get formatted display title"""
        status = "Hidden" if self.is_minimized else f"WS {self.workspace}"
        return f"{self.icon} {self.class_name} - {self.title} [{status}]"
