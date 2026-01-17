"""
Torrent Validation Utilities
Centralized validation functions for .torrent files
"""
import logging
from pathlib import Path
from typing import Tuple
from app.core.torrent_parser import Torrent

logger = logging.getLogger(__name__)


def validate_torrent_file(file_path: Path, content: bytes = None) -> Tuple[bool, str]:
    """
    Comprehensive validation for .torrent files
    
    Args:
        file_path: Path to the torrent file
        content: Optional file content (for in-memory validation)
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # Check file size (must be > 0 and < 10MB for safety)
        if content:
            file_size = len(content)
        else:
            if not file_path.exists():
                return False, "File does not exist"
            file_size = file_path.stat().st_size
            
        if file_size == 0:
            return False, "File is empty"
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            return False, "File too large (>10MB)"
        
        # Check file header (should start with bencode 'd')
        if content:
            header = content[:1] if len(content) > 0 else b''
        else:
            with open(file_path, 'rb') as f:
                header = f.read(1)
                
        if header != b'd':
            return False, "Invalid torrent file format (not bencoded)"
        
        # Try to parse as Torrent (this will validate bencoding and required fields)
        if content:
            # For in-memory validation, write to temp file
            temp_file = file_path.parent / f"temp_validate_{file_path.name}"
            with open(temp_file, 'wb') as f:
                f.write(content)
            try:
                test_torrent = Torrent(temp_file)
            finally:
                temp_file.unlink(missing_ok=True)
        else:
            test_torrent = Torrent(file_path)
        
        # Basic validation checks
        if not test_torrent.name or len(test_torrent.name.strip()) == 0:
            return False, "Missing or empty torrent name"
        
        if not test_torrent.info_hash or len(test_torrent.info_hash) != 40:
            return False, "Invalid info hash"
        
        if test_torrent.size <= 0:
            return False, "Invalid file size"
        
        # Check if we have at least one tracker
        if not hasattr(test_torrent, 'trackers') or not test_torrent.trackers:
            return False, "No trackers found"
        
        return True, "Valid torrent"
        
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


def quick_validate_torrent_file(file_path: Path) -> bool:
    """Quick validation for file watcher (basic checks only)"""
    try:
        # Basic checks
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False
        
        # Check file header (should start with bencode 'd')
        with open(file_path, 'rb') as f:
            header = f.read(1)
            return header == b'd'
    except Exception:
        return False