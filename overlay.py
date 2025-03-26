import tkinter as tk
import tkinter.font as tkFont
from pynput.mouse import Listener as MouseListener
import keyboard
import win32con
import win32gui
import win32api
from scan_for_start import scan_for_start
import time
import os


class OsuOverlay:
    def __init__(self, mapdata, modstring):
        # These are the in-game mods
        self.DT = False
        self.HR = False
        self.EZ = False
        self.HT = False
        self.HD = False
        self.FL = False
        # Selected mods list from get_ID_and_mods
        self.modstring = modstring
        self.mapdata = mapdata
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
        self.sliderfill = 'gray18'
        self.draw_approach = True


# Make a semi-transparent click-through window.
    def set_click_through(self, hwnd):
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        new_style = style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_style)
        # Make the overlay higher opacity for EZ, otherwise it gets confusing in-game
        if self.EZ:
            win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(99, 99, 99), 180, win32con.LWA_ALPHA)
        else:
            win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(99, 99, 99), 60, win32con.LWA_ALPHA)


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


    def draw_circle(self, x, y, object_type, sliderend):
        if self.canvas:
            fill_color = 'green' if object_type == 'slider' else 'red'

            def draw_rectangle_between_circles(x1, y1, x2, y2):
                width = self.circle_size
                dx, dy = x2 - x1, y2 - y1
                length = (dx ** 2 + dy ** 2) ** 0.5
                if length == 0:
                    length = 1
                dx, dy = dx / length, dy / length
                px, py = -dy * width, dx * width
                corners = [x1 + px, y1 + py, x2 + px, y2 + py, x2 - px, y2 - py, x1 - px, y1 - py]
                rectangle_id = self.canvas.create_polygon(corners, fill=self.sliderfill)
                self.scheduled_tasks.append(self.root.after(self.circle_removal_delay, lambda: self.canvas.delete(rectangle_id)))
                return rectangle_id

            if sliderend:
                if self.HR:
                    adjusted_slider_points = [(int(point[0]) * 2.25 + 384, 1116 - (int(point[1]) * 2.25 + 126)) for point in sliderend]
                else:
                    adjusted_slider_points = [(int(point[0]) * 2.25 + 384, int(point[1]) * 2.25 + 126) for point in sliderend]
                points_to_draw = (
                    [(x, y)] + adjusted_slider_points
                    if len(adjusted_slider_points) > 1
                    else [(x, y), adjusted_slider_points[0]] if adjusted_slider_points else []
                )

                for i in range(len(points_to_draw) - 1):
                    x1, y1 = points_to_draw[i]
                    x2, y2 = points_to_draw[i + 1]
                    draw_rectangle_between_circles(x1, y1, x2, y2)

                for point in adjusted_slider_points:
                    drawn_slider_end = self.canvas.create_oval(
                        point[0] - self.circle_size,
                        point[1] - self.circle_size,
                        point[0] + self.circle_size,
                        point[1] + self.circle_size,
                        fill=self.sliderfill,
                        outline=self.sliderfill
                    )
                    self.circle_objects[drawn_slider_end] = {'x': point[0], 'y': point[1]}
                    self.scheduled_tasks.append(
                        self.root.after(self.circle_removal_delay, lambda drawn_slider_end=drawn_slider_end: self.remove_circle(drawn_slider_end))
                    )

            # Draw the approach circle animation.
            # Set the initial approach radius using a multiplier (adjust as needed).
            if self.draw_approach:
                approach_multiplier = 3.0
                initial_approach_radius = self.circle_size * approach_multiplier

                # Create the approach circle first so it lies behind the hit circle.
                approach_circle_id = self.canvas.create_oval(
                    x - initial_approach_radius,
                    y - initial_approach_radius,
                    x + initial_approach_radius,
                    y + initial_approach_radius,
                    outline='white',
                    width=12
                )
                # Ensure the approach circle is deleted when its time is up.
                self.scheduled_tasks.append(self.root.after(self.circle_removal_delay, lambda: self.canvas.delete(approach_circle_id)))
                # Animate the approach circle shrinking.
                start_time = time.time()
                def update_approach_circle():
                    elapsed = time.time() - start_time
                    total_duration = self.circle_removal_delay / 1000.0  # convert ms to seconds
                    progress = min(elapsed / total_duration, 1)
                    # Linear interpolation: when progress=0, radius is initial; when progress=1, radius equals self.circle_size.
                    new_radius = self.circle_size + (initial_approach_radius - self.circle_size) * (1 - progress)
                    self.canvas.coords(approach_circle_id, x - new_radius, y - new_radius, x + new_radius, y + new_radius)
                    if progress < 1:
                        self.root.after(1, update_approach_circle)
                update_approach_circle()

            # Draw the hit circle on top of the approach circle.
            circle_id = self.canvas.create_oval(
                x - self.circle_size,
                y - self.circle_size,
                x + self.circle_size,
                y + self.circle_size,
                fill=fill_color
            )
            self.circle_objects[circle_id] = {'x': x, 'y': y}
            self.scheduled_tasks.append(self.root.after(self.circle_removal_delay, lambda: self.remove_circle(circle_id)))


