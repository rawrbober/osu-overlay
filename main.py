from overlay import OsuOverlay
from get_ID_and_mods import GetStart
import keyboard
import time
from manualdata import mandata

TIME_TO_SLEEP = 0.03
SONG_PATH = "D:/osu!/Songs"

 
def main():
    # Main function to run the application loop
    while True:
        keyboard.unhook_all()
        handler = GetStart(TIME_TO_SLEEP, SONG_PATH)
        mods = handler.start_hotkeys()
        data = handler.get_map_data()
        time.sleep(1)
        print("Throwing it into overlay")
        overlay = OsuOverlay(data,mods)
        overlay.initialize_script()


if __name__ == '__main__':
    main()

