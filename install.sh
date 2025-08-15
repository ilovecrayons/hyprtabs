#!/bin/bash
# HyprTabs Installation Script

set -e

echo "🚀 Installing HyprTabs..."

# Check if we're on Arch Linux
if ! command -v pacman &> /dev/null; then
    echo "⚠️  This installer is designed for Arch Linux"
    echo "   Please install python-gobject and gtk3 manually for your distribution"
else
    echo "📦 Installing dependencies..."
    if ! pacman -Qi python-gobject &> /dev/null || ! pacman -Qi gtk3 &> /dev/null; then
        echo "   Installing python-gobject and gtk3..."
        sudo pacman -S --needed python-gobject gtk3
    else
        echo "   Dependencies already installed ✅"
    fi
fi

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x hyprtabs hyprtabs.py

# Test Python script compilation
echo "🧪 Testing Python script..."
if python3 -m py_compile hyprtabs.py; then
    echo "   Python script compiles successfully ✅"
else
    echo "   ❌ Python script has syntax errors"
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
echo "   \$hyprtabs = $CURRENT_DIR/hyprtabs"
echo "   bind = ALT, Tab, exec, \$hyprtabs"
echo "   bind = ALT, grave, exec, \$hyprtabs minimize"
echo ""
echo "2. Reload Hyprland config:"
echo "   hyprctl reload"
echo ""
echo "3. Test with Alt+Tab!"
echo ""
echo "📖 See README.md for full documentation and customization options."
