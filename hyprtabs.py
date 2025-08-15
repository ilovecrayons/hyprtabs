#!/usr/bin/env python3
"""
HyprTabs - Advanced Alt-Tab window switcher with minimize/restore for Hyprland
Replaces the broken niflveil restore menu with a proper cycling interface
"""

import json
import subprocess
import sys
import os
import signal
import threading
import time
import fcntl
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

# Constants
CACHE_DIR = "/tmp/minimize-state"
CACHE_FILE = "/tmp/minimize-state/windows.json"
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

class SingletonManager:
    """Manages singleton instance and inter-process communication"""
    
    @staticmethod
    def is_running() -> bool:
        """Check if another instance is running"""
        return os.path.exists(LOCK_FILE)
    
    @staticmethod
    def acquire_lock() -> bool:
        """Acquire singleton lock"""
        try:
            lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode())
            os.close(lock_fd)
            return True
        except OSError:
            return False
    
    @staticmethod
    def release_lock():
        """Release singleton lock"""
        try:
            os.unlink(LOCK_FILE)
        except OSError:
            pass
    
    @staticmethod
    def send_command(command: str) -> bool:
        """Send command to running instance"""
        if not os.path.exists(FIFO_FILE):
            return False
        
        try:
            with open(FIFO_FILE, 'w') as fifo:
                fifo.write(command + '\n')
                fifo.flush()
            return True
        except (OSError, IOError):
            return False
    
    @staticmethod
    def create_fifo():
        """Create FIFO for communication"""
        try:
            if os.path.exists(FIFO_FILE):
                os.unlink(FIFO_FILE)
            os.mkfifo(FIFO_FILE)
        except OSError:
            pass

