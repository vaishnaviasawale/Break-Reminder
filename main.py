import random
import tkinter as tk
from io import BytesIO
from pathlib import Path

import requests
from ddgs import DDGS
from PIL import Image, ImageTk

import config

WINDOW_WIDTH = 700
WINDOW_HEIGHT = 700

PROJECT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_DIR / "assets"

FALLBACK_IMAGES = list(ASSETS_DIR.glob("fallback_*.png"))

XKCD_API = "https://xkcd.com/info.0.json"

TOPICS = [
    "beautiful landscapes",
    "seaside views",
    "European towns",
    "fairy illustrations",
    "puppies",
]


def get_xkcd_image():
    response = requests.get(XKCD_API, timeout=5)  # Download JSON
    response.raise_for_status()  # Catches any errors early
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

    return image, title


def get_duckduckgo_image(topic):
    results = list(
        DDGS().images(
            topic,
            max_results=1,
        )
    )

    if not results:
        raise RuntimeError("No images found")

    image_url = results[0]["image"]

    response = requests.get(
        image_url,
        timeout=5,
    )
    response.raise_for_status()

    image = Image.open(BytesIO(response.content))

    return image, topic


def get_fallback_image():
    if not FALLBACK_IMAGES:
        return None
    # If no fallback image exists, show only the text

    fallback_image = random.choice(FALLBACK_IMAGES)

    return Image.open(fallback_image), "Time for a break!"


def get_image():
    try:
        sources = ["xkcd"] + TOPICS
        source = random.choice(sources)

        if source == "xkcd":
            image, title = get_xkcd_image()
        else:
            image, title = get_duckduckgo_image(source)

    except (requests.RequestException, RuntimeError, OSError):
        fallback = get_fallback_image()

        if fallback is None:
            return None, "Time for a break!"

        image, title = fallback

    image.thumbnail((450, 300))

    photo = ImageTk.PhotoImage(image)

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

    if photo is None:
        image_label.config(image="")
        image_label.image = None
        return

    image_label.config(image=photo)

    image_label.image = photo
    # We are attaching a new attribute called image to the image_label object.
    # In Python, most objects can have attributes added dynamically. By
    # storing the PhotoImage there, we keep a reference to it alive. If we
    # didn't, the local variable photo would disappear when update_content()
    # returns, and Python's garbage collector could free the image, causing it
    # to vanish from the window.

    # The actual image data still belongs to the PhotoImage object, Tkinter
    # does not copy the pixels into the widget. This is unlike for quotes,
    # where widget has its own copy of the string
    # (quote_label.config(text=get_quote())


def update_control_button():
    if config.is_enabled():
        control_status_button.config(text="Disable Reminder")
    else:
        control_status_button.config(text="Enable Reminder")


def toggle_enabled():
    if config.is_enabled():
        config.disable()
    else:
        config.enable()

    update_control_button()


def timer_finished():
    if not config.is_enabled():
        root.deiconify()  # Make window visible again
        enable_inputs()
        return

    update_content()
    root.deiconify()
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
        root.withdraw()  # Hide the window, but keep the program running
        milliseconds = minutes * 60 * 1000
        root.after(milliseconds, timer_finished)

    except ValueError as e:
        # Value error because usually strings can be converted into ints
        # but this particular string does not represent an integer aka the
        # value is invalid
        # If it was something like int([1, 2, 3]) it would be a TypeError as
        # Python does not even know how to convert it into an int
        print("Please enter a number! Error: ", e)
        # Do I need to return here? No, because Python has reached the end of
        # the function and returns automatically here (the function ends
        # immediately after this Except block)


def quit_app():
    root.destroy()


def main():
    global root
    global instruction_label
    global image_label
    global time_entry
    global start_button
    global control_status_button
    # These variables existed at a module level - when moved inside main,
    # they become local to main(). The global declarations tell Python:
    # "These variables belong to the module; make them available to the other
    # functions too."

    root = tk.Tk()
    root.title("Time for a break!")
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
    root.protocol("WM_DELETE_WINDOW", quit_app)

    instruction_label = tk.Label(
        root,
        font=("Sans", 20, "bold"),
    )
    instruction_label.pack(padx=20, pady=20)

    image_label = tk.Label(root)
    image_label.pack(pady=15)

    instruction = tk.Label(root, text="How many minutes until the next break?")
    instruction.pack(pady=10)

    time_entry = tk.Entry(root)
    time_entry.pack()

    start_button = tk.Button(root, text="Start Timer", command=start_timer)
    # We skip the parenthesis when calling start_timer as we don't want to
    # execute it immediately
    # This is unline the way we use get_quote or get_image since we need to
    # execute those function immediately and use their values
    start_button.pack(pady=20)

    control_status_button = tk.Button(
        root,
        command=toggle_enabled,
    )

    control_status_button.pack(pady=10)

    update_control_button()

    root.mainloop()


if __name__ == "__main__":
    main()
