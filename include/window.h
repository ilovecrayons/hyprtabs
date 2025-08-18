#pragma once

#include <string>
#include <unordered_map>

class Window {
public:
    Window(const std::string& address, const std::string& title, 
           const std::string& class_name, int workspace, bool is_minimized = false);
    
    // Getters
    const std::string& getAddress() const { return address_; }
    const std::string& getTitle() const { return title_; }
    const std::string& getClassName() const { return class_name_; }
    int getWorkspace() const { return workspace_; }
    bool isMinimized() const { return is_minimized_; }
    const std::string& getIcon() const { return icon_; }
    const std::string& getShortAddr() const { return short_addr_; }
    
    std::string getDisplayTitle() const;
    
private:
    std::string address_;
    std::string title_;
    std::string class_name_;
    int workspace_;
    bool is_minimized_;
    std::string icon_;
    std::string short_addr_;
    
    // Cache for icons to avoid repeated lookups
    static std::unordered_map<std::string, std::string> icon_cache_;
    
    std::string getIconCached();
};
