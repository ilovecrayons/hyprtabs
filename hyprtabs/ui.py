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

class AltTabWindow(Gtk.Window):
    """Main Alt-Tab window interface"""
    
    def __init__(self):
        super().__init__()
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
        """Setup the UI"""
        self.set_title("HyprTabs")
        
        # Initialize layer shell
        GtkLayerShell.init_for_window(self)
        
        # Set layer shell properties
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "hyprtabs")
        
        # Set anchors to center the window
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, False)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, False)
        
        # Enable keyboard interaction
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.EXCLUSIVE)
        
        # Set margins to center the window
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.BOTTOM, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 0)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 0)
        
        # Remove regular window properties that don't apply to layer shell
        self.set_decorated(False)
        self.set_resizable(False)
        
        # Enable keyboard events
        self.set_can_focus(True)
        self.set_accept_focus(True)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK | Gdk.EventMask.KEY_RELEASE_MASK)
        
        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.main_box.set_margin_top(20)
        self.main_box.set_margin_bottom(20)
        self.main_box.set_margin_start(20)
        self.main_box.set_margin_end(20)
        self.add(self.main_box)
        
        # Title label
        self.title_label = Gtk.Label()
        self.title_label.set_markup("<b>Alt+Tab Window Switcher</b>")
        self.main_box.pack_start(self.title_label, False, False, 0)
        
        # Window list - optimize ListBox settings
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(False)  # Disable animations
        self.main_box.pack_start(self.list_box, True, True, 0)
        
        # Instructions
        self.instructions = Gtk.Label()
        self.instructions.set_markup(
            "<small>Hold Alt + Tab to cycle • Release Alt to switch • Esc to cancel</small>"
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
            transition: none;
        }
        
        .window-item:selected {
            background-color: rgba(100, 150, 255, 0.8);
            transition: none;
        }
        
        .window-item:hover {
            transition: none;
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
        """Load and display all windows"""
        self.windows = WindowManager.get_all_windows()
        
        # Clear existing items
        for child in self.list_box.get_children():
            self.list_box.remove(child)
        
        # Add window items in batch for better performance
        for i, window in enumerate(self.windows):
            row = self.create_window_row(window)
            self.list_box.add(row)
            
        # Select first item
        if self.windows:
            self.current_index = 0
            # Do initial selection setup immediately
            row = self.list_box.get_row_at_index(0)
            if row:
                self.list_box.select_row(row)
            
            # Set initial title
            current_window = self.windows[0]
            status = "Hidden" if current_window.is_minimized else f"WS {current_window.workspace}"
            self.title_label.set_markup(
                f"<b>1/{len(self.windows)}</b> - {current_window.class_name} ({status})"
            )
        
        # Check if Alt is currently pressed when window opens
        # This is important for Alt+Tab behavior - assume it's pressed for faster startup
        self.alt_pressed = True  # Assume Alt is pressed since we're likely opened with Alt+Tab
            
        self.show_all()
        
        # Set window size after showing (layer shell needs this)
        GLib.idle_add(self._set_window_size)
    
    def _set_window_size(self):
        """Set the window size for proper centering"""
        # Request a reasonable size for the window
        self.set_size_request(500, 400)
        
        # Center the window by setting it to not be anchored to any edge
        # This makes it float in the center
        return False  # Don't repeat
    
    def create_window_row(self, window) -> Gtk.ListBoxRow:
        """Create a row for a window"""
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("window-item")
        
        # Add color coding based on window state
        if window.is_minimized:
            row.get_style_context().add_class("window-hidden")
        else:
            row.get_style_context().add_class("window-active")
        
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        # Icon/Status
        status_label = Gtk.Label(label=window.icon)
        status_label.set_size_request(30, -1)
        box.pack_start(status_label, False, False, 0)
        
        # Window info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        title_label = Gtk.Label(label=f"{window.class_name}")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_markup(f"<b>{window.class_name}</b>")
        info_box.pack_start(title_label, False, False, 0)
        
        subtitle_label = Gtk.Label(label=window.title)
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
