#!/bin/bash
# HyprTabs Installation Script - Supports both Python and C++ versions

set -e

echo "🚀 Installing HyprTabs..."

# Ask user which version they want
echo ""
echo "Which version do you want to install?"
echo "1) Python version (existing, slower but simpler)"
echo "2) C++ version (new, faster compiled performance)"
echo "3) Both versions"
read -p "Enter your choice (1/2/3): " -n 1 -r
echo ""

INSTALL_PYTHON=false
INSTALL_CPP=false

case $REPLY in
    1) INSTALL_PYTHON=true ;;
    2) INSTALL_CPP=true ;;
    3) INSTALL_PYTHON=true; INSTALL_CPP=true ;;
    *) echo "Invalid choice. Exiting."; exit 1 ;;
esac

# Check if we're on Arch Linux
if ! command -v pacman &> /dev/null; then
    echo "⚠️  This installer is designed for Arch Linux"
    echo "   Please install dependencies manually for your distribution"
else
    echo "📦 Installing dependencies..."
    
    DEPS=""
    if [ "$INSTALL_PYTHON" = true ]; then
        DEPS="$DEPS python-gobject gtk3"
    fi
    
    if [ "$INSTALL_CPP" = true ]; then
        DEPS="$DEPS cmake gcc gtk3 gtk-layer-shell nlohmann-json"
    fi
    
    if [ -n "$DEPS" ]; then
        echo "   Installing: $DEPS"
        sudo pacman -S --needed $DEPS
    else
        echo "   No dependencies to install"
    fi
fi

if [ "$INSTALL_PYTHON" = true ]; then
    echo "� Setting up Python version..."
    # Make scripts executable
    chmod +x hyprtabs-runner hyprtabs.py
    
    # Test Python script compilation
    echo "🧪 Testing Python script..."
    if python3 -m py_compile hyprtabs.py; then
        echo "   Python script compiles successfully ✅"
    else
        echo "   ❌ Python script has syntax errors"
        exit 1
    fi
fi

if [ "$INSTALL_CPP" = true ]; then
    echo "⚙️ Building C++ version..."
    if [ -f "build.sh" ]; then
        ./build.sh
    else
        echo "❌ build.sh not found. Cannot build C++ version."
        exit 1
    fi
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

if [ "$INSTALL_PYTHON" = true ] && [ "$INSTALL_CPP" = true ]; then
    echo "   # HyprTabs Alt-Tab (Python version)"
    echo "   \$hyprtabs_py = $CURRENT_DIR/hyprtabs-runner"
    echo "   bind = ALT, Tab, exec, \$hyprtabs_py"
    echo ""
    echo "   # HyprTabs Alt-Tab (C++ version - faster)"
    echo "   \$hyprtabs_cpp = $CURRENT_DIR/build/hyprtabs"
    echo "   bind = ALT, Tab, exec, \$hyprtabs_cpp"
    echo ""
    echo "   Choose one of the above bindings (C++ version recommended for better performance)"
elif [ "$INSTALL_CPP" = true ]; then
    echo "   # HyprTabs Alt-Tab (C++ version)"
    echo "   \$hyprtabs = $CURRENT_DIR/build/hyprtabs"
    echo "   bind = ALT, Tab, exec, \$hyprtabs"
else
    echo "   # HyprTabs Alt-Tab (Python version)"
    echo "   \$hyprtabs = $CURRENT_DIR/hyprtabs-runner"
    echo "   bind = ALT, Tab, exec, \$hyprtabs"
fi

echo ""
echo "2. Reload Hyprland config:"
echo "   hyprctl reload"
echo ""
echo "3. Test with Alt+Tab!"
echo ""
if [ "$INSTALL_CPP" = true ]; then
    echo "🚀 C++ version provides significantly better performance than Python version!"
    echo ""
fi
echo "📖 See README.md for full documentation and customization options."
