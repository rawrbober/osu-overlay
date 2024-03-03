import tkinter as tk
import tkinter.font as tkFont
from pynput.mouse import Listener as MouseListener
import keyboard
import requests
import win32con
import win32gui
import win32api
import pyperclip
import os
from scan_for_start import scan_for_start

class OsuOverlay:
    def __init__(self, DT, HR, EZ):
        # These are the in-game mods
        self.DT = DT
        self.HR = HR
        self.EZ = EZ

        # Don't touch these, core overlay components
        self.mouse_x, self.mouse_y = 0, 0
        self.circle_objects = {}
        self.canvas = None
        self.start_flag = False
        self.root = None
        self.listener = None
        self.is_closing = False
        self.scheduled_tasks = []
        
        # Both of these will be changed based on map values automatically
        self.circle_removal_delay = 400
        self.circle_size = 4

# Make a semi-transparent click-through window.
    def set_click_through(self, hwnd):
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        new_style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        # 1,2,3 = RGB, 4 = Overlay opacity       <-            1   2   3    4
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(99, 99, 99), 90, win32con.LWA_ALPHA)

# So that it doesn't minimize when osu is interacted with
    def keep_on_top(self):
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.scheduled_tasks.append(self.root.after(100, self.keep_on_top))

    def cancel_scheduled_tasks(self):
        while self.scheduled_tasks:
            task_id = self.scheduled_tasks.pop()
            self.root.after_cancel(task_id)

    def mouse_move(self, x, y):
        self.mouse_x, self.mouse_y = x, y

    def remove_circle(self, circle_id):
        if self.canvas:
            self.canvas.delete(circle_id)
            self.circle_objects.pop(circle_id, None)

    def draw_circle(self, x, y, object_type):
        if self.canvas:
            # Draw color according to the object type (slider or hitcircle)
            fill_color = 'green' if object_type == 'slider' else 'pink'
            # Draw circled the proper size, taken from get_stats
            circle_id = self.canvas.create_oval(x - self.circle_size, y - self.circle_size, x + self.circle_size, y + self.circle_size, fill=fill_color)
            self.circle_objects[circle_id] = {'x': x, 'y': y}
            self.scheduled_tasks.append(self.root.after(self.circle_removal_delay, lambda: self.remove_circle(circle_id)))

# Checks for mouse collision in order to remove circles that have been hit
    def check_interaction(self):
        if not self.EZ:
            to_remove = [circle_id for circle_id, info in self.circle_objects.items()
                        if ((self.mouse_x - info['x']) ** 2 + (self.mouse_y - info['y']) ** 2) ** 0.5 < 30]
            for circle_id in to_remove:
                self.remove_circle(circle_id)
            self.scheduled_tasks.append(self.root.after(10, self.check_interaction))

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')


    def draw_mods(self, x_offset=35, y_offset=40, size=40, color='white', duration=2500):
        if self.canvas:
            # Define the mods
            modlist = ""
            if self.DT:
                modlist = modlist + "DT "
            if self.HR:
                modlist = modlist + "HR "
            if self.EZ:
                modlist = modlist + "EZ "

            # Create a Tkinter font
            font = tkFont.Font(size=size)
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            # Calculate text position (top right corner)
            text_x = canvas_width - x_offset
            text_y = y_offset
            # Create text on the canvas
            text_id = self.canvas.create_text(text_x, text_y, text=modlist, anchor="ne", fill=color, font=font)
            # Schedule the text to be removed after 'duration' milliseconds
            self.root.after(duration, lambda: self.canvas.delete(text_id))
        


    # Basic parser for beatmap stats
    def get_stats(self, text) -> int:
        # Separate into sections
        sections = text.split('\n\n')
        # Find the difficulty section
        for section in sections:
            if '[Difficulty]' in section:
                # Split into lines
                lines = section.split('\n')
                for line in lines:
                    # Get the circle size (CS)
                    if 'CircleSize:' in line:
                        # Osu pixel from CS formula -> Radius in pixels = 109 - (9*CS)
                        # Calculate CS
                        self.circle_size = float(line.split(':')[1].strip())
                        # Adjust for mods, PS: HR and EZ can not be ran at the same time in-game
                        if self.HR:
                            self.circle_size = self.circle_size * 1.3
                        elif self.EZ:
                            self.circle_size = self.circle_size / 2
                        # Use the CS -> pixel formula to get the circle radius in pixels for draw_circle
                        self.circle_size = self.circle_size = int(109 - (9 * self.circle_size))
                    if 'ApproachRate:' in line:
                        # Extract and return the ApproachRate value
                        AR = float(line.split(':')[1].strip())
                        # AR calculation formulas + mods interactions:
                        if self.HR:
                            AR = AR * 1.4
                            if AR > 10:
                                AR = 10
                        elif self.EZ:
                            AR = AR/2
                        if AR < 5:
                            preempt = 1200 + 600 * (5 - AR) / 5
                        if AR == 5:
                            preempt = 1200
                        if AR > 5:
                            preempt = 1200 - 750 * (AR - 5) / 5
                        if self.DT:
                            preempt =  int(preempt*(2/3))
                        if preempt > 300:
                            return int(preempt)
                        else:
                            # Osu's max applicable AR is 11 (300ms)
                            return(300)

