import os
import sys
import stat
import argparse
from modules import scan_directories, analyze_files, execute_action, save_actions_to_json, load_actions_from_json
from config import DEFAULT_PERMISSIONS,MAIN_FOLDER


def print_group_actions(group_name, actions, renamed_paths=None):
    renamed_paths = renamed_paths or {}
    print(f"\n=== {group_name.replace('_', ' ').title()} ({len(actions)} files) ===")
    for action in actions:
        current_path = renamed_paths.get(action['path'], action['path'])
        print(f"File: {current_path}")
        print(f"Suggested action: {action['action']}")
        if action.get("new_path"):
            new_path = renamed_paths.get(action['new_path'], action['new_path'])
            print(f"New path: {new_path}")
        if action.get("new_mode"):
            print(f"New mode: {DEFAULT_PERMISSIONS}")
        print(f"Reason: {action['reason']}")
        print("-" * 50)

def get_file_choice(action, deleted_paths=None, renamed_paths=None):
    deleted_paths = deleted_paths or set()
    renamed_paths = renamed_paths or {}
    
    current_path = renamed_paths.get(action['path'], action['path'])
    print(f"\nFile: {current_path}")
    print(f"Suggested action: {action['action']}")
    if action.get("new_path"):
        new_path = renamed_paths.get(action['new_path'], action['new_path'])
        print(f"New path: {new_path}")
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
                return "delete", current_path
            elif choice == 'm' and "move" in valid_actions:
                return "move", current_path
            elif choice == 'r' and "rename" in valid_actions:
                return "rename", current_path
            elif choice == 'c' and "chmod" in valid_actions:
                return "chmod", current_path
            elif choice == 'k':
                return "keep", current_path
            elif choice == 's':
                return None, current_path
        print("Invalid choice. Please try again.")

