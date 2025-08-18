#pragma once

#include <string>

class SingletonManager {
public:
    static bool acquireLock();
    static void releaseLock();
    static bool isRunning();
    
private:
    static int lock_fd_;
    static const std::string& getLockFile();
};
