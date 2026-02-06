"""
Torrent Validation Utilities
Centralized validation functions for .torrent files
"""
import logging
import time
from pathlib import Path
from typing import Tuple
from app.core.torrent_parser import Torrent

logger = logging.getLogger(__name__)


def validate_torrent_file(file_path: Path, content: bytes = None, retry_count: int = 3) -> Tuple[bool, str]:
    """
    Comprehensive validation for .torrent files with retry logic
    
    Args:
        file_path: Path to the torrent file
        content: Optional file content (for in-memory validation)
        retry_count: Number of retries for transient errors
    
    Returns:
        (is_valid, error_message)
    """
    last_error = ""
    
    for attempt in range(retry_count):
        try:
            # Check file size (must be > 0 and < 10MB for safety)
            if content:
                file_size = len(content)
            else:
                if not file_path.exists():
                    return False, "File does not exist"
                file_size = file_path.stat().st_size
                
            if file_size == 0:
                # File might still be writing - retry
                if attempt < retry_count - 1:
                    time.sleep(0.5)
                    continue
                return False, "File is empty (0 bytes)"
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                return False, f"File too large ({file_size / 1024 / 1024:.1f}MB > 10MB limit)"
            
            # Check file header (should start with bencode 'd')
            if content:
                header = content[:20] if len(content) >= 20 else content
            else:
                with open(file_path, 'rb') as f:
                    header = f.read(20)
                    
            if len(header) == 0:
                # File might still be writing - retry
                if attempt < retry_count - 1:
                    time.sleep(0.5)
                    continue
                return False, "Could not read file (empty read)"
                    
            if header[0:1] != b'd':
                # This is a real format error - no retry needed
                header_hex = header[:10].hex()
                header_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in header[:10])
                return False, f"Not a torrent file (header: {header_hex} = '{header_ascii}')"
            
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
                return False, "Torrent has no name (missing 'name' field in info dict)"
            
            if not test_torrent.info_hash or len(test_torrent.info_hash) != 40:
                return False, f"Invalid info hash (got {len(test_torrent.info_hash) if test_torrent.info_hash else 0} chars, expected 40)"
            
            if test_torrent.size <= 0:
                return False, f"Invalid torrent size ({test_torrent.size} bytes)"
            
            # Check if we have at least one tracker
            if not hasattr(test_torrent, 'trackers') or not test_torrent.trackers:
                return False, "No tracker URLs found (missing 'announce' field)"
            
            return True, "Valid torrent"
            
        except Exception as e:
            last_error = str(e)
            # Retry on transient errors
            if attempt < retry_count - 1:
                time.sleep(0.5)
                continue
            
    return False, f"Parsing failed after {retry_count} attempts: {last_error}"


def quick_validate_torrent_file(file_path: Path) -> bool:
    """Quick validation for file watcher (basic checks only)"""
    try:
        # Skip Windows Zone.Identifier files
        if ':Zone.Identifier' in str(file_path) or file_path.name.endswith(':Zone.Identifier'):
            logger.debug(f"Skipping Zone.Identifier file: {file_path}")
            return False
        
        # Basic checks
        if not file_path.exists():
            logger.debug(f"File does not exist: {file_path}")
            return False
            
        file_size = file_path.stat().st_size
        if file_size == 0:
            logger.debug(f"File is empty: {file_path}")
            return False
        
        # Check file header (should start with bencode 'd')
        with open(file_path, 'rb') as f:
            header = f.read(10)  # Read more for debugging
            
        if len(header) == 0:
            logger.debug(f"Could not read header from: {file_path}")
            return False
            
        if header[0:1] != b'd':
            logger.warning(f"Invalid torrent header for {file_path.name}: first bytes = {header[:10].hex()} (expected 'd' = 0x64)")
            return False
            
        return True
    except Exception as e:
        logger.debug(f"Quick validation exception for {file_path}: {e}")
        return False