def get_group_choice(group_name, actions, mode, deleted_paths=None, renamed_paths=None):
    deleted_paths = deleted_paths or set()
    renamed_paths = renamed_paths or {}
    
    if not actions:
        return []

    if mode == "analyze":
        chosen_actions = []
        print_group_actions(group_name, actions, renamed_paths)
        for action in actions:
            if action['path'] in deleted_paths:
                print(f"Skipped {action['path']}: already deleted")
                continue
            chosen_action, current_path = get_file_choice(action, deleted_paths, renamed_paths)
            if chosen_action:
                updated_action = {**action, "action": chosen_action, "path": current_path}
                if updated_action.get("new_path") and current_path in renamed_paths:
                    updated_action["new_path"] = renamed_paths[current_path]
                chosen_actions.append(updated_action)
        return chosen_actions
    else:  # select mode
        print_group_actions(group_name, actions, renamed_paths)
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
                    return [{"path": renamed_paths.get(a["path"], a["path"]), **a, "action": "delete"} for a in actions]
                elif choice == 'm' and "move" in valid_actions:
                    return [{"path": renamed_paths.get(a["path"], a["path"]), **a, "action": "move"} for a in actions]
                elif choice == 'r' and "rename" in valid_actions:
                    return [{"path": renamed_paths.get(a["path"], a["path"]), **a, "action": "rename"} for a in actions]
                elif choice == 'c' and "chmod" in valid_actions:
                    return [{"path": renamed_paths.get(a["path"], a["path"]), **a, "action": "chmod"} for a in actions]
                elif choice == 'k':
                    return [{"path": renamed_paths.get(a["path"], a["path"]), **a, "action": "keep"} for a in actions]
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
    deleted_paths = set()
    renamed_paths = {}
    
    while True:
        choice = input("\nEnter group numbers to process (e.g., '1 2 3', or 'all' for all, or 'done' to finish): ").lower()
        if choice == 'done':
            break
        elif choice == 'all':
            for name in group_names:
                if name not in selected_groups:
                    selected_groups[name] = get_group_choice(
                        name, grouped_actions[name], mode="select", deleted_paths=deleted_paths, renamed_paths=renamed_paths
                    )
            break

        try:
            indices = [int(i) - 1 for i in choice.split()]
            for idx in indices:
                if 0 <= idx < len(group_names):
                    name = group_names[idx]
                    if name not in selected_groups:
                        selected_groups[name] = get_group_choice(
                            name, grouped_actions[name], mode="select", deleted_paths=deleted_paths, renamed_paths=renamed_paths
                        )
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

        # Tworzenie mapowania nowych nazw dla grupy bad_chars
        renamed_paths = {}
        if "bad_chars" in grouped_actions:
            for action in grouped_actions["bad_chars"]:
                if action["action"] == "rename" and action.get("new_path"):
                    renamed_paths[action["path"]] = action["new_path"]

        # Zbieranie ścieżek plików do usunięcia z grup temporary, duplicates itp.
        paths_to_delete = set()
        for group_name in ["temporary", "duplicates", "empty"]:  # Dodaj inne grupy, jeśli potrzebne
            if group_name in grouped_actions:
                for action in grouped_actions[group_name]:
                    if action["action"] == "delete":
                        paths_to_delete.add(action["path"])

        # Aktualizacja grupy move_to_x
        if "move_to_x" in grouped_actions:
            updated_actions = []
            for action in grouped_actions["move_to_x"]:
                current_path = renamed_paths.get(action["path"], action["path"])
                # Pomijamy pliki, które są sugerowane do usunięcia
                if current_path in paths_to_delete:
                    continue
                updated_action = {**action, "path": current_path}
                if action.get("new_path"):
                    updated_action["new_path"] = os.path.join(
                        MAIN_FOLDER, os.path.basename(current_path)
                    )
                updated_actions.append(updated_action)
            grouped_actions["move_to_x"] = updated_actions

        save_result = save_actions_to_json(grouped_actions)
        print(save_result)
        print("JSON generation complete. Use 'replay' mode to execute actions.")
        return

    # Reszta kodu (tryby replay, select, auto, analyze) pozostaje bez zmian
    if mode == "replay":
        grouped_actions = load_actions_from_json()
        if not grouped_actions:
            print("No actions loaded. Run in analyze, auto, select, or json mode first.")
            return
        print("Replaying actions from actions.json...")
        deleted_paths = set()
        for group_name, actions in grouped_actions.items():
            if not actions:
                continue
            for action in actions:
                if action["path"] in deleted_paths:
                    print(f"Skipped {action['path']}: already deleted in this run")
                    continue
                result = execute_action(action)
                print(result)
                if result.startswith("Deleted:"):
                    deleted_paths.add(action["path"])
        return

    files, duplicates = scan_directories()
    grouped_actions = analyze_files(files, duplicates)

    if not any(grouped_actions.values()):
        print("No actions suggested.")
        return

    save_result = save_actions_to_json(grouped_actions)
    print(save_result)

    print("Processing files...")
    deleted_paths = set()
    renamed_paths = {}

    if mode == "select":
        selected_groups = select_groups_and_actions(grouped_actions)
        for group_name, actions in selected_groups.items():
            if not actions:
                continue
            updated_actions = []
            for action in actions:
                original_path = action["path"]
                current_path = renamed_paths.get(original_path, original_path)
                if current_path in deleted_paths:
                    print(f"Skipped {current_path}: already deleted")
                    continue
                action["path"] = current_path
                if action["action"] == "move":
                    action["new_path"] = os.path.join(
                        MAIN_FOLDER, os.path.basename(current_path)
                    )
                result = execute_action(action)
                print(result)
                if result.startswith("Deleted:"):
                    deleted_paths.add(current_path)
                if result.startswith("Renamed:"):
                    renamed_paths[original_path] = action["new_path"]
                updated_actions.append(action)
            grouped_actions[group_name] = [
                a for a in grouped_actions[group_name] if a["path"] not in deleted_paths
            ]
        save_actions_to_json(grouped_actions)

    elif mode == "auto":
        for group_name, actions in grouped_actions.items():
            if not actions:
                continue
            updated_actions = []
            for action in actions:
                current_path = renamed_paths.get(action["path"], action["path"])
                if current_path in deleted_paths:
                    print(f"Skipped {current_path}: already deleted")
                    continue
                action["path"] = current_path
                if group_name in ["temporary", "duplicates"]:
                    result = execute_action({**action, "action": "delete"})
                    print(result)
                    if result.startswith("Deleted:"):
                        deleted_paths.add(current_path)
                elif group_name == "bad_chars":
                    result = execute_action({**action, "action": "rename"})
                    print(result)
                    if result.startswith("Renamed:"):
                        renamed_paths[current_path] = action["new_path"]
                elif group_name == "move_to_x" and current_path not in deleted_paths:
                    action["new_path"] = os.path.join(
                        MAIN_FOLDER, os.path.basename(current_path)
                    )
                    result = execute_action({**action, "action": "move"})
                    print(result)
                updated_actions.append(action)
            grouped_actions[group_name] = [
                a for a in grouped_actions[group_name] if a["path"] not in deleted_paths
            ]
        save_actions_to_json(grouped_actions)

    else:  # analyze mode
        updated_actions = {}
        for group_name, actions in grouped_actions.items():
            if not actions:
                continue
            updated_actions_list = []
            for action in actions:
                current_path = renamed_paths.get(action["path"], action["path"])
                if current_path in deleted_paths:
                    continue
                updated_action = {**action, "path": current_path}
                if action.get("new_path"):
                    updated_action["new_path"] = renamed_paths.get(
                        action["new_path"], action["new_path"]
                    )
                if group_name == "move_to_x":
                    updated_action["new_path"] = os.path.join(
                        MAIN_FOLDER, os.path.basename(current_path)
                    )
                updated_actions_list.append(updated_action)
            chosen_actions = get_group_choice(
                group_name, updated_actions_list, mode="analyze", deleted_paths=deleted_paths, renamed_paths=renamed_paths
            )
            updated_actions[group_name] = []
            for chosen_action in chosen_actions:
                if chosen_action:
                    if chosen_action["action"] == "move" and chosen_action["path"] in deleted_paths:
                        print(f"Skipped moving {chosen_action['path']}: already deleted")
                        continue
                    result = execute_action(chosen_action)
                    print(result)
                    updated_actions[group_name].append(chosen_action)
                    if result.startswith("Deleted:"):
                        deleted_paths.add(chosen_action["path"])
                    if result.startswith("Renamed:"):
                        renamed_paths[chosen_action["path"]] = chosen_action["new_path"]
                else:
                    updated_actions[group_name].append(
                        next(a for a in actions if a["path"] == chosen_action["path"])
                    )
            grouped_actions[group_name] = [
                a for a in grouped_actions[group_name] if a["path"] not in deleted_paths
            ]
        save_actions_to_json(updated_actions)

    print("Processing complete. Actions saved to actions.json.")

if __name__ == "__main__":
    main()