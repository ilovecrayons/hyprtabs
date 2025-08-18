#pragma once

#include <string>
#include <unordered_map>

class Constants {
public:
    // Directories and Files
    static const std::string CACHE_DIR;
    static const std::string CACHE_FILE;
    static const std::string PREVIEW_DIR;
    static const std::string LOCK_FILE;
    static const std::string FIFO_FILE;
    
    // Icon mapping - use function to avoid static initialization order issues
    static const std::unordered_map<std::string, std::string>& getIcons();
    
private:
    Constants() = default;
};
