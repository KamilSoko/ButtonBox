import board
import digitalio
import usb_hid
import neopixel
import rotaryio
import time
from time import sleep
from adafruit_logging import RotatingFileHandler
import adafruit_logging as logging

from hid_gamepad import Gamepad
from colours import *

l = logging.getLogger('test')
l.addHandler(RotatingFileHandler('log.txt', "a", 10000))
l.setLevel(logging.DEBUG)


# Button definitions
BTN_0_1 = 1
BTN_0_2 = 2
BTN_1_1 = 3
BTN_1_2 = 4
BTN_1_3 = 5
BTN_2_1 = 6
BTN_2_2 = 7
BTN_2_3 = 8
BTN_3_1 = 9
BTN_3_2 = 10
BTN_3_3 = 11
TOG_1_1 = 15
TOG_1_2 = 16
TOG_2_1 = 17
TOG_2_2 = 18
TOG_3_1 = 19
TOG_3_2 = 20
ENC_1 = 22
ENC_1_BTN_R = 23
ENC_1_BTN_L = 24
ENC_2 = 25
ENC_2_BTN_R = 26
ENC_2_BTN_L = 27

push_buttons = ((board.GP0, BTN_0_1), (board.GP1, BTN_0_2), (board.GP15, BTN_1_1), (board.GP5, BTN_1_2), (board.GP2, BTN_1_3), (board.GP16, BTN_2_1), (board.GP6, BTN_2_2), (board.GP3, BTN_2_3), (board.GP14, BTN_3_1), (board.GP7, BTN_3_2), (board.GP4, BTN_3_3))
rocker_buttons = ((board.GP8, TOG_1_1), (board.GP9, TOG_1_2), (board.GP10, TOG_2_1), (board.GP11, TOG_2_2), (board.GP12, TOG_3_1), (board.GP13, TOG_3_2))
encoder_buttons = ((board.GP19, ENC_1), (board.GP22, ENC_2))

COLOUR_CHANGE_BTN_IDX = 0  # ENC_1
LONG_PRESS_DURATION = 3.0  # seconds

# Brightness settings
BRIGHTNESS_STEP = 0.05
MIN_BRIGHTNESS = 0.05
MAX_BRIGHTNESS = 1.0
PRESET_FILE = "preset.txt"
BRIGHTNESS = 0.05
COLOUR = YELLOW

def log_debug(message):
    """Append debug message to log.txt file."""
    try:
        l.debug(message)
    except Exception as e:
        print(f"[ERROR] Logging failed: {e}")
#load preset if available
def save_preset(colour_idx, brightness):
    try:
        with open(PRESET_FILE, "w") as f:
            f.write(f"{colour_idx},{brightness}\n")
    except Exception as e:
        print(f"[ERROR] Failed to save preset: {e}")

def load_preset():
    try:
        with open(PRESET_FILE, "r") as f:
            line = f.readline()
            idx, bright = line.strip().split(",")
            return int(idx), float(bright)
    except Exception as e:
        print(f"[ERROR] Failed to load preset: {e}")
        return 0, 0.2  # fallback defaults

def detect_long_press(button_io, duration):
    """Returns True if button is held for 'duration' seconds."""
    if not button_io.value:
        print("[DEBUG] Button pressed, checking for long press...")
        start = time.monotonic()
        while not button_io.value:
            if time.monotonic() - start > duration:
                print(f"[DEBUG] Long press detected (> {duration}s)")

                return True
        print("[DEBUG] Button released before long press threshold.")
        return False
    return False

def colour_change_mode(pixels, encoder1, encoder2, current_colour_idx, current_brightness):
    """Allows cycling through colours using encoder."""
    print("[DEBUG] Entering colour change mode.")
    last_pos_1 = encoder1.position
    last_pos_2 = encoder2.position
    while True:
        pos_1 = encoder1.position
        if pos_1 != last_pos_1:
            if pos_1 > last_pos_1:
                current_colour_idx = (current_colour_idx + 1) % len(COLOUR_LIST)
                print(f"[DEBUG] Encoder_1 turned right. Colour index: {current_colour_idx}")
            else:
                current_colour_idx = (current_colour_idx - 1) % len(COLOUR_LIST)
                print(f"[DEBUG] Encoder_1 turned left. Colour index: {current_colour_idx}")
            pixels.fill(COLOUR_LIST[current_colour_idx])
            print(f"[DEBUG] LED colour changed to: {COLOUR_LIST[current_colour_idx]}")
            last_pos_1 = pos_1

        pos_2 = encoder2.position
        if pos_2 != last_pos_2:
            if pos_2 > last_pos_2:
                current_brightness = min(current_brightness + BRIGHTNESS_STEP, MAX_BRIGHTNESS)
                print(f"[DEBUG] Encoder_2 turned right. Brightness: {current_brightness:.2f}")
            else:
                current_brightness = max(current_brightness - BRIGHTNESS_STEP, MIN_BRIGHTNESS)
                print(f"[DEBUG] Encoder_2 turned left. Brightness: {current_brightness:.2f}")
            pixels.brightness = current_brightness
            last_pos_2 = pos_2
            
        pixels.show()
        # Exit mode if button released
        if encoder_buttons_IO[COLOUR_CHANGE_BTN_IDX].value:
            print("[DEBUG] Exiting colour change mode.")
            save_preset(current_colour_idx, current_brightness)
            break
        sleep(0.05)
    return current_colour_idx, current_brightness

