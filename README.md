# HyprTabs - Advanced Alt-Tab Window Switcher for Hyprland

A modern Alt-Tab window switcher for Hyprland that supports both minimizing and restoring windows. Rewrite of Mauitron/NiflVeil without eww UI dependencies.

## Features

- **Alt-Tab cycling**: Hold Alt and press Tab to cycle through all windows
- **Show all windows**: Displays both active and minimized/hidden windows

## Installation

1. Clone the repository and run the installation script:
   ```bash
   ./install.sh
   ```

2. Make the scripts executable:
   ```bash
   chmod +x hyprtabs hyprtabs.py
   ```

3. Add keybinds to your Hyprland config (`~/.config/hypr/hyprland.conf`):
   ```bash
   # Replace with your actual path
   $hyprtabs = ~/hyprtabs
   
   # Main Alt+Tab functionality
   bind = ALT, Tab, exec, $hyprtabs
   
   # Optional: Alt+` to minimize current window
   bind = ALT, grave, exec, $hyprtabs minimize
   ```

## Usage

### Basic Alt-Tab
1. Press `Alt+Tab` to open the window switcher
2. While holding `Alt`, press `Tab` repeatedly to cycle through windows
3. **Release `Alt` to automatically activate the selected window**
4. Press `Esc` to cancel without switching

### Keyboard Controls
- `Tab` / `↓` / `j`: Next window 
- **Release Alt**: Auto-activate selected window (Windows-style behavior)
- `Enter` / `Space`: Manual activate selected window
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

## Customization

You can modify the Python script to change:
- Window icons (edit the `ICONS` dictionary)
- UI styling (edit the CSS in `apply_css()`)
- Behavior (modify what happens when selecting active vs hidden windows)
- Keyboard shortcuts


