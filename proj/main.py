import os
import sys
import stat
import argparse
from modules import scan_directories, analyze_files, execute_action, save_actions_to_json, load_actions_from_json
from config import DEFAULT_PERMISSIONS,MAIN_FOLDER






def print_group_actions(group_name, actions):
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

def get_file_choice(action):
   
    print(f"\nFile: {action['path']}")
    print(f"Suggested action: {action['action']}")
    if action.get("new_path"):
        print(f"New path: {action['new_path']}")
    if action.get("new_mode"):
        print(f"New mode: {DEFAULT_PERMISSIONS}")
    print(f"Reason: {action['reason']}")
    print("-" * 50)

    valid_actions = {action["action"]}
    action_prompt = "Choose action for this file ("
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

def get_group_choice(group_name, actions, mode):
    
    if not actions:
        return []

    if mode == "analyze":
        
        chosen_actions = []
        print_group_actions(group_name, actions)
        for action in actions:
            chosen_action = get_file_choice(action)
            if chosen_action:
                chosen_actions.append({**action, "action": chosen_action})
        return chosen_actions
    else:
        
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
                    return choice
                elif choice == 'm' and "move" in valid_actions:
                    return choice
                elif choice == 'r' and "rename" in valid_actions:
                    return choice
                elif choice == 'c' and "chmod" in valid_actions:
                    return choice
                elif choice == 'k':
                    return choice
                elif choice == 's':
                    return []
            print("Invalid choice. Please try again.")

def select_groups_and_actions(grouped_actions):
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
                    selected_groups[name] = get_group_choice(name, grouped_actions[name], mode="select")
            break

        try:
            indices = [int(i) - 1 for i in choice.split()]
            for idx in indices:
                if 0 <= idx < len(group_names):
                    name = group_names[idx]
                    if name not in selected_groups:
                        selected_groups[name] = get_group_choice(name, grouped_actions[name], mode="select")
                else:
                    print(f"Invalid group number: {idx + 1}")
        except ValueError:
            print("Invalid input. Enter numbers, 'all', or 'done'.")

    return selected_groups




def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Narzędzie do czyszczenia folderow"
    )
    parser.add_argument(
        "mode",
        choices=["analyze", "auto", "replay", "select", "json"],
        nargs='?',
        default="analyze",
        help="Tryb działania: analyze (interaktywny,kazdy plik podtwierdzamy), auto (automatyczny), replay ( wykonaj akcje z JSON-a), select ( grupy plików), json (generuj  JSON)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    mode = args.mode

    if mode == "json":
        files, duplicates = scan_directories()
        grouped_actions = analyze_files(files, duplicates)

        if not any(grouped_actions.values()):
            print("No actions suggested.")
            return

        save_result = save_actions_to_json(grouped_actions)
        print(save_result)
        print("JSON generation complete. Use 'replay' mode to execute actions.")
        return

    if mode == "replay":
        grouped_actions = load_actions_from_json()
        if not grouped_actions:
            print("No actions loaded. Run in analyze, auto, select, or json mode first.")
            return

        print("Replaying actions from actions.json...")
        for group_name, actions in grouped_actions.items():
            if not actions:
                continue
            for action in actions:
                result = execute_action(action)
                print(result)

    else:
        files, duplicates = scan_directories()
        grouped_actions = analyze_files(files, duplicates)

        if not any(grouped_actions.values()):
            print("No actions suggested.")
            return

        
        save_result = save_actions_to_json(grouped_actions)
        print(save_result)

        
        print("Processing files...")
        deleted_paths = set()
        renamed_paths ={}
        if mode == "select":
            
            selected_groups = select_groups_and_actions(grouped_actions)
            renamed_paths = {}  #zmiany nazw
            
            for group_name, actions in selected_groups.items():
                for action in actions:
                    original_path = action["path"]
                    current_path = renamed_paths.get(original_path, original_path)
                    action["path"] = current_path

                    if action["action"] == "move":
                        if current_path in deleted_paths:
                            print(f"Skipped moving {current_path}: already deleted")
                            continue
                        action["new_path"] = os.path.join(
                            os.path.dirname(action["new_path"]),
                            os.path.basename(current_path)
                        )

                    result = execute_action(action)
                    print(result)

                    if action["action"] == "delete" and result.startswith("Deleted:"):
                        deleted_paths.add(current_path)

                    if action["action"] == "rename" and result.startswith("Renamed:"):
                        renamed_paths[original_path] = action["new_path"]


        elif mode == "auto":
        
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
                        renamed_paths[action["path"]] = action["new_path"]
                        print(result)
                    elif group_name == "move_to_x" and action["path"] not in deleted_paths:
                        if action["path"] in renamed_paths:
                            
                            new_name = os.path.basename(renamed_paths[action["path"]])  
                            new_path = os.path.join(MAIN_FOLDER, new_name)  
                            action["path"] = renamed_paths[action["path"]]  
                            action["new_path"] = new_path

                           
                        result = execute_action({**action, "action": "move"})
                        print(result)

        else:
            
            updated_actions = {}
            for group_name, actions in grouped_actions.items():
                if not actions:
                    continue
                chosen_actions = get_group_choice(group_name, actions, mode="analyze")
                updated_actions[group_name] = []
                for chosen_action in chosen_actions:
                    if chosen_action:
                        if chosen_action["action"] == "move" and chosen_action["path"] in deleted_paths:
                            print(f"Skipped moving {chosen_action['path']}: already deleted")
                            continue
                        result = execute_action(chosen_action)
                        print(result)
                        updated_actions[group_name].append(chosen_action)
                        if chosen_action["action"] == "delete" and result.startswith("Deleted:"):
                            deleted_paths.add(chosen_action["path"])
                    else:
                        
                        updated_actions[group_name].append(next(a for a in actions if a["path"] == chosen_action["path"]))

            
            save_actions_to_json(updated_actions)

    print("Processing complete. Actions saved to actions.json.")

if __name__ == "__main__":
    main()