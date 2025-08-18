#include "hyprland_manager.h"
#include "constants.h"
#include <nlohmann/json.hpp>
#include <cstdlib>
#include <memory>
#include <array>
#include <chrono>
#include <fstream>
#include <filesystem>

using json = nlohmann::json;

std::string HyprlandManager::window_cache_;
double HyprlandManager::cache_timestamp_ = 0.0;

std::optional<std::string> HyprlandManager::runHyprctl(const std::vector<std::string>& command) {
    std::string cmd = "hyprctl";
    for (const auto& arg : command) {
        cmd += " " + arg;
    }
    
    std::array<char, 128> buffer;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
    
    if (!pipe) {
        return std::nullopt;
    }
    
    while (fgets(buffer.data(), buffer.size(), pipe.get()) != nullptr) {
        result += buffer.data();
    }
    
    return result;
}

std::optional<std::string> HyprlandManager::getCachedWindows() {
    auto current_time = std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    
    if (!window_cache_.empty() && 
        current_time - cache_timestamp_ < cache_duration_) {
        return window_cache_;
    }
    return std::nullopt;
}

void HyprlandManager::cacheWindows(const std::string& windows_data) {
    window_cache_ = windows_data;
    cache_timestamp_ = std::chrono::duration<double>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}

std::vector<Window> HyprlandManager::getActiveWindows() {
    auto cached = getCachedWindows();
    std::string output;
    
    if (cached) {
        output = *cached;
    } else {
        auto result = runHyprctl({"clients", "-j"});
        if (!result) {
            return {};
        }
        output = *result;
        cacheWindows(output);
    }
    
    std::vector<Window> windows;
    
    try {
        json clients = json::parse(output);
        
        for (const auto& client : clients) {
            // Include all windows, including those in special workspaces
            bool is_in_special = false;
            std::string workspace_name = "";
            int workspace_id = 1;
            
            if (client.contains("workspace") && client["workspace"].contains("name")) {
                workspace_name = client["workspace"]["name"];
                workspace_id = client["workspace"].value("id", 1);
                is_in_special = (workspace_name.find("special:") == 0);
            }
            
            // For special:minimum, treat as minimized; for other special workspaces, treat as regular windows
            bool is_minimized = (workspace_name == "special:minimum");
            
            windows.emplace_back(
                client.value("address", ""),
                client.value("title", ""),
                client.value("class", ""),
                workspace_id,
                is_minimized,
                workspace_name
            );
        }
    } catch (const json::parse_error&) {
        return {};
    }
    
    return windows;
}

std::vector<Window> HyprlandManager::getMinimizedWindows() {
    if (!std::filesystem::exists(Constants::CACHE_FILE)) {
        return {};
    }
    
    std::vector<Window> windows;
    
    try {
        std::ifstream file(Constants::CACHE_FILE);
        json data;
        file >> data;
        
        for (const auto& item : data) {
            windows.emplace_back(
                item.value("address", ""),
                item.value("original_title", ""),
                item.value("class", ""),
                0, // Minimized windows don't have a workspace
                true,
                "special:minimum" // Minimized windows are in special:minimum
            );
        }
    } catch (const std::exception&) {
        return {};
    }
    
    return windows;
}

std::vector<Window> HyprlandManager::getAllWindows() {
    // getActiveWindows now includes all windows, including those in special workspaces
    // so we no longer need to merge with getMinimizedWindows to avoid duplication
    return getActiveWindows();
}

std::optional<Window> HyprlandManager::getActiveWindow() {
    auto result = runHyprctl({"activewindow", "-j"});
    if (!result) {
        return std::nullopt;
    }
    
    try {
        json active_data = json::parse(*result);
        
        std::string workspace_name = "";
        int workspace_id = 1;
        if (active_data.contains("workspace")) {
            workspace_id = active_data["workspace"].value("id", 1);
            workspace_name = active_data["workspace"].value("name", "");
        }
        
        return Window(
            active_data.value("address", ""),
            active_data.value("title", ""),
            active_data.value("class", ""),
            workspace_id,
            false,
            workspace_name
        );
    } catch (const json::parse_error&) {
        return std::nullopt;
    }
}

