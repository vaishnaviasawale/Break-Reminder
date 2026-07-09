import tkinter as tk
import requests
from PIL import Image, ImageTk
from pathlib import Path
from io import BytesIO
import random

import config

TEST_DELAY_MS = 5000
WINDOW_WIDTH = 700
WINDOW_HEIGHT = 700

ASSETS_DIR = Path("assets")

FALLBACK_IMAGES = list(
    ASSETS_DIR.glob("fallback_*.png")
)

XKCD_API = "https://xkcd.com/info.0.json"

def get_image():
    try:
        response = requests.get(XKCD_API, timeout=5) # Download JSON
        response.raise_for_status() # Catches any errors early
        data = response.json()

        number = data["num"]

        # Choose a random comic
        comic_number = random.randint(1, number)
        comic_response = requests.get(
            f"https://xkcd.com/{comic_number}/info.0.json",
            timeout=5,
        )
        comic_response.raise_for_status()

        comic_data = comic_response.json()

        image_url = comic_data["img"]
        title = comic_data["title"]

        image_response = requests.get(
            image_url,
            timeout=5,
        )
        image_response.raise_for_status()

        # image_response.content is Raw Bytes
        # BytesIO pretends those bytes are in a file
        # .open() reads the JPEG
        image = Image.open(BytesIO(image_response.content))

    except requests.RequestException:
        fallback_image = random.choice(FALLBACK_IMAGES)
        image = Image.open(fallback_image)
        title = "Time for a break!"

    image.thumbnail((450, 300)) # Fit in the window
    photo = ImageTk.PhotoImage(image) # Converts Pillow's image into something Tkinter understands

    return photo, title



def disable_inputs():
    time_entry.config(state="disabled")
    start_button.config(state="disabled")

def enable_inputs():
    time_entry.config(state="normal")
    start_button.config(state="normal")

def update_content():
    photo, title = get_image()

    instruction_label.config(
        text=title,
        font=("Sans", 18, "bold"),
    )

    image_label.config(
        image=photo
    )

    image_label.image = photo
    # We are attaching a new attribute called image to the image_label object. In Python, most objects can have attributes added dynamically. By storing the PhotoImage there, we keep a reference to it alive. If we didn't, the local variable photo would disappear when update_content() returns, and Python's garbage collector could free the image, causing it to vanish from the window.

    # The actual image data still belongs to the PhotoImage object, Tkinter does not copy the pixels into the widget. This is unlike for quotes, where widget has its own copy of the string      (quote_label.config(text=get_quote())  

def timer_finished():
    if not config.is_enabled():
        return
    update_content()
    root.deiconify() # Make the window visible again
    enable_inputs()

def start_timer():
    if not config.is_enabled():
        return
    minutes_text = time_entry.get()

    try:
        minutes = int(minutes_text)
        if minutes <= 0:
            print("Not a valid number of minutes!")
            return

        print(f"Starting timer for {minutes} minutes")
        disable_inputs()
        root.withdraw() # Hide the window, but keep the program running
        milliseconds = minutes * 60 * 1000
        root.after(TEST_DELAY_MS, timer_finished)
        
    except ValueError as e:
        # Value error because usually strings can be converted into ints
        # but this particular string does not represent an integer aka the value is invalid
        # If it was something like int([1, 2, 3]) it would be a TypeError as 
        # Python does not even know how to convert it into an int
        print("Please enter a number! Error: ", e)
        # Do I need to return here? No, because Python has reached the end of the function and
        # returns automatically here (the function ends immediately after this Except block)

root = tk.Tk()
root.title("Time for a break!")
root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

instruction_label = tk.Label(root, font=("Sans", 20, "bold"),)
instruction_label.pack(padx=20, pady=20)

image_label = tk.Label(root)
image_label.pack(pady=15)

instruction = tk.Label(root, text="How many minutes until the next break?")
instruction.pack(pady=10)

time_entry = tk.Entry(root)
time_entry.pack()

start_button = tk.Button(root, text="Start Timer", command=start_timer)
# We skip the parenthesis when calling start_timer as we don't want to execute it immediately
# This is unline the way we use get_quote or get_image since we need to execute those function
# immediately and use their values
start_button.pack(pady=20)

root.mainloop()
