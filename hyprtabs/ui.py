"""
UI for HyprTabs.
"""
import threading
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell

from .constants import FIFO_FILE
from .hyprland import WindowManager
from .singleton import SingletonManager

import os
import sys
import logging

class AltTabWindow(Gtk.Window):
    """Main Alt-Tab window interface"""
    
    def __init__(self):
        super().__init__()
        # Set up logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            stream=sys.stdout
        )
        self.logger = logging.getLogger("HyprTabs")
        
        self.windows = []
        self.current_index = 0
        self.fifo_thread = None
        self.running = True
        self.alt_pressed = False  # Track Alt key state
        self.setup_ui()
        self.setup_keybindings()
        self.load_windows()
        self.start_fifo_listener()
        
    def setup_ui(self):
        """Setup the UI optimized for speed"""
        self.set_title("HyprTabs")
        
        # Initialize layer shell
        GtkLayerShell.init_for_window(self)
        
        # Set layer shell properties for instant display
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "hyprtabs")
        
        # Set anchors to center the window
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
        
        # Enable exclusive keyboard interaction for instant focus
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        
        # Set margins to center the window
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 0)
        
        # Remove regular window properties that don't apply to layer shell
        self.set_decorated(False)
        self.set_resizable(False)
        
        # Optimize for speed - disable double buffering and enable hardware acceleration
        self.set_can_focus(True)
        self.set_accept_focus(True)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.KEY_RELEASE_MASK)
        
        # Set fixed size immediately to avoid resizing
        self.set_size_request(500, 400)
        
        # Main container with minimal spacing
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(15)
        self.main_box.set_margin_bottom(15)
        self.main_box.set_margin_start(15)
        self.main_box.set_margin_end(15)
        self.add(self.main_box)
        
        # Title label
        self.title_label = Gtk.Label()
        self.title_label.set_markup("<b>Alt+Tab Window Switcher</b>")
        self.main_box.pack_start(self.title_label, False, False, 0)
        
        # Window list - optimize for performance
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(False)
        # Disable homogeneous sizing for faster rendering
        self.list_box.set_can_focus(False)  # Prevent focus stealing
        self.main_box.pack_start(self.list_box, True, True, 0)
        
        # Instructions
        self.instructions = Gtk.Label()
        self.instructions.set_markup(
            "<small>Hold Alt + Tab to cycle • Release Alt to switch • Esc to cancel</small>"
        )
        self.main_box.pack_start(self.instructions, False, False, 0)
        
        # Apply CSS immediately
        self.apply_css()
        
    def apply_css(self):
        """Apply custom CSS styling optimized for speed"""
        css = """
        window {
            background-color: rgba(0, 0, 0, 0.9);
            border-radius: 10px;
            border: 2px solid #555;
        }
        
        * {
            transition: none;
            animation: none;
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
        
        .window-active {
            background-color: rgba(0, 100, 150, 0.3);
            border-left: 4px solid #00ff66;
        }
        
        .window-active:selected {
            background-color: rgba(0, 100, 255, 0.8);
        }
        
        .window-hidden {
            background-color: rgba(100, 0, 0, 0.3);
            border-left: 4px solid #ff3333;
        }
        
        .window-hidden:selected {
            background-color: rgba(200, 0, 0, 0.8);
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
        self.connect("key-release-event", self.on_key_release)
    
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
        """Load and display all windows with optimizations"""
        self.windows = WindowManager.get_all_windows()
        
        # Clear existing items efficiently
        self.list_box.foreach(lambda child: self.list_box.remove(child))
        
        # Pre-create all rows in batch for better performance
        rows = []
        for window in self.windows:
            row = self.create_window_row(window)
            rows.append(row)
        
        # Add all rows at once
        for row in rows:
            self.list_box.add(row)
            
        # Select first item immediately
        if self.windows:
            self.current_index = 0
            row = self.list_box.get_row_at_index(0)
            if row:
                self.list_box.select_row(row)
            
            # Set initial title immediately
            current_window = self.windows[0]
            status = "Hidden" if current_window.is_minimized else f"WS {current_window.workspace}"
            self.title_label.set_markup(
                f"<b>1/{len(self.windows)}</b> - {current_window.class_name} ({status})"
            )
        
        # Assume Alt is pressed for faster startup
        self.alt_pressed = True
            
        # Show everything at once
        self.show_all()
    
    def create_window_row(self, window) -> Gtk.ListBoxRow:
        """Create a row for a window - optimized for speed"""
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("window-item")
        
        # Add state class immediately
        state_class = "window-hidden" if window.is_minimized else "window-active"
        row.get_style_context().add_class(state_class)
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Icon - use fixed size for consistency
        status_label = Gtk.Label(label=window.icon)
        status_label.set_size_request(30, -1)
        box.pack_start(status_label, False, False, 0)
        
        # Window info - single vertical box
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        # Title with immediate markup
        title_label = Gtk.Label()
        title_label.set_halign(Gtk.Align.START)
        title_label.set_markup(f"<b>{window.class_name}</b>")
        info_box.pack_start(title_label, False, False, 0)
        
        # Subtitle - optimized text setting
        subtitle_label = Gtk.Label()
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
        
        # Select the row immediately without animations
        row = self.list_box.get_row_at_index(self.current_index)
        if row:
            self.list_box.select_row(row)
            # Ensure row is visible
            row.grab_focus()
            
        # Update title with current window info (simplified)
        if self.current_index < len(self.windows):
            current_window = self.windows[self.current_index]
            status = "Hidden" if current_window.is_minimized else f"WS {current_window.workspace}"
            self.title_label.set_markup(
                f"<b>{self.current_index + 1}/{len(self.windows)}</b> - {current_window.class_name} ({status})"
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
        """Activate the currently selected window and ensure it gets focus"""
        if not self.windows or self.current_index >= len(self.windows):
            self.logger.warning("No windows to activate")
            return
            
        window = self.windows[self.current_index]
        
        self.hide()
        
        # Process any pending GTK events
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        
        # Focus the window and log the result
        WindowManager.focus_window(window)
        
        # Allow the window manager time to process the focus change
        # before terminating our application
        GLib.timeout_add(100, self.close_window)
        return False

    def close_window(self):
        """Close the alt-tab window"""
        self.logger.debug("Closing window")
        self.running = False
        
        # Process any remaining events before quitting
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
            
        SingletonManager.release_lock()
        self.destroy()
        self.logger.debug("Quitting GTK main loop")
        Gtk.main_quit()
        return False

    def on_key_press(self, widget, event):
        """Handle key press events"""
        keyval = event.keyval
        state = event.state
        
        # Track Alt key state - check both individual Alt keys and modifier state
        if keyval in (Gdk.KEY_Alt_L, Gdk.KEY_Alt_R) or (state & Gdk.ModifierType.MOD1_MASK):
            self.alt_pressed = True
        
        # Check for Alt+Tab or Tab while Alt is held
        if keyval == Gdk.KEY_Tab:
            if state & Gdk.ModifierType.SHIFT_MASK:
                self.cycle_prev()
            else:
                self.cycle_next()
            return True
        
        # Enter or Space to activate (manual activation)
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
    
    def on_key_release(self, widget, event):
        """Handle key release events"""
        keyval = event.keyval
        state = event.state
        
        # Check for Alt key release - both individual keys and when modifier is no longer pressed
        if keyval in (Gdk.KEY_Alt_L, Gdk.KEY_Alt_R):
            self.alt_pressed = False
            # Auto-activate current window when Alt is released
            self.activate_current_window()
            return True
        
        # Also check if Alt modifier is no longer active (fallback)
        elif self.alt_pressed and not (state & Gdk.ModifierType.MOD1_MASK):
            self.alt_pressed = False
            self.activate_current_window()
            return True
        
        return False
