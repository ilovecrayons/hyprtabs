#include "ui_manager.h"
#include "singleton_manager.h"
#include "hyprland_manager.h"
#include "constants.h"
#include <iostream>
#include <filesystem>
#include <cstdlib>
#include <sys/stat.h>
#include <unistd.h>
#include <gtk/gtk.h>
#include <signal.h>

// Global cleanup function for signal handlers
void cleanup() {
    SingletonManager::releaseLock();
    if (std::filesystem::exists(Constants::FIFO_FILE)) {
        std::filesystem::remove(Constants::FIFO_FILE);
    }
}

// Signal handler for graceful shutdown
void signalHandler(int sig) {
    std::cout << "Received signal " << sig << ", cleaning up..." << std::endl;
    cleanup();
    exit(0);
}

void createFifo() {
    // Remove existing FIFO if it exists
    if (std::filesystem::exists(Constants::FIFO_FILE)) {
        std::filesystem::remove(Constants::FIFO_FILE);
    }
    
    // Create new FIFO
    if (mkfifo(Constants::FIFO_FILE.c_str(), 0666) != 0) {
        std::cerr << "Warning: Could not create FIFO file" << std::endl;
    }
}

void showHelp() {
    std::cout << "HyprTabs - Alt-Tab window switcher for Hyprland\n\n";
    std::cout << "Usage:\n";
    std::cout << "  hyprtabs           - Show window switcher\n";
    std::cout << "  hyprtabs --help    - Show this help\n";
    std::cout << "  hyprtabs --version - Show version\n\n";
    std::cout << "Controls:\n";
    std::cout << "  Alt+Tab / Tab      - Next window\n";
    std::cout << "  Shift+Tab          - Previous window\n";
    std::cout << "  Arrow keys / j,k   - Navigate\n";
    std::cout << "  Enter / Space      - Activate window\n";
    std::cout << "  Escape             - Cancel\n";
    std::cout << "  Mouse click        - Select and activate window\n";
}

void showVersion() {
    std::cout << "HyprTabs 1.0.0 (C++ version)\n";
    std::cout << "Built with GTK3 and gtk-layer-shell\n";
}

int main(int argc, char* argv[]) {
    // Set up signal handlers for graceful shutdown
    signal(SIGTERM, signalHandler);
    signal(SIGINT, signalHandler);
    signal(SIGHUP, signalHandler);
    
    // Handle command line arguments first (before any GTK calls)
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--help" || arg == "-h") {
            showHelp();
            return 0;
        } else if (arg == "--version" || arg == "-v") {
            showVersion();
            return 0;
        }
    }
    
    // Initialize GTK early to avoid issues
    if (!gtk_init_check(&argc, &argv)) {
        std::cerr << "Failed to initialize GTK. Make sure you're running in a graphical environment." << std::endl;
        return 1;
    }
    
    // Check if another instance is running
    if (SingletonManager::isRunning()) {
        std::cerr << "Another instance of HyprTabs is already running." << std::endl;
        return 1;
    }
    
    // Acquire singleton lock
    if (!SingletonManager::acquireLock()) {
        std::cerr << "Failed to acquire singleton lock." << std::endl;
        return 1;
    }
    
    // Set up cleanup on exit
    std::atexit(cleanup);
    
    try {
        // Create FIFO for communication
        createFifo();
        
        // Check if we have any windows to show
        auto windows = HyprlandManager::getAllWindows();
        if (windows.empty()) {
            std::cout << "No windows found." << std::endl;
            cleanup();
            return 0;
        }
        
        // Create and run UI
        UIManager ui;
        ui.run();
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        cleanup();
        return 1;
    }
    
    cleanup();
    return 0;
}