class WindowManager:
    """Handles Hyprland window operations"""
    
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
        """Focus a window"""
        if window.is_minimized:
            return WindowManager.restore_window(window)
        else:
            output = WindowManager.run_hyprctl([
                "dispatch", "focuswindow", f"address:{window.address}"
            ])
            return output is not None
    
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
            # Focus the window
            WindowManager.run_hyprctl([
                "dispatch", "focuswindow", f"address:{window.address}"
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

class AltTabWindow(Gtk.Window):
    """Main Alt-Tab window interface"""
    
    def __init__(self):
        super().__init__()
        self.windows = []
        self.current_index = 0
        self.fifo_thread = None
        self.running = True
        self.setup_ui()
        self.setup_keybindings()
        self.load_windows()
        self.start_fifo_listener()
        
    def setup_ui(self):
        """Setup the UI"""
        self.set_title("HyprTabs")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        
        # Center on screen
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        
        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_box.set_margin_top(20)
        self.main_box.set_margin_bottom(20)
        self.main_box.set_margin_left(20)
        self.main_box.set_margin_right(20)
        self.add(self.main_box)
        
        # Title label
        self.title_label = Gtk.Label()
        self.title_label.set_markup("<b>Alt+Tab Window Switcher</b>")
        self.main_box.pack_start(self.title_label, False, False, 0)
        
        # Window list
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.main_box.pack_start(self.list_box, True, True, 0)
        
        # Instructions
        self.instructions = Gtk.Label()
        self.instructions.set_markup(
            "<small>Hold Alt + Tab to cycle • Enter to switch • Esc to cancel</small>"
        )
        self.main_box.pack_start(self.instructions, False, False, 0)
        
        # Style
        self.apply_css()
        
    def apply_css(self):
        """Apply custom CSS styling"""
        css = """
        window {
            background-color: rgba(0, 0, 0, 0.9);
            border-radius: 10px;
            border: 2px solid #555;
        }
        
        .window-item {
            padding: 10px;
            margin: 2px;
            border-radius: 5px;
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        .window-item:selected {
            background-color: rgba(100, 150, 255, 0.8);
        }
        
        .minimized {
            color: #888;
        }
        """
        
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def setup_keybindings(self):
        """Setup keyboard event handlers"""
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        
    def start_fifo_listener(self):
        """Start FIFO listener thread"""
        def listen_for_commands():
            try:
                with open(FIFO_FILE, 'r') as fifo:
                    while self.running:
                        try:
                            line = fifo.readline().strip()
                            if line:
                                GLib.idle_add(self.handle_fifo_command, line)
                        except (OSError, IOError):
                            break
            except (OSError, IOError):
                pass
        
        self.fifo_thread = threading.Thread(target=listen_for_commands, daemon=True)
        self.fifo_thread.start()
    
    def handle_fifo_command(self, command: str):
        """Handle commands received via FIFO"""
        if command == "next":
            self.cycle_next()
        elif command == "prev":
            self.cycle_prev()
        elif command == "activate":
            self.activate_current_window()
        elif command == "close":
            self.close_window()
        return False  # Don't repeat
    
    def load_windows(self):
        """Load and display all windows"""
        self.windows = WindowManager.get_all_windows()
        
        # Clear existing items
        for child in self.list_box.get_children():
            self.list_box.remove(child)
        
        # Add window items
        for i, window in enumerate(self.windows):
            row = self.create_window_row(window)
            self.list_box.add(row)
            
        # Select first item
        if self.windows:
            self.current_index = 0
            self.update_selection()
            
        self.show_all()
    
    def create_window_row(self, window: Window) -> Gtk.ListBoxRow:
        """Create a row for a window"""
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("window-item")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Icon/Status
        status_label = Gtk.Label(window.icon)
        status_label.set_size_request(30, -1)
        box.pack_start(status_label, False, False, 0)
        
        # Window info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        title_label = Gtk.Label(f"{window.class_name}")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_markup(f"<b>{window.class_name}</b>")
        info_box.pack_start(title_label, False, False, 0)
        
        subtitle_label = Gtk.Label(window.title)
        subtitle_label.set_halign(Gtk.Align.START)
        subtitle_label.set_ellipsize(3)  # ELLIPSIZE_END
        subtitle_label.set_max_width_chars(50)
        
        if window.is_minimized:
            subtitle_label.get_style_context().add_class("minimized")
            subtitle_label.set_markup(f"<i>{window.title} (Hidden)</i>")
        else:
            subtitle_label.set_text(f"{window.title} (Workspace {window.workspace})")
        
        info_box.pack_start(subtitle_label, False, False, 0)
        
        box.pack_start(info_box, True, True, 0)
        
        row.add(box)
        return row
    
    def update_selection(self):
        """Update the current selection"""
        if not self.windows:
            return
            
        # Ensure index is valid
        self.current_index = self.current_index % len(self.windows)
        
        # Select the row
        row = self.list_box.get_row_at_index(self.current_index)
        if row:
            self.list_box.select_row(row)
            
        # Update title with current window info
        if self.current_index < len(self.windows):
            current_window = self.windows[self.current_index]
            self.title_label.set_markup(
                f"<b>Window {self.current_index + 1}/{len(self.windows)}</b> - {current_window.display_title}"
            )
    
    def cycle_next(self):
        """Cycle to next window"""
        if self.windows:
            self.current_index = (self.current_index + 1) % len(self.windows)
            self.update_selection()
    
    def cycle_prev(self):
        """Cycle to previous window"""
        if self.windows:
            self.current_index = (self.current_index - 1) % len(self.windows)
            self.update_selection()
    
    def activate_current_window(self):
        """Activate the currently selected window"""
        if not self.windows or self.current_index >= len(self.windows):
            return
            
        window = self.windows[self.current_index]
        
        if window.is_minimized:
            # Restore minimized window
            WindowManager.restore_window(window)
        else:
            # Minimize active window or focus it
            # For now, let's focus it (you can change this behavior)
            WindowManager.focus_window(window)
        
        self.close_window()
    
    def close_window(self):
        """Close the alt-tab window"""
        self.running = False
        SingletonManager.release_lock()
        self.destroy()
        Gtk.main_quit()
    
    def on_key_press(self, widget, event):
        """Handle key press events"""
        keyval = event.keyval
        state = event.state
        
        # Check for Alt+Tab or Tab while Alt is held
        if keyval == Gdk.KEY_Tab:
            if state & Gdk.ModifierType.SHIFT_MASK:
                self.cycle_prev()
            else:
                self.cycle_next()
            return True
        
        # Enter or Space to activate
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_space, Gdk.KEY_KP_Enter):
            self.activate_current_window()
            return True
        
        # Escape to cancel
        elif keyval == Gdk.KEY_Escape:
            self.close_window()
            return True
            
        # Arrow keys for navigation
        elif keyval == Gdk.KEY_Down or keyval == Gdk.KEY_j:
            self.cycle_next()
            return True
        elif keyval == Gdk.KEY_Up or keyval == Gdk.KEY_k:
            self.cycle_prev()
            return True
        
        return False
    
    def on_focus_out(self, widget, event):
        """Handle focus lost - close window"""
        # Note: This might be too aggressive, you can comment it out
        # if you want the window to stay open when losing focus
        # self.close_window()
        return False

def main():
    """Main entry point"""
    # Handle non-GUI commands first
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "minimize":
            # Minimize current window
            windows = WindowManager.get_active_windows()
            if windows:
                # Get currently focused window
                active_output = WindowManager.run_hyprctl(["activewindow", "-j"])
                if active_output:
                    try:
                        active_data = json.loads(active_output)
                        active_addr = active_data.get("address", "")
                        
                        for window in windows:
                            if window.address == active_addr:
                                WindowManager.minimize_window(window)
                                break
                    except json.JSONDecodeError:
                        pass
            return
        
        elif command == "restore" and len(sys.argv) > 2:
            # Restore specific window
            window_id = sys.argv[2]
            minimized_windows = WindowManager.get_minimized_windows()
            for window in minimized_windows:
                if window.address == window_id:
                    WindowManager.restore_window(window)
                    break
            return
        
        elif command == "restore-all":
            # Restore all minimized windows
            minimized_windows = WindowManager.get_minimized_windows()
            for window in minimized_windows:
                WindowManager.restore_window(window)
            return
        
        elif command == "show":
            # Show status for waybar
            minimized_windows = WindowManager.get_minimized_windows()
            count = len(minimized_windows)
            if count > 0:
                print(f'{{"text":"󰘸 {count}","class":"has-windows","tooltip":"{count} minimized windows"}}')
            else:
                print('{"text":"󰘸","class":"empty","tooltip":"No minimized windows"}')
            return
        
        elif command in ["next", "prev", "activate", "close"]:
            # Commands for running instance
            if SingletonManager.is_running():
                SingletonManager.send_command(command)
                return
            else:
                # If asking to cycle but no instance running, start one
                if command in ["next", "prev"]:
                    command = "show"  # Start the UI
                else:
                    return  # Nothing to do
    
    # Default: show alt-tab interface or handle singleton
    if SingletonManager.is_running():
        # Send next command to existing instance
        SingletonManager.send_command("next")
        return
    
    # Acquire singleton lock
    if not SingletonManager.acquire_lock():
        print("Failed to acquire lock", file=sys.stderr)
        return
    
    # Set up cleanup
    def cleanup_handler(signum, frame):
        SingletonManager.release_lock()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, cleanup_handler)
    signal.signal(signal.SIGINT, cleanup_handler)
    
    # Ensure cache directory exists
    os.makedirs(CACHE_DIR, exist_ok=True)
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'w') as f:
            json.dump([], f)
    
    # Create FIFO for communication
    SingletonManager.create_fifo()
    
    # Create and show the window
    window = AltTabWindow()
    
    def on_destroy(widget):
        SingletonManager.release_lock()
        try:
            os.unlink(FIFO_FILE)
        except OSError:
            pass
        Gtk.main_quit()
    
    window.connect("destroy", on_destroy)
    window.show_all()
    
    # Grab keyboard focus
    window.grab_focus()
    window.present()
    
    try:
        Gtk.main()
    finally:
        SingletonManager.release_lock()
        try:
            os.unlink(FIFO_FILE)
        except OSError:
            pass

if __name__ == "__main__":
    main()
