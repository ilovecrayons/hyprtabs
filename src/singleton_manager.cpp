#include "singleton_manager.h"
#include "constants.h"
#include <fcntl.h>
#include <unistd.h>
#include <sys/file.h>

int SingletonManager::lock_fd_ = -1;

const std::string& SingletonManager::getLockFile() {
    static const std::string lock_file = Constants::LOCK_FILE;
    return lock_file;
}

bool SingletonManager::acquireLock() {
    const auto& lock_file = getLockFile();
    lock_fd_ = open(lock_file.c_str(), O_CREAT | O_WRONLY, 0644);
    if (lock_fd_ == -1) {
        return false;
    }
    
    if (flock(lock_fd_, LOCK_EX | LOCK_NB) == -1) {
        close(lock_fd_);
        lock_fd_ = -1;
        return false;
    }
    
    return true;
}

void SingletonManager::releaseLock() {
    if (lock_fd_ != -1) {
        flock(lock_fd_, LOCK_UN);
        close(lock_fd_);
        lock_fd_ = -1;
        unlink(getLockFile().c_str());
    }
}

bool SingletonManager::isRunning() {
    const auto& lock_file = getLockFile();
    int fd = open(lock_file.c_str(), O_RDONLY);
    if (fd == -1) {
        return false;
    }
    
    bool locked = (flock(fd, LOCK_EX | LOCK_NB) == -1);
    close(fd);
    return locked;
}
