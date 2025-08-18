#pragma once

#include "window.h"
#include <vector>
#include <string>
#include <memory>
#include <optional>

class HyprlandManager {
public:
    static std::vector<Window> getActiveWindows();
    static std::vector<Window> getMinimizedWindows();
    static std::vector<Window> getAllWindows();
    static std::optional<Window> getActiveWindow();
    
    static bool focusWindow(const Window& window);
    static bool minimizeWindow(const Window& window);
    static bool restoreWindow(const Window& window);
    
private:
    static std::optional<std::string> runHyprctl(const std::vector<std::string>& command);
    static void addToCache(const Window& window);
    static void removeFromCache(const Window& window);
    
    // Cache for window data
    static std::string window_cache_;
    static double cache_timestamp_;
    static constexpr double cache_duration_ = 0.1; // 100ms cache
    
    static std::optional<std::string> getCachedWindows();
    static void cacheWindows(const std::string& windows_data);
};
