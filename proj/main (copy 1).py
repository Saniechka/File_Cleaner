import os
import sys
from modules import scan_directories, analyze_files, execute_action, save_actions_to_json, load_actions_from_json
from config import DEFAULT_PERMISSIONS

def print_group_actions(group_name, actions):
    """Print actions for a group of files."""
    print(f"\n=== {group_name.replace('_', ' ').title()} ({len(actions)} files) ===")
    for action in actions:
        print(f"File: {action['path']}")
        print(f"Suggested action: {action['action']}")
        if action.get("new_path"):
            print(f"New path: {action['new_path']}")
        if action.get("new_mode"):
            print(f"New mode: {DEFAULT_PERMISSIONS}")
        print(f"Reason: {action['reason']}")
        print("-" * 50)

def get_group_choice(group_name, actions):
    """Get user choice for a group of actions."""
    if not actions:
        return None
    
    print_group_actions(group_name, actions)
    valid_actions = set(action["action"] for action in actions)
    action_prompt = "Choose action for all files in this group ("
    if "delete" in valid_actions:
        action_prompt += "d: delete, "
    if "move" in valid_actions:
        action_prompt += "m: move, "
    if "rename" in valid_actions:
        action_prompt += "r: rename, "
    if "chmod" in valid_actions:
        action_prompt += "c: chmod, "
    action_prompt += "k: keep, s: skip): "
    
    while True:
        choice = input(action_prompt).lower()
        if choice in ['d', 'm', 'r', 'c', 'k', 's']:
            if choice == 'd' and "delete" in valid_actions:
                return "delete"
            elif choice == 'm' and "move" in valid_actions:
                return "move"
            elif choice == 'r' and "rename" in valid_actions:
                return "rename"
            elif choice == 'c' and "chmod" in valid_actions:
                return "chmod"
            elif choice == 'k':
                return "keep"
            elif choice == 's':
                return None
        print("Invalid choice. Please try again.")



def select_groups_and_actions(grouped_actions):
    """Allow user to select groups and actions for the select mode."""
    group_names = [name for name, actions in grouped_actions.items() if actions]
    if not group_names:
        return {}
    
    print("\nAvailable groups:")
    for i, name in enumerate(group_names, 1):
        print(f"{i}. {name.replace('_', ' ').title()} ({len(grouped_actions[name])} files)")
    
    selected_groups = {}
    while True:
        choice = input("\nEnter group numbers to process (e.g., '1 2 3', or 'all' for all, or 'done' to finish): ").lower()
        if choice == 'done':
            break
        elif choice == 'all':
            for name in group_names:
                if name not in selected_groups:
                    selected_groups[name] = get_group_choice(name, grouped_actions[name])
            break
        
        try:
            indices = [int(i) - 1 for i in choice.split()]
            for idx in indices:
                if 0 <= idx < len(group_names):
                    name = group_names[idx]
                    if name not in selected_groups:
                        selected_groups[name] = get_group_choice(name, grouped_actions[name])
                else:
                    print(f"Invalid group number: {idx + 1}")
        except ValueError:
            print("Invalid input. Enter numbers, 'all', or 'done'.")
    
    return selected_groups
def main():
    """Main function to run the file organization script."""
    # Check for mode
    mode = "analyze"  # Default mode
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode not in ["analyze", "auto", "replay", "select"]:
            print("Invalid mode. Use: analyze, auto, replay, select")
            return
    
    # Process based on mode
    if mode == "replay":
        # Replay mode: load actions from JSON and execute automatically
        grouped_actions = load_actions_from_json()
        if not grouped_actions:
            print("No actions loaded. Run in analyze, auto, or select mode first.")
            return
        
        print("Replaying actions from actions.json...")
        for group_name, actions in grouped_actions.items():
            if not actions:
                continue
            for action in actions:
                result = execute_action(action)
                print(result)
    
    else:
        # Analyze, auto, or select mode: scan directories and generate actions
        files, duplicates = scan_directories()
        grouped_actions = analyze_files(files, duplicates)
        
        if not any(grouped_actions.values()):
            print("No actions suggested.")
            return
        
        # Save actions to JSON
        save_result = save_actions_to_json(grouped_actions)
        print(save_result)
        
        # Process actions
        print("Processing files...")
        deleted_paths = set()  # Track deleted files to avoid moving them
        if mode == "select":
            # Select mode: choose groups and actions, then execute
            selected_groups = select_groups_and_actions(grouped_actions)
            for group_name, chosen_action in selected_groups.items():
                if chosen_action:
                    for action in grouped_actions[group_name]:
                        if chosen_action == "move" and action["path"] in deleted_paths:
                            print(f"Skipped moving {action['path']}: already deleted")
                            continue
                        result = execute_action({**action, "action": chosen_action})
                        print(result)
                        if chosen_action == "delete" and result.startswith("Deleted:"):
                            deleted_paths.add(action["path"])
        
        elif mode == "auto":
            # Auto mode: automatically execute actions for specific groups
            for group_name, actions in grouped_actions.items():
                if not actions:
                    continue
                for action in actions:
                    if group_name in ["temporary", "duplicates"]:
                        result = execute_action({**action, "action": "delete"})
                        print(result)
                        if result.startswith("Deleted:"):
                            deleted_paths.add(action["path"])
                    elif group_name == "bad_chars":
                        result = execute_action({**action, "action": "rename"})
                        print(result)
                    elif group_name == "move_to_x" and action["path"] not in deleted_paths:
                        result = execute_action({**action, "action": "move"})
                        print(result)
        
        else:
            # Interactive mode (analyze): process group by group
            for group_name, actions in grouped_actions.items():
                if not actions:
                    continue
                chosen_action = get_group_choice(group_name, actions)
                if chosen_action:
                    for action in actions:
                        if chosen_action == "move" and action["path"] in deleted_paths:
                            print(f"Skipped moving {action['path']}: already deleted")
                            continue
                        result = execute_action({**action, "action": chosen_action})
                        print(result)
                        if chosen_action == "delete" and result.startswith("Deleted:"):
                            deleted_paths.add(action["path"])
    
    print("Processing complete. Actions saved to actions.json.")

if __name__ == "__main__":
    main()