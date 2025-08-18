# Hyprtabs - hyprctl Alt+Tab helper

An Alt-Tab window switcher for Hyprland that supports both minimizing and restoring windows. Rewrite of Mauitron/NiflVeil without eww UI dependencies.

## Features

- **Alt-Tab cycling**: Hold Alt and press Tab to cycle through all windows
- **Show all windows**: Displays both active and minimized/hidden windows

## Installation

1. Clone the repository and run the installation script:
   ```bash
   ./install.sh
   ```

2. Add keybinds to your Hyprland config (`~/.config/hypr/hyprland.conf`):
   ```bash
   # Replace with your actual path
   $hyprtabs = ~/hyprtabs/build/hyprtabs

   # Include performance optimizations
   source = ~/hyprtabs/hyprland-rules.conf
   
   # Main Alt+Tab functionality
   bind = ALT, Tab, exec, $hyprtabs
   
   # Alt+` to minimize current window
   bind = ALT, grave, exec, $hyprtabs minimize
   ```

## Usage

### Basic Alt-Tab
1. Press `Alt+Tab` to open the window switcher
2. While holding `Alt`, press `Tab` repeatedly to cycle through windows
3. **Release `Alt` to automatically activate the selected window**
4. Press `Esc` to cancel without switching
5. Press `Alt+~` to minimize the current window

### Command Line Interface
```bash
# Show alt-tab interface
./hyprtabs

# Minimize current window
./hyprtabs minimize
```

## Window Behavior

- **Active windows**: Shown with workspace number (e.g., "WS 2")
- **Hidden windows**: Shown with "(Hidden)" status
- **Action on selection**:
  - Hidden window → Restores to current workspace and focuses
  - Active window → Focuses the window