bool HyprlandManager::focusWindow(const Window& window) {
    if (window.isMinimized()) {
        return restoreWindow(window);
    } else {
        // Handle special workspaces
        if (window.isInSpecialWorkspace()) {
            // For special workspaces, use the workspace name directly
            auto result = runHyprctl({"dispatch", "togglespecialworkspace", window.getWorkspaceName().substr(8)}); // Remove "special:" prefix
            if (!result) {
                return false;
            }
        } else {
            // Switch to the window's workspace first if needed
            if (window.getWorkspace() > 0) {
                runHyprctl({"dispatch", "workspace", std::to_string(window.getWorkspace())});
            }
        }
        
        // Focus the window
        auto result = runHyprctl({"dispatch", "focuswindow", "address:" + window.getAddress()});
        
        // Bring to front to ensure it's actually focused
        runHyprctl({"dispatch", "bringactivetotop"});
        
        return result.has_value();
    }
}

bool HyprlandManager::minimizeWindow(const Window& window) {
    if (window.isMinimized()) {
        return true; // Already minimized
    }
    
    // Move to special workspace
    auto result = runHyprctl({
        "dispatch", "movetoworkspacesilent", 
        "special:minimum,address:" + window.getAddress()
    });
    
    if (result) {
        addToCache(window);
        return true;
    }
    return false;
}

bool HyprlandManager::restoreWindow(const Window& window) {
    if (!window.isMinimized()) {
        return true; // Already active
    }
    
    // Get current workspace
    auto workspace_info = runHyprctl({"activeworkspace", "-j"});
    if (!workspace_info) {
        return false;
    }
    
    int current_ws = 1;
    try {
        json workspace_data = json::parse(*workspace_info);
        current_ws = workspace_data.value("id", 1);
    } catch (const json::parse_error&) {
        current_ws = 1;
    }
    
    // Move from special workspace to current workspace
    auto result = runHyprctl({
        "dispatch", "movetoworkspace",
        std::to_string(current_ws) + ",address:" + window.getAddress()
    });
    
    if (result) {
        // Ensure the current workspace is active
        runHyprctl({"dispatch", "workspace", std::to_string(current_ws)});
        
        // Focus the window after restoring
        runHyprctl({"dispatch", "focuswindow", "address:" + window.getAddress()});
        
        // Bring to front to ensure visibility
        runHyprctl({"dispatch", "bringactivetotop"});
        
        removeFromCache(window);
        return true;
    }
    return false;
}

void HyprlandManager::addToCache(const Window& window) {
    std::filesystem::create_directories(Constants::CACHE_DIR);
    
    json cached_windows = json::array();
    if (std::filesystem::exists(Constants::CACHE_FILE)) {
        try {
            std::ifstream file(Constants::CACHE_FILE);
            file >> cached_windows;
        } catch (const std::exception&) {
            cached_windows = json::array();
        }
    }
    
    json window_data = {
        {"address", window.getAddress()},
        {"display_title", window.getDisplayTitle()},
        {"class", window.getClassName()},
        {"original_title", window.getTitle()},
        {"preview", ""},
        {"icon", window.getIcon()}
    };
    
    // Check if already exists
    bool found = false;
    for (auto& cached : cached_windows) {
        if (cached.value("address", "") == window.getAddress()) {
            cached = window_data;
            found = true;
            break;
        }
    }
    
    if (!found) {
        cached_windows.push_back(window_data);
    }
    
    std::ofstream file(Constants::CACHE_FILE);
    file << cached_windows.dump(4);
}

void HyprlandManager::removeFromCache(const Window& window) {
    if (!std::filesystem::exists(Constants::CACHE_FILE)) {
        return;
    }
    
    try {
        std::ifstream file(Constants::CACHE_FILE);
        json cached_windows;
        file >> cached_windows;
        file.close();
        
        // Remove the window
        cached_windows.erase(
            std::remove_if(cached_windows.begin(), cached_windows.end(),
                [&window](const json& w) {
                    return w.value("address", "") == window.getAddress();
                }),
            cached_windows.end()
        );
        
        std::ofstream outfile(Constants::CACHE_FILE);
        outfile << cached_windows.dump(4);
    } catch (const std::exception&) {
        // Ignore errors
    }
}
