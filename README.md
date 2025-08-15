# HyprTabs - Advanced Alt-Tab Window Switcher for Hyprland

A modern Alt-Tab window switcher for Hyprland that supports both minimizing and restoring windows, with a clean GTK interface.

## Features

- **Alt-Tab cycling**: Hold Alt and press Tab to cycle through all windows
- **Show all windows**: Displays both active and minimized/hidden windows
- **Smart actions**: 
  - Selecting a hidden window restores it
  - Selecting an active window focuses it
- **Keyboard navigation**: Full keyboard control with arrow keys, vim-style keys
- **Visual indicators**: Clear status showing workspace numbers and hidden state
- **Singleton behavior**: Proper handling of rapid key presses
- **Waybar integration**: Status display for minimized windows count

## Installation

1. Ensure you have the required dependencies:
   ```bash
   # On Arch Linux
   sudo pacman -S python-gobject gtk3
   ```

2. Make the scripts executable:
   ```bash
   chmod +x hyprtabs hyprtabs.py
   ```

3. Add keybinds to your Hyprland config (`~/.config/hypr/hyprland.conf`):
   ```bash
   # Replace with your actual path
   $hyprtabs = /home/huang/hyprtabs/hyprtabs
   
   # Main Alt+Tab functionality
   bind = ALT, Tab, exec, $hyprtabs
   
   # Optional: Alt+` to minimize current window
   bind = ALT, grave, exec, $hyprtabs minimize
   ```

## Usage

### Basic Alt-Tab
1. Press `Alt+Tab` to open the window switcher
2. While holding `Alt`, press `Tab` repeatedly to cycle through windows
3. Release `Alt` to activate the selected window
4. Press `Esc` to cancel without switching

### Keyboard Controls
- `Tab` / `↓` / `j`: Next window
- `Shift+Tab` / `↑` / `k`: Previous window  
- `Enter` / `Space`: Activate selected window
- `Esc`: Cancel and close

### Command Line Interface
```bash
# Show alt-tab interface
./hyprtabs

# Minimize current window
./hyprtabs minimize

# Restore specific window by ID
./hyprtabs restore 0x12345678

# Restore all minimized windows
./hyprtabs restore-all

# Show status (for waybar integration)
./hyprtabs show
```

## Window Behavior

- **Active windows**: Shown with workspace number (e.g., "WS 2")
- **Hidden windows**: Shown with "(Hidden)" status
- **Action on selection**:
  - Hidden window → Restores to current workspace and focuses
  - Active window → Focuses the window

## Waybar Integration

Add this to your waybar configuration:

```json
"custom/hyprtabs": {
    "exec": "/home/huang/hyprtabs/hyprtabs show",
    "interval": 2,
    "format": "{}",
    "return-type": "json",
    "tooltip": true
}
```

## Customization

You can modify the Python script to change:
- Window icons (edit the `ICONS` dictionary)
- UI styling (edit the CSS in `apply_css()`)
- Behavior (modify what happens when selecting active vs hidden windows)
- Keyboard shortcuts

## Troubleshooting

### Alt-Tab doesn't work
- Check that the keybind is properly set in hyprland.conf
- Ensure the script path is correct and executable
- Test manually: `./hyprtabs`

### GTK/UI issues
- Make sure you have `python-gobject` and `gtk3` installed
- Test with: `python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk"`

### Windows not showing
- Check if niflveil's cache directory exists: `/tmp/minimize-state/`
- Verify Hyprland is running and `hyprctl` works
- Test window detection: `hyprctl clients -j`

## Differences from Original niflveil

This replacement provides:
- ✅ Proper Alt-Tab cycling behavior
- ✅ Shows ALL windows, not just minimized ones
- ✅ Clean GTK interface instead of broken eww UI
- ✅ Singleton behavior for rapid key presses
- ✅ Better keyboard navigation
- ✅ Maintains compatibility with existing cache format

## License

This project builds upon the niflveil concept and maintains compatibility with its cache format while providing a completely rewritten interface.
