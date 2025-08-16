#!/usr/bin/env python3
"""
Test script to verify mouse click functionality in hyprtabs
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from hyprtabs.ui import AltTabWindow
from hyprtabs.hyprland import WindowManager

def test_mouse_click_functionality():
    """Test that mouse clicks are properly handled"""
    
    # Create the window
    window = AltTabWindow()
    
    # Get some windows to test with
    windows = WindowManager.get_all_windows()
    
    if not windows:
        print("No windows found to test with. Please open some applications first.")
        return False
    
    print(f"Found {len(windows)} windows:")
    for i, w in enumerate(windows):
        print(f"  {i}: {w.class_name} - {w.title}")
    
    # Check if the list box has the proper event handlers connected
    listbox = window.list_box
    
    # Check if the activation is enabled
    activation_enabled = listbox.get_activate_on_single_click()
    print(f"\nSingle click activation enabled: {activation_enabled}")
    
    # Check if event handlers are connected (we can't directly check this easily)
    # But we can verify the methods exist
    has_row_activated = hasattr(window, 'on_row_activated') and callable(getattr(window, 'on_row_activated'))
    has_row_selected = hasattr(window, 'on_row_selected') and callable(getattr(window, 'on_row_selected'))
    
    print(f"Row activated handler exists: {has_row_activated}")
    print(f"Row selected handler exists: {has_row_selected}")
    
    # Check that rows exist in the listbox
    num_rows = 0
    for i in range(len(windows)):
        row = listbox.get_row_at_index(i)
        if row:
            num_rows += 1
    
    print(f"Number of rows in listbox: {num_rows}")
    print(f"Number of windows: {len(windows)}")
    
    success = (activation_enabled and has_row_activated and has_row_selected and num_rows == len(windows))
    
    print(f"\nMouse click functionality test: {'PASSED' if success else 'FAILED'}")
    
    # Cleanup
    window.running = False
    window.destroy()
    
    return success

if __name__ == "__main__":
    test_mouse_click_functionality()
    Gtk.main_quit()
