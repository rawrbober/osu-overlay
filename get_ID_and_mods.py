import win32api, win32con
import pygetwindow as gw
import keyboard
import win32gui
import time
import os 


class GetStart:
    def __init__(self, time_to_sleep, directory_path):
        self.directory_path = directory_path
        self.time_to_sleep = time_to_sleep
        self.mods = ""
        self.last_hotkey_pressed = 9


    def get_last_press(self):
        while True:
            hotkey_state = win32api.GetKeyState(0x70)
            if hotkey_state == 0 or hotkey_state == 1:
                self.last_hotkey_pressed = hotkey_state
                break


    def press_key_1(self):
        win32api.keybd_event(ord('1'), 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(ord('1'), 0, win32con.KEYEVENTF_KEYUP, 0)


    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')


    def check_focus(self):
        if win32gui.GetWindowText(win32gui.GetForegroundWindow()) == "osu!":
            return True
        return False


    def mod_selection(self):
        print(self.last_hotkey_pressed)
        self.clear_screen()
        print("Mod selection opened")
        print("Use keys to select mods (D,F,H) -> DT HD FL for example")
        print("Once you're done exit with esc, 2, for F1")
        time.sleep(0.03)
        # Clear in-game mods
        self.press_key_1()
        self.get_last_press()
        while True:
            if self.check_focus():
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    mod_map = {
                        'q': " EZ ",
                        'e': " HT ",
                        'a': " HR ",
                        'd': " DT ",
                        'f': " HD ",
                        'g': " FL "
                    }
                    
                    if event.name in mod_map:
                        self.mods += mod_map[event.name]
                    elif event.name in {"f1", "esc", "2"}:
                        self.clear_screen()
                        self.get_last_press()
                        return self.mods


    def start_hotkeys(self):
        self.clear_screen()
        print("F1 to change mods\n")
        print("Make sure osu is in focus and you have your browser open.")
        while True:
            if self.check_focus():
                event = keyboard.read_event()
                if event.event_type == keyboard.KEY_DOWN:
                    if event.name == 'f1':
                        self.mods = self.mod_selection()
                        return self.mods
        

    def _get_active_map_name(self):
        # Get map name form active window
        print("Getmap running")
        self.get_last_press()
        while True:
            if win32api.GetKeyState(0x70) == self.last_hotkey_pressed:
                active_window = gw.getActiveWindow()
                if active_window and len(active_window.title) > 4 and "osu!" in active_window.title:
                    return active_window.title
            else:
                self.mod_selection()
            

    def _find_map_directory(self, map_name):
        # Find map in directory
        matching_folders = []
        try:
            for entry in os.scandir(self.directory_path):
                if entry.is_dir():
                    folder_path = os.path.join(self.directory_path, entry.name)
                    for sub_entry in os.scandir(folder_path):
                        if sub_entry.is_file() and map_name in sub_entry.name:
                            matching_folders.append(entry.name)
                            break
            return os.path.join(self.directory_path, matching_folders[0]) if matching_folders else None
        except Exception as e:
            print(f"Error: {e}")
            return None
    

    def _parse_map_data(self, name):
        #Get map name and difficulty from window title"""
        cleaned = name.split("osu!  - ")[1]
        map_name = cleaned.split(" [")[0]
        difficulty = cleaned.split(" [")[1]
        print(f'Map: {map_name} | Diff: [{difficulty}')
        return map_name, difficulty
    

    def _read_osu_file(self, map_path, diff_name):
        #Read map file from directory
        try:
            for entry in os.scandir(map_path):
                if entry.name.endswith('.osu') and diff_name in entry.name:
                    with open(entry.path, 'r', encoding='utf-8') as f:
                        return f.read()
            print("No matching .osu file found.")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None


    def get_map_data(self):
        window_title = self._get_active_map_name()
        map_name, difficulty = self._parse_map_data(window_title)
        map_path = self._find_map_directory(map_name)
        if not map_path:
            print("No map directory found")
            return None
        
        print("Getmap done")
        return self._read_osu_file(map_path, difficulty)
