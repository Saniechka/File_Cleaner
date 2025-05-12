import os
import shutil
import time

def create_file(path, content="", mtime=None, permissions=0o644):
    """Create a file with specified content, modification time, and permissions."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    os.chmod(path, permissions)

def clear_directories(dirs):
    """Clear specified directories if they exist."""
    for dir in dirs:
        if os.path.exists(dir):
            shutil.rmtree(dir)
        os.makedirs(dir)

def main():
    """Create test files for file organization project."""
    # Define directories matching config.py
    dirs = ["x", "y1", "y2"]
    
    # Clear directories to start fresh
    clear_directories(dirs)
    
    # Current time and offsets for modification times
    now = time.time()
    older = now - 3600  # 1 hour ago
    newer = now - 1800  # 30 minutes ago
    
    # 1. Empty files
    create_file("y1/empty.txt", mtime=now)
    create_file("y2/zero.txt", mtime=older)
    
    # 2. Temporary files
    create_file("y1/file.bak", content="Temp file", mtime=now)
    create_file("x/temp.tmp", content="Temporary content", mtime=older)
    create_file("y2/note.txt~", content="Backup note", mtime=newer)
    
    # 3. Files with problematic characters
    create_file("y1/test:file*.txt", content="File with bad chars", mtime=now)
    create_file("y2/doc space.txt", content="File with space", mtime=older)
    create_file("x/photo#album.jpg", content="Photo file", mtime=newer)
    
    # 4. Files with non-standard permissions
    create_file("y1/executable.txt", content="Executable file", mtime=now, permissions=0o777)
    create_file("y2/write_all.txt", content="All write access", mtime=older, permissions=0o777)
    
    # 5. Files with same name, different modification times
    create_file("x/doc.txt", content="Document in x", mtime=older)
    create_file("y1/doc.txt", content="Document in y1", mtime=newer)
    create_file("y2/doc.txt", content="Document in y2", mtime=now)
    
    # 6. Duplicate files (same content, different names/locations)
    duplicate_content = "This is a duplicate file content."
    create_file("x/original.txt", content=duplicate_content, mtime=older)
    create_file("y1/copy.txt", content=duplicate_content, mtime=newer)
    create_file("y2/duplicate.txt", content=duplicate_content, mtime=now)
    
    # 7. Normal files to move to x
    create_file("y1/normal1.txt", content="Normal file 1", mtime=now)
    create_file("y2/normal2.txt", content="Normal file 2", mtime=older)
    
    print("Test files created in directories: x, y1, y2")
    print("Run your script to test file organization (e.g., python main.py analyze)")

if __name__ == "__main__":
    main()
