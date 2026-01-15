"""
Log Streaming Service
Captures and broadcasts application logs in real-time via WebSocket
"""
import logging
import queue
from typing import List, Dict
from datetime import datetime


class LogHandler(logging.Handler):
    """Custom logging handler that captures logs for WebSocket streaming"""
    
    def __init__(self):
        super().__init__()
        self.log_queue: queue.Queue = queue.Queue(maxsize=1000)  # Limit to 1000 logs
        self.recent_logs: List[Dict] = []
        self.max_recent = 200  # Keep last 200 logs in memory
        
    def emit(self, record: logging.LogRecord):
        """Called when a log is emitted"""
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': self.format(record)
            }
            
            # Add to recent logs (FIFO)
            self.recent_logs.append(log_entry)
            if len(self.recent_logs) > self.max_recent:
                self.recent_logs.pop(0)
            
            # Add to queue for WebSocket broadcast (non-blocking)
            try:
                self.log_queue.put_nowait(log_entry)
            except queue.Full:
                # Queue is full, remove oldest and add new
                try:
                    self.log_queue.get_nowait()
                    self.log_queue.put_nowait(log_entry)
                except:
                    pass
                    
        except Exception:
            self.handleError(record)
    
    def get_recent_logs(self, count: int = 100) -> List[Dict]:
        """Get recent logs"""
        return self.recent_logs[-count:]
    
    def get_new_logs(self, timeout: float = 0.1) -> List[Dict]:
        """Get new logs from queue (non-blocking)"""
        logs = []
        try:
            while True:
                log = self.log_queue.get(timeout=timeout)
                logs.append(log)
                if len(logs) >= 10:  # Batch up to 10 logs
                    break
        except queue.Empty:
            pass
        return logs


# Global log handler instance
log_handler = LogHandler()
log_handler.setLevel(logging.DEBUG)
log_handler.setFormatter(logging.Formatter('%(message)s'))

# Don't attach automatically - will be attached in main.py after logging config