# Parsing beatmap info into coords and delay and putting them into an array, gets displayed over time
# Gets the approach rate from beatmap info, modifies existing delay to the new accurate one.
    def load_circle_info(self):
        mapID = pyperclip.paste().split("beatmaps/")[1]
        response = requests.get(f"https://osu.ppy.sh/osu/{mapID}").text
        # Set the removal timing to the map approach rate
        self.circle_removal_delay = self.get_stats(response)
        circles_info = [(int(int(components[0]) * 2.25 + 384), int(int(components[1]) * 2.25 + 126), int(components[2]), 'slider' if len(components) > 6 else 'circle') for components in (line.split(',') for line in response.split("[HitObjects]")[1].split("\n")[1:-1]) if len(components) > 2]
        if circles_info:
            # Add 20ms to the initial delay (pixel scanning the start adds delay inaccuracy)
            initial_delay = (circles_info[0][2])+20
            # If the map starts with a spinner the pixel scanning is delayed, this accounts for it
            if int(str(response.split("[HitObjects]")[1].split("\n")[1:-1][0]).count(",")) == 6:
                initial_delay += 70
            # Adjust speed and HR circle inversion
            if self.DT and self.HR:
                circles_info = [(x, 1090-y, int(delay/1.5 - (initial_delay/1.5)), object_type) for x, y, delay, object_type in circles_info]
            # Adjust speed 
            elif self.DT:
                circles_info = [(x, y, int(delay/1.5 - (initial_delay/1.5)), object_type) for x, y, delay, object_type in circles_info]
            # Adjust for x-axis inversion
            elif self.HR:
                circles_info = [(x, 1090-y, delay - initial_delay, object_type) for x, y, delay, object_type in circles_info]
            # If no mods:
            else:
                circles_info = [(x, y, delay - initial_delay, object_type) for x, y, delay, object_type in circles_info]
        return circles_info

    # When the user restarts the map by holding "`"
    def reset_game(self):
        # Reset the canvas contents without closing the canvas
        self.cancel_scheduled_tasks()
        self.start_flag = False
        self.circle_objects.clear()
        if self.canvas:
            self.canvas.delete("all")

    # We're in-game, start drawing
    def start_sequence(self):
        self.clear_screen()
        print("Started")
        for x, y, delay, object_type in self.circles_info:
            self.scheduled_tasks.append(self.root.after(max(0, delay), lambda x=x, y=y, object_type=object_type: self.draw_circle(x, y, object_type)))

    # Stop drawing and clear canvas, usually called by pressing escape to find a new map/quit
    def close_canvas(self):
        if self.root and not self.is_closing:
            self.is_closing = True
            self.cancel_scheduled_tasks()
            if self.canvas:
                self.canvas.delete("all")
            self.circle_objects.clear()
            if self.listener:
                self.listener.stop()
                self.listener = None
            def safely_close():
                if self.root:
                    self.root.quit()
                    self.root.destroy()
                    self.root = None
                self.is_closing = False
                self.start_flag = False
            self.root.after(0, safely_close)
        elif not self.root:
            self.is_closing = False
            self.start_flag = False

    def on_key_press(self, event):
        # Press enter to start the first hitobject scanning (this is also the hotkey to start a map in osu)
        # Automatic start. Will start at the wrong time if the user hovers over the initial position with their cursor in osu.
        if event.name == 'enter' and not self.start_flag and self.root:
            # Load circle data
            self.circles_info = self.load_circle_info()
            print("Scanning for first hitobject")
            self.draw_mods()
            # Scan for the first hitcircle to appear (pauses code until it appears)
            scan_for_start(1, self.HR)
            # Start the sequence once it's detected
            self.start_flag = True
            self.start_sequence()
        elif event.name == '`' and self.root:
            # ` is the default hotkey to restart a map in osu, we reset the canvas and drawing timers
            self.reset_game()
            print("Resetting game")
            # Sometimes the map doesn't fully fade to black on resets, added pixel range to correct that
            scan_for_start(31, self.HR)
            print("Starting sequence")
            self.start_sequence()
        elif event.name == 'esc':
            if self.start_flag == True:
                print("Closing canvas and waiting for reinitialization")
            self.close_canvas()
            self.clear_screen()

    def initialize_script(self):
        # Initialize canvas
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.root.update()

        # Make the window seethrough and clickthrough (overlay)
        self.set_click_through(win32gui.FindWindow(None, self.root.title()))
        self.keep_on_top()

        # Initialize mouse position tracking for collision detection
        self.listener = MouseListener(on_move=self.mouse_move)
        self.listener.start()

        # Initialize hotkeys
        keyboard.on_press(self.on_key_press)
        self.check_interaction()
        self.root.mainloop()