# Checks for mouse collision in order to remove circles that have been hit
    def check_interaction(self):
        if not self.EZ:
            to_remove = [circle_id for circle_id, info in self.circle_objects.items()
                        if ((self.mouse_x - info['x']) ** 2 + (self.mouse_y - info['y']) ** 2) ** 0.5 < self.circle_size]
            for circle_id in to_remove:
                self.remove_circle(circle_id)
            self.scheduled_tasks.append(self.root.after(10, self.check_interaction))


    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')


    def update_mods(self, mods_status):
        # Update the mods based on the dictionary provided
        for mod, status in mods_status.items():
            if hasattr(self, mod):
                setattr(self, mod, status)


    def modstring_parse(self):
        mods = {"DT": False, "HR": False, "HD": False, "FL": False, "HT": False, "EZ": False}
        mod_list = self.modstring.split()
        # Update mods based on their occurrences
        for mod in mod_list:
            if mod == "DT":
                # Account for NC being enabled if DT is pressed twice
                mods[mod] = not (mod_list.count(mod) % 3 == 0)
            else:
                mods[mod] = mod_list.count(mod) % 2 != 0
        # Some mods disable each other, integrating logic for that
        last_occurrences = {mod: i for i, mod in enumerate(mod_list) if mod in mods}
        # HR vs EZ logic
        if 'HR' in last_occurrences and 'EZ' in last_occurrences:
            if last_occurrences['HR'] > last_occurrences['EZ']:
                mods['HR'] = True
                mods['EZ'] = False
            else:
                mods['HR'] = False
                mods['EZ'] = True
        # DT vs HT logic
        if 'DT' in last_occurrences and 'HT' in last_occurrences:
            if last_occurrences['DT'] > last_occurrences['HT']:
                mods['DT'] = True
                mods['HT'] = False
            else:
                mods['DT'] = False
                mods['HT'] = True

        self.update_mods(mods)


    def draw_mods(self, x_offset=35, y_offset=200, size=40, color='white', duration=2500):
        if self.canvas:
            mods = ['DT', 'HR', 'EZ', 'HT', 'HD', 'FL']
            active_mods = [mod for mod in mods if getattr(self, mod, False)]
            modlist = ' '.join(active_mods) + ' '
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
        print("getting stats")
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
    

    def extract_slider_points(self, slider_type, slider_data):
        points = slider_data.split('|')
        # L = straight slider, P = curved slider
        extracted_points = [tuple(map(int, point.split(':'))) for point in points[1:]]
        return extracted_points
    

    def extract_info(self,components):
        x = int(int(components[0]) * 2.25 + 384)
        y = int(int(components[1]) * 2.25 + 126)
        delay = int(components[2])
        object_type = 'slider' if len(components) > 6 else 'circle'
        slider_data = components[5]
        if object_type == 'slider':
            slider_type = slider_data.split('|')[0]
            # Extract slider points based on the type.
            if ":" in slider_data:
                slider_points = self.extract_slider_points(slider_type, slider_data)
            else:
                slider_points = None
        else:
            slider_points = None
        return (x, y, delay, object_type, slider_points)
    

    # Parsing beatmap info into coords and delay and putting them into an array, gets displayed over time
    # Gets the approach rate from beatmap info, modifies existing delay to the new accurate one.
    def load_circle_info(self):
        # Set the removal timing to the map approach rate
        self.circle_removal_delay = self.get_stats(self.mapdata)
        circles_info = [
            self.extract_info(components)
            for components in (line.split(',') for line in self.mapdata.split("[HitObjects]")[1].split("\n")[1:-1])
            if len(components) > 2
        ]
        if circles_info:
            # Add 20ms to the initial delay (pixel scanning the start adds delay inaccuracy)
            initial_delay = (circles_info[0][2])+20
            if self.EZ:
                initial_delay -= self.circle_removal_delay
                initial_delay += 450
                self.circle_removal_delay = 450
            # If the map starts with a spinner the pixel scanning is delayed, this accounts for it
            if int(str(self.mapdata.split("[HitObjects]")[1].split("\n")[1:-1][0]).count(",")) == 6:
                initial_delay += 70
            # Adjust speed and HR circle inversion
            if self.DT and self.HR:
                circles_info = [(x, 1116-y, int(delay/1.5 - (initial_delay/1.5)), object_type, sliderend) for x, y, delay, object_type, sliderend in circles_info]
            # Adjust speed 
            elif self.DT:
                circles_info = [(x, y, int(delay/1.5 - (initial_delay/1.5)), object_type, sliderend) for x, y, delay, object_type, sliderend in circles_info]
            # Adjust for x-axis inversion
            elif self.HR:
                circles_info = [(x, 1116-y, delay - initial_delay, object_type, sliderend) for x, y, delay, object_type, sliderend in circles_info]
            # If no mods:
            else:
                circles_info = [(x, y, delay - initial_delay, object_type, sliderend) for x, y, delay, object_type, sliderend in circles_info]
        return circles_info


    # When the user restarts the map by holding "`"
    def reset_game(self):
        print("Resetting game")
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
        for x, y, delay, object_type, sliderend in self.circles_info:
            self.scheduled_tasks.append(self.root.after(max(0, delay), lambda x=x, y=y, object_type=object_type, sliderend=sliderend: self.draw_circle(x, y, object_type, sliderend)))

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
        print("started onkeypress")
        # Press enter to start the first hitobject scanning (this is also the hotkey to start a map in osu)
        # Automatic start. Will start at the wrong time if the user hovers over the initial position with their cursor in osu.
        if event.name == '`' and self.root:
            # ` is the default hotkey to restart a map in osu, we reset the canvas and drawing timers
            self.reset_game()
            print("Resetting game")
            time.sleep(0.5)
            # Sometimes the map doesn't fully fade to black on resets, added pixel range to correct that
            if self.EZ:
                scan_for_start(13, self.HR, self.mapdata)
            else:
                scan_for_start(60, self.HR, self.mapdata)
            print("Starting sequence")
            self.start_sequence()
        elif event.name == 'esc':
            if self.start_flag == True:
                print("Closing canvas and waiting for reinitialization")
            self.close_canvas()
            self.clear_screen()
            keyboard.unhook_all()


    def initialize_script(self):
        # Initialize canvas
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.root.update()
        # Parse mods
        self.modstring_parse()
        # Make the window seethrough and clickthrough (overlay)
        self.set_click_through(win32gui.FindWindow(None, self.root.title()))
        self.keep_on_top()

        # Initialize mouse position tracking for collision detection
        self.listener = MouseListener(on_move=self.mouse_move)
        self.listener.start()

        # Initialize hotkeys
        if not self.start_flag and self.root:
            # Load circle data
            self.circles_info = self.load_circle_info()
            self.draw_mods()
            # Scan for the first hitcircle to appear (pauses code until it appears)
            scan_for_start(1, self.HR, self.mapdata)
            # Start the sequence once it's detected
            self.start_flag = True
            self.start_sequence()
        keyboard.on_press(self.on_key_press)
        self.root.mainloop()
        self.check_interaction()
