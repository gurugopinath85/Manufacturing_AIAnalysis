"""
File utilities for handling uploads, validation, and file operations.
"""
import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd
from werkzeug.utils import secure_filename

from app.core.config import get_settings


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    return Path(filename).suffix.lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file type is allowed."""
    settings = get_settings()
    extension = get_file_extension(filename)
    return extension in settings.allowed_file_types


def get_file_size(filepath: str) -> int:
    """Get file size in bytes."""
    return os.path.getsize(filepath)


def validate_file_size(filepath: str) -> bool:
    """Validate file size against maximum allowed."""
    settings = get_settings()
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024
    return get_file_size(filepath) <= max_size_bytes


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Use secure_filename to handle security issues
    safe_name = secure_filename(filename)
    
    # Additional sanitization
    safe_name = safe_name.replace(" ", "_")
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
    
    return safe_name


def ensure_upload_directory() -> str:
    """Ensure upload directory exists and return path."""
    settings = get_settings()
    upload_path = Path(settings.upload_directory)
    
    # Create directory if it doesn't exist
    upload_path.mkdir(parents=True, exist_ok=True)
    
    return str(upload_path.absolute())


def save_uploaded_file(file_content: bytes, filename: str) -> Tuple[str, int]:
    """
    Save uploaded file content to disk.
    
    Returns:
        Tuple of (file_path, file_size)
    """
    # Validate file type
    if not is_allowed_file(filename):
        raise ValueError(f"File type not allowed: {get_file_extension(filename)}")
    
    # Sanitize filename
    safe_filename = sanitize_filename(filename)
    
    # Ensure upload directory exists
    upload_dir = ensure_upload_directory()
    
    # Handle filename conflicts
    file_path = os.path.join(upload_dir, safe_filename)
    counter = 1
    
    while os.path.exists(file_path):
        name, ext = os.path.splitext(safe_filename)
        file_path = os.path.join(upload_dir, f"{name}_{counter}{ext}")
        counter += 1
    
    # Write file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    # Validate file size after saving
    if not validate_file_size(file_path):
        os.remove(file_path)  # Clean up
        settings = get_settings()
        raise ValueError(f"File size exceeds maximum allowed: {settings.max_file_size_mb}MB")
    
    return file_path, get_file_size(file_path)


def list_uploaded_files() -> List[Dict[str, any]]:
    """List all uploaded files with metadata."""
    upload_dir = ensure_upload_directory()
    files = []
    
    for filename in os.listdir(upload_dir):
        filepath = os.path.join(upload_dir, filename)
        if os.path.isfile(filepath) and is_allowed_file(filename):
            stat = os.stat(filepath)
            files.append({
                'name': filename,
                'path': filepath,
                'size_bytes': stat.st_size,
                'modified': stat.st_mtime,
                'extension': get_file_extension(filename)
            })
    
    return sorted(files, key=lambda x: x['modified'], reverse=True)


def delete_uploaded_file(filename: str) -> bool:
    """Delete an uploaded file."""
    upload_dir = ensure_upload_directory()
    file_path = os.path.join(upload_dir, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False


def read_data_file(filepath: str) -> pd.DataFrame:
    """
    Read a data file (CSV or Excel) into a pandas DataFrame.
    
    Args:
        filepath: Path to the data file
        
    Returns:
        pandas DataFrame with the data
    """
    extension = get_file_extension(filepath)
    
    try:
        if extension == '.csv':
            # Try different encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    df = pd.read_csv(filepath, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not read CSV file with any supported encoding")
                
        elif extension in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        else:
            raise ValueError(f"Unsupported file format: {extension}")
        
        # Basic validation
        if df.empty:
            raise ValueError("File contains no data")
            
        return df
        
    except Exception as e:
        raise ValueError(f"Error reading file {filepath}: {str(e)}")


def get_table_name_from_filename(filepath: str) -> str:
    """Extract table name from file path."""
    filename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(filename)[0]
    
    # Clean up name for use as table name
    table_name = name_without_ext.lower()
    table_name = "".join(c if c.isalnum() else "_" for c in table_name)
    table_name = "_".join(part for part in table_name.split("_") if part)
    
    return table_name


def backup_file(filepath: str) -> str:
    """Create a backup copy of a file."""
    backup_path = f"{filepath}.backup"
    shutil.copy2(filepath, backup_path)
    return backup_path


def clean_old_files(max_age_days: int = 30) -> List[str]:
    """
    Clean up old uploaded files.
    
    Args:
        max_age_days: Files older than this will be deleted
        
    Returns:
        List of deleted file paths
    """
    import time
    
    upload_dir = ensure_upload_directory()
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    deleted_files = []
    
    for filename in os.listdir(upload_dir):
        filepath = os.path.join(upload_dir, filename)
        if os.path.isfile(filepath):
            file_age = current_time - os.path.getmtime(filepath)
            if file_age > max_age_seconds:
                try:
                    os.remove(filepath)
                    deleted_files.append(filepath)
                except OSError:
                    pass  # Skip files that can't be deleted
    
    return deleted_files
