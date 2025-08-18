#include "window.h"
#include "constants.h"
#include <algorithm>

std::unordered_map<std::string, std::string> Window::icon_cache_;

Window::Window(const std::string& address, const std::string& title, 
               const std::string& class_name, int workspace, bool is_minimized)
    : address_(address), title_(title), class_name_(class_name), 
      workspace_(workspace), is_minimized_(is_minimized) {
    
    icon_ = getIconCached();
    
    // Create short address (last 4 characters)
    if (address_.length() >= 4) {
        short_addr_ = address_.substr(address_.length() - 4);
    } else {
        short_addr_ = address_;
    }
}

std::string Window::getIconCached() {
    // Check cache first
    auto it = icon_cache_.find(class_name_);
    if (it != icon_cache_.end()) {
        return it->second;
    }
    
    // Find icon
    std::string class_lower = class_name_;
    std::transform(class_lower.begin(), class_lower.end(), class_lower.begin(), ::tolower);
    
    // Default fallback
    std::string icon = "󰖲";
    
    // Get icons map
    const auto& icons = Constants::getIcons();
    
    // Find matching icon
    auto default_it = icons.find("default");
    if (default_it != icons.end()) {
        icon = default_it->second;
    }
    
    for (const auto& [app_name, app_icon] : icons) {
        if (app_name != "default" && class_lower.find(app_name) != std::string::npos) {
            icon = app_icon;
            break;
        }
    }
    
    // Cache the result
    icon_cache_[class_name_] = icon;
    return icon;
}

std::string Window::getDisplayTitle() const {
    std::string status = is_minimized_ ? "Hidden" : "WS " + std::to_string(workspace_);
    return icon_ + " " + class_name_ + " - " + title_ + " [" + status + "]";
}
