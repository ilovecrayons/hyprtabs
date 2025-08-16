#!/usr/bin/env python3
"""
HyprTabs - Advanced Alt-Tab window switcher with minimize/restore for Hyprland
"""

import json
import sys
import os
import signal
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from hyprtabs.constants import CACHE_DIR, CACHE_FILE, FIFO_FILE
from hyprtabs.hyprland import WindowManager
from hyprtabs.singleton import SingletonManager
from hyprtabs.ui import AltTabWindow

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
