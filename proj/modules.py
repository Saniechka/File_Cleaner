import os
import hashlib
import stat
from collections import defaultdict
import shutil
import json
from config import TEMP_EXTENSIONS
from config import BAD_CHARS
from config import BAD_CHARS, REPLACE_CHAR
from config import SCAN_DIRS
from config import DEFAULT_PERMISSIONS, SCAN_DIRS
from config import ACTIONS_FILE

def is_empty(path):
    try:
        return os.path.getsize(path) == 0
    except OSError:
        return False

def is_temp(path):
    return any(path.endswith(ext) for ext in TEMP_EXTENSIONS)

def has_bad_chars(path):
    name = os.path.basename(path)
    return any(ch in name for ch in BAD_CHARS)

def is_nonstandard_permissions(path):
    try:
        mode = os.stat(path).st_mode
        return stat.S_IMODE(mode) != 0o644
    except OSError:
        return False

def sanitize_filename(name): # replace chars
    return ''.join(c if c not in BAD_CHARS else REPLACE_CHAR for c in name)

def get_file_hash(path):
    hasher = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError:
        return None


def find_same_name_different_mtime(files):
    name_map = defaultdict(list)
    for file in files:
        name_map[file["name"]].append(file)
    
    result = {}
    for name, group in name_map.items():
        if len(group) > 1:
            group.sort(key=lambda x: x["mtime"], reverse=True)
            result[name] = group
    return result

def suggest_oldest_of_duplicates(duplicates):
    result = {}
    for hash, paths in duplicates.items():
        sorted_paths = sorted(paths, key=lambda p: os.path.getmtime(p))
        result[hash] = {
            "keep": sorted_paths[0],
            "remove": sorted_paths[1:]
        }
    return result

def scan_directories():
    
    
    files = []
    duplicates = defaultdict(list)
    
    for dir in SCAN_DIRS:
        if not os.path.exists(dir):
            continue
        for root, _, filenames in os.walk(dir):
            for name in filenames:
                path = os.path.join(root, name)
                try:
                    mtime = os.path.getmtime(path)
                    file_info = {
                        "path": path,
                        "name": name,
                        "mtime": mtime,
                        "dir": dir
                    }
                    files.append(file_info)
                    
                    
                    file_hash = get_file_hash(path)
                    if file_hash:
                        duplicates[file_hash].append(path)
                except OSError:
                    continue
    
    return files, duplicates


def save_actions_to_json(grouped_actions):
    
    
    try:
        with open(ACTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(grouped_actions, f, indent=4, ensure_ascii=False)
        return f"Saved actions to {ACTIONS_FILE}"
    except Exception as e:
        return f"Error saving actions to {ACTIONS_FILE}: {e}"

def load_actions_from_json():
   
    
    try:
        if not os.path.exists(ACTIONS_FILE):
            return None
        with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading actions from {ACTIONS_FILE}: {e}")
        return None



def analyze_files(files, duplicates):
    
    
    grouped_actions = {
        "empty": [],
        "temporary": [],
        "bad_chars": [],
        "nonstandard_perms": [],
        "same_name": [],
        "duplicates": [],
        "move_to_x": []
    }
    
   
    non_empty_files = []
    for file in files:
        if is_empty(file["path"]):
            grouped_actions["empty"].append({
                "path": file["path"],
                "action": "delete",
                "reason": "Empty file"
            })
        else:
            non_empty_files.append(file)
    
    
    for file in non_empty_files:
        
        if is_temp(file["path"]):
            grouped_actions["temporary"].append({
                "path": file["path"],
                "action": "delete",
                "reason": "Temporary file"
            })
        
        
        if has_bad_chars(file["path"]):
            new_name = sanitize_filename(file["name"])
            new_path = os.path.join(os.path.dirname(file["path"]), new_name)
            grouped_actions["bad_chars"].append({
                "path": file["path"],
                "action": "rename",
                "new_path": new_path,
                "reason": "Problematic characters in name"
            })
        
       
        if is_nonstandard_permissions(file["path"]):
            grouped_actions["nonstandard_perms"].append({
                "path": file["path"],
                "action": "chmod",
                "new_mode": DEFAULT_PERMISSIONS,
                "reason": "Non-standard permissions"
            })
        
        
        if file["dir"] != SCAN_DIRS[0]:  
            new_path = os.path.join(SCAN_DIRS[0], file["name"])
            grouped_actions["move_to_x"].append({
                "path": file["path"],
                "action": "move",
                "new_path": new_path,
                "reason": f"Move to {SCAN_DIRS[0]}"
            })
    
   
    same_name_groups = find_same_name_different_mtime(non_empty_files)
    for name, group in same_name_groups.items():
        for i, file in enumerate(group[1:], 1):
            grouped_actions["same_name"].append({
                "path": file["path"],
                "action": "delete",
                "reason": f"Older version of {name}, newer exists at {group[0]['path']}"
            })
    
    
    duplicate_suggestions = suggest_oldest_of_duplicates(duplicates)
    for hash, suggestion in duplicate_suggestions.items():
        for path in suggestion["remove"]:
            grouped_actions["duplicates"].append({
                "path": path,
                "action": "delete",
                "reason": f"Duplicate of {suggestion['keep']}"
            })
    
    return grouped_actions



def execute_action(action):
    """Execute the specified action on a file."""
    try:
        if action["action"] == "delete":
            os.remove(action["path"])
            return f"Deleted: {action['path']}"
        elif action["action"] == "move":
            os.makedirs(os.path.dirname(action["new_path"]), exist_ok=True)
            shutil.move(action["path"], action["new_path"])
            return f"Moved: {action['path']} to {action['new_path']}"
        elif action["action"] == "rename":
            os.rename(action["path"], action["new_path"])
            return f"Renamed: {action['path']} to {action['new_path']}"
        elif action["action"] == "chmod":
            os.chmod(action["path"], action["new_mode"])
            return f"Changed permissions: {action['path']} to {DEFAULT_PERMISSIONS}"
        elif action["action"] == "keep":
            return f"Kept unchanged: {action['path']}"
        else:
            return f"Unknown action for {action['path']}"
    except Exception as e:
        return f"Error processing {action['path']}: {e}"