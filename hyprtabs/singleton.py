"""
Singleton manager for HyprTabs.
"""
import os
from .constants import LOCK_FILE, FIFO_FILE

class SingletonManager:
    """Manages singleton instance and inter-process communication"""
    
    @staticmethod
    def is_running() -> bool:
        """Check if another instance is running"""
        return os.path.exists(LOCK_FILE)
    
    @staticmethod
    def acquire_lock() -> bool:
        """Acquire singleton lock"""
        try:
            lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode())
            os.close(lock_fd)
            return True
        except OSError:
            return False
    
    @staticmethod
    def release_lock():
        """Release singleton lock"""
        try:
            os.unlink(LOCK_FILE)
        except OSError:
            pass
    
    @staticmethod
    def send_command(command: str) -> bool:
        """Send command to running instance"""
        if not os.path.exists(FIFO_FILE):
            return False
        
        try:
            with open(FIFO_FILE, 'w') as fifo:
                fifo.write(command + '\n')
                fifo.flush()
            return True
        except (OSError, IOError):
            return False
    
    @staticmethod
    def create_fifo():
        """Create FIFO for communication"""
        try:
            if os.path.exists(FIFO_FILE):
                os.unlink(FIFO_FILE)
            os.mkfifo(FIFO_FILE)
        except OSError:
            pass
