#!/bin/bash
# HyprTabs Installation Script

set -e

echo "🚀 Installing HyprTabs..."

# Check if we're on a supported system
if ! command -v hyprctl &> /dev/null; then
    echo "❌ hyprctl not found - make sure Hyprland is installed and running"
    exit 1
fi

# Check if we're on Arch Linux
if ! command -v pacman &> /dev/null; then
    echo "⚠️  This installer is designed for Arch Linux"
    echo "   Please install dependencies manually for your distribution"
else
    echo "📦 Installing dependencies..."
    echo "   Installing: cmake gcc gtk3 gtk-layer-shell nlohmann-json"
    sudo pacman -S --needed cmake gcc gtk3 gtk-layer-shell nlohmann-json
fi

echo "⚙️ Building C++ version..."
if [ -f "build.sh" ]; then
    ./build.sh
else
    echo "❌ build.sh not found. Cannot build C++ version."
    exit 1
fi

# Check if hyprctl is available
if ! command -v hyprctl &> /dev/null; then
    echo "⚠️  hyprctl not found - make sure Hyprland is installed and running"
else
    echo "   Hyprland detected ✅"
fi

# Get the current directory
CURRENT_DIR="$(pwd)"

echo ""
echo "✅ Installation complete!"
echo ""
echo "📝 Next steps:"
echo "1. Add this to your ~/.config/hypr/hyprland.conf:"
echo ""
echo "   # HyprTabs Alt-Tab"
echo "   \$hyprtabs = $CURRENT_DIR/build/hyprtabs"
echo "   bind = ALT, Tab, exec, \$hyprtabs"
echo ""
echo "2. Reload Hyprland config:"
echo "   hyprctl reload"
echo ""
echo "3. Test with Alt+Tab!"
echo ""
echo "📖 See README.md for full documentation and customization options."