def setup_buttons(button_tuples):
    print("[DEBUG] Setting up buttons...")
    btn_ios = []
    for pin, _ in button_tuples:
        btn = digitalio.DigitalInOut(pin)
        btn.direction = digitalio.Direction.INPUT
        btn.pull = digitalio.Pull.UP
        btn_ios.append(btn)
    print("[DEBUG] Buttons setup complete.")
    return btn_ios

def handle_buttons(button_ios, button_defs, gamepad):
    for i, btn in enumerate(button_ios):
        gamepad_btn = button_defs[i][1]
        if btn.value:
            gamepad.release_buttons(gamepad_btn)
        else:
            gamepad.press_buttons(gamepad_btn)
            print(f"[DEBUG] Button {gamepad_btn} state: {'released' if btn.value else 'pressed'}")

def setup_neopixels(pin, num_pixels, brightness, colour):
    print(f"[DEBUG] Setting up NeoPixels on pin {pin} with {num_pixels} pixels.")
    pixels = neopixel.NeoPixel(pin, num_pixels, brightness=brightness, auto_write=False)
    pixels.fill(colour)
    pixels.show()
    print(f"[DEBUG] Initial LED colour set to: {colour}")
    return pixels

def handle_encoder(encoder, last_pos, btn_l, btn_r, gamepad):
    pos = encoder.position
    if last_pos is None or pos != last_pos:
        print(f"[DEBUG] Encoder position changed: {pos}")
        if last_pos is None:
            if pos > 0:
                gamepad.press_buttons(btn_r)
                print(f"[DEBUG] Encoder initial position > 0, pressing button {btn_r}")
            else:
                gamepad.press_buttons(btn_l)
                print(f"[DEBUG] Encoder initial position <= 0, pressing button {btn_l}")
        elif last_pos > pos:
            gamepad.press_buttons(btn_l)
            print(f"[DEBUG] Encoder turned left, pressing button {btn_l}")
        else:
            gamepad.press_buttons(btn_r)
            print(f"[DEBUG] Encoder turned right, pressing button {btn_r}")
        sleep(0.05)
    return pos

def main():
    global l
    print("[DEBUG] Starting main function.")
    log_debug("Device started.")
    global encoder_buttons_IO  # Make it global to access in colour_change_mode
    push_buttons_IO = setup_buttons(push_buttons)
    log_debug("Push buttons initialized.")
    rocker_buttons_IO = setup_buttons(rocker_buttons)
    log_debug("Rocker buttons initialized.")
    encoder_buttons_IO = setup_buttons(encoder_buttons)
    log_debug("Encoder buttons initialized.")
    preset_colour_idx, preset_brightness = load_preset()
    log_debug(f"Loaded preset - Colour Index: {preset_colour_idx}, Brightness: {preset_brightness}")
    if 0 <= preset_colour_idx < len(COLOUR_LIST):
        COLOUR = COLOUR_LIST[preset_colour_idx]
        colour_idx = preset_colour_idx  # <-- ADD THIS
    else:
        colour_idx = 0  # <-- fallback
    if MIN_BRIGHTNESS <= preset_brightness <= MAX_BRIGHTNESS:
        BRIGHTNESS = preset_brightness
        brightness = preset_brightness  # <-- ADD THIS
    else:
        brightness = 0.2  # <-- fallback
        
    pixels = setup_neopixels(board.GP26, 8, BRIGHTNESS, COLOUR)
    log_debug("NeoPixels initialized.")

    encoder_1 = rotaryio.IncrementalEncoder(board.GP17, board.GP18)
    encoder_2 = rotaryio.IncrementalEncoder(board.GP20, board.GP21)
    encoder_1_last_pos = 0
    encoder_2_last_pos = 0
    log_debug("Encoders initialized.")

    gp = Gamepad(usb_hid.devices)
    log_debug("Gamepad initialized.")

    while True:
        sleep(0.01)
        gp.release_buttons(ENC_1_BTN_L, ENC_2_BTN_L, ENC_1_BTN_R, ENC_2_BTN_R)

        handle_buttons(push_buttons_IO, push_buttons, gp)
        handle_buttons(rocker_buttons_IO, rocker_buttons, gp)
        handle_buttons(encoder_buttons_IO, encoder_buttons, gp)

        encoder_1_last_pos = handle_encoder(encoder_1, encoder_1_last_pos, ENC_1_BTN_L, ENC_1_BTN_R, gp)
        encoder_2_last_pos = handle_encoder(encoder_2, encoder_2_last_pos, ENC_2_BTN_L, ENC_2_BTN_R, gp)
        
        # Check for long press on ENC_1
        if detect_long_press(encoder_buttons_IO[COLOUR_CHANGE_BTN_IDX], LONG_PRESS_DURATION):
            print("[DEBUG] Long press on ENC_1 detected, entering colour change mode.")
            colour_idx, brightness = colour_change_mode(pixels, encoder_1, encoder_2, colour_idx, pixels.brightness)

if __name__ == "__main__":
    main()