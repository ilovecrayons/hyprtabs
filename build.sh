#!/bin/bash

# Build script for HyprTabs C++ version

set -e  # Exit on error

echo "Building HyprTabs C++ version..."

# Check for required dependencies
echo "Checking dependencies..."

# Check for CMake
if ! command -v cmake &> /dev/null; then
    echo "Error: CMake is required but not installed"
    exit 1
fi

# Check for pkg-config
if ! command -v pkg-config &> /dev/null; then
    echo "Error: pkg-config is required but not installed"
    exit 1
fi

# Check for GTK3
if ! pkg-config --exists gtk+-3.0; then
    echo "Error: GTK3 development files are required"
    echo "Install with: sudo pacman -S gtk3 (Arch) or sudo apt install libgtk-3-dev (Ubuntu)"
    exit 1
fi

# Check for GTK Layer Shell
if ! pkg-config --exists gtk-layer-shell-0; then
    echo "Error: GTK Layer Shell development files are required"
    echo "Install with: sudo pacman -S gtk-layer-shell (Arch) or build from source"
    exit 1
fi

# Check for nlohmann/json
if ! pkg-config --exists nlohmann_json; then
    echo "Warning: nlohmann_json not found via pkg-config, trying to find header-only version..."
    if ! find /usr/include -name "nlohmann" -type d 2>/dev/null | grep -q nlohmann; then
        echo "Error: nlohmann/json is required"
        echo "Install with: sudo pacman -S nlohmann-json (Arch) or sudo apt install nlohmann-json3-dev (Ubuntu)"
        exit 1
    fi
fi

# Create build directory
echo "Creating build directory..."
mkdir -p build
cd build

# Configure with CMake
echo "Configuring with CMake..."
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build the project
echo "Building..."
make -j$(nproc)

echo "Build completed successfully!"
echo "Executable: $(pwd)/hyprtabs"

# Optionally install
read -p "Do you want to install to /usr/local/bin? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Installing..."
    sudo make install
    echo "Installation completed!"
else
    echo "To install manually, run: sudo make install"
fi

echo ""
echo "You can now run: ./hyprtabs"
echo "Or if installed: hyprtabs"
