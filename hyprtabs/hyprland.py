"""
Hyprland window manager for HyprTabs.
"""
import json
import os
import subprocess
import sys
import time
from typing import List, Optional

from .constants import CACHE_DIR, CACHE_FILE
from .window import Window

class WindowManager:
    """Handles Hyprland window operations"""
    
    # Cache for window data to reduce hyprctl calls
    _window_cache = None
    _cache_timestamp = 0
    _cache_duration = 0.1  # Cache for 100ms for instant startup
    
    @staticmethod
    def _get_cached_windows() -> Optional[dict]:
        """Get cached window data if it's still fresh"""
        current_time = time.time()
        if (WindowManager._window_cache is not None and 
            current_time - WindowManager._cache_timestamp < WindowManager._cache_duration):
            return WindowManager._window_cache
        return None
    
    @staticmethod
    def _cache_windows(windows_data: dict):
        """Cache window data"""
        WindowManager._window_cache = windows_data
        WindowManager._cache_timestamp = time.time()
    
    @staticmethod
    def run_hyprctl(command: List[str]) -> Optional[str]:
        """Run hyprctl command and return output"""
        try:
            result = subprocess.run(
                ["hyprctl"] + command,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"hyprctl command failed: {e}", file=sys.stderr)
            return None
    
    @staticmethod
    def get_active_windows() -> List[Window]:
        """Get all active (non-minimized) windows"""
        output = WindowManager.run_hyprctl(["clients", "-j"])
        if not output:
            return []
        
        try:
            clients = json.loads(output)
            windows = []
            
            for client in clients:
                # Skip special workspaces (minimized windows are in special:minimum)
                if client.get("workspace", {}).get("name", "").startswith("special:"):
                    continue
                    
                window = Window(
                    address=client.get("address", ""),
                    title=client.get("title", ""),
                    class_name=client.get("class", ""),
                    workspace=client.get("workspace", {}).get("id", 1),
                    is_minimized=False
                )
                windows.append(window)
            
            return windows
        except json.JSONDecodeError:
            return []
    
    @staticmethod
    def get_minimized_windows() -> List[Window]:
        """Get all minimized windows from cache"""
        if not os.path.exists(CACHE_FILE):
            return []
        
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
            
            windows = []
            for item in data:
                window = Window(
                    address=item.get("address", ""),
                    title=item.get("original_title", ""),
                    class_name=item.get("class", ""),
                    workspace=0,  # Minimized windows don't have a workspace
                    is_minimized=True
                )
                windows.append(window)
            
            return windows
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    @staticmethod
    def get_all_windows() -> List[Window]:
        """Get all windows (active + minimized)"""
        active_windows = WindowManager.get_active_windows()
        minimized_windows = WindowManager.get_minimized_windows()
        return active_windows + minimized_windows
    
    @staticmethod
    def focus_window(window: Window) -> bool:
        """Focus a window and bring it to front"""
        if window.is_minimized:
            return WindowManager.restore_window(window)
        else:
            # Switch to the window's workspace first if needed
            if window.workspace > 0:
                output1 = WindowManager.run_hyprctl([
                    "dispatch", "workspace", str(window.workspace)
                ])
            
            # Focus the window
            output2 = WindowManager.run_hyprctl([
                "dispatch", "focuswindow", f"address:{window.address}"
            ])
            
            # Bring to front to ensure it's actually focused
            output3 = WindowManager.run_hyprctl([
                "dispatch", "bringactivetotop"
            ])
            
            return output2 is not None
    
    @staticmethod
    def minimize_window(window: Window) -> bool:
        """Minimize a window"""
        if window.is_minimized:
            return True  # Already minimized
            
        # Move to special workspace
        output = WindowManager.run_hyprctl([
            "dispatch", "movetoworkspacesilent", 
            f"special:minimum,address:{window.address}"
        ])
        
        if output is not None:
            # Add to cache
            WindowManager._add_to_cache(window)
            return True
        return False
    
    @staticmethod
    def restore_window(window: Window) -> bool:
        """Restore a minimized window"""
        if not window.is_minimized:
            return True  # Already active
        
        # Get current workspace
        workspace_info = WindowManager.run_hyprctl(["activeworkspace", "-j"])
        if not workspace_info:
            return False
        
        try:
            workspace_data = json.loads(workspace_info)
            current_ws = workspace_data.get("id", 1)
        except json.JSONDecodeError:
            current_ws = 1
        
        # Move from special workspace to current workspace
        output = WindowManager.run_hyprctl([
            "dispatch", "movetoworkspace",
            f"{current_ws},address:{window.address}"
        ])
        
        if output is not None:
            # Ensure the current workspace is active
            WindowManager.run_hyprctl([
                "dispatch", "workspace", str(current_ws)
            ])
            
            # Focus the window after restoring
            WindowManager.run_hyprctl([
                "dispatch", "focuswindow", f"address:{window.address}"
            ])
            
            # Bring to front to ensure visibility
            WindowManager.run_hyprctl([
                "dispatch", "bringactivetotop"
            ])
            
            # Remove from cache
            WindowManager._remove_from_cache(window)
            return True
        return False
    
    @staticmethod
    def _add_to_cache(window: Window):
        """Add window to minimized cache"""
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        # Read existing cache
        cached_windows = []
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r') as f:
                    cached_windows = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                cached_windows = []
        
        # Add new window
        window_data = {
            "address": window.address,
            "display_title": window.display_title,
            "class": window.class_name,
            "original_title": window.title,
            "preview": "",
            "icon": window.icon
        }
        
        # Check if already exists
        for i, cached in enumerate(cached_windows):
            if cached.get("address") == window.address:
                cached_windows[i] = window_data
                break
        else:
            cached_windows.append(window_data)
        
        # Write back to cache
        with open(CACHE_FILE, 'w') as f:
            json.dump(cached_windows, f)
    
    @staticmethod
    def _remove_from_cache(window: Window):
        """Remove window from minimized cache"""
        if not os.path.exists(CACHE_FILE):
            return
        
        try:
            with open(CACHE_FILE, 'r') as f:
                cached_windows = json.load(f)
            
            # Remove the window
            cached_windows = [
                w for w in cached_windows 
                if w.get("address") != window.address
            ]
            
            # Write back to cache
            with open(CACHE_FILE, 'w') as f:
                json.dump(cached_windows, f)
                
        except (json.JSONDecodeError, FileNotFoundError):
            pass
