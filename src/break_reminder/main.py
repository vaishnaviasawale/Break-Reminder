import fcntl
import random
import tkinter as tk
from io import BytesIO
from pathlib import Path
import socket
import threading
from datetime import datetime, timedelta
import requests
from ddgs import DDGS
from PIL import Image, ImageTk

from break_reminder import config

WINDOW_WIDTH = 700
WINDOW_HEIGHT = 700

PROJECT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_DIR / "assets"

RUNTIME_DIR = Path.home() / ".config" / "break-reminder"
SOCKET_FILE = RUNTIME_DIR / "break-reminder.sock"
LOCK_FILE = RUNTIME_DIR / "break-reminder.lock"

FALLBACK_IMAGES = list(ASSETS_DIR.glob("fallback_*.png"))

XKCD_API = "https://xkcd.com/info.0.json"

TOPICS = [
    "beautiful landscapes",
    "seaside views",
    "European towns",
    "fairy illustrations",
    "puppies",
]

timer_id = None  # If a timer is already running and I start another timer,
# cancel the old timer. To keep track, we need a timer_id
timer_end_time = None
timer_status_label = None


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
    global timer_id
    global timer_end_time

    timer_id = None
    timer_end_time = None

    if not config.is_enabled():
        root.deiconify()  # Make window visible again
        return

    update_content()
    root.deiconify()


def start_timer():
    global timer_id  # Module-level variable
    global timer_end_time  # Several functions need access to this, so we make
    # it global

    if not config.is_enabled():
        return

    minutes_text = time_entry.get().strip()

    if not minutes_text:
        error_label.config(
            text="Please enter the number of minutes."
        )
        return

    try:
        minutes = int(minutes_text)
    except ValueError:
        # Value error because usually strings can be converted into ints
        # but this particular string does not represent an integer aka the
        # value is invalid
        # If it was something like int([1, 2, 3]) it would be a TypeError as
        # Python does not even know how to convert it into an int
        error_label.config(
            text="Please enter a whole number of minutes."
        )
        return

    if minutes <= 0:
        error_label.config(
            text="Please enter a number greater than 0."
        )
        return

    error_label.config(text="")

    if timer_id is not None:
        root.after_cancel(timer_id)

    timer_end_time = datetime.now() + timedelta(
        minutes=minutes,
    )

    milliseconds = minutes * 60 * 1000
    timer_id = root.after(
        milliseconds,
        timer_finished,
    )

    update_timer_display()
    refresh_timer_display()
    root.withdraw()
    # Do I need to return here? No, because Python has reached the end of
    # the function and returns automatically here (the function ends
    # immediately after this Except block)


def quit_app():
    global timer_id
    global timer_end_time

    if timer_id is not None:
        root.after_cancel(timer_id)
        timer_id = None

    timer_end_time = None

    # SOCKET_FILE.unlink(missing_ok=True)
    # Instead of using the socket itself as the rough indication of whether an
    # application existed, the lock file is responsible for ownership

    root.destroy()


def update_timer_display():
    # We only need global when assigning to the module-level variable.
    # Reading it doesn't require global.
    if timer_end_time is None:
        timer_status_label.config(text="")
        return

    remaining = timer_end_time - datetime.now()

    total_seconds = max(
        0,
        int(remaining.total_seconds()),
    )

    minutes, seconds = divmod(total_seconds, 60)

    break_time = timer_end_time.strftime("%I:%M %p").lstrip("0")

    timer_status_label.config(
        text=(
            f"Next break in {minutes}:{seconds:02d}\n"
            f"Break at {break_time}"
        )
    )


def refresh_timer_display():
    if timer_end_time is None:
        return

    update_timer_display()

    root.after(
        1000,
        refresh_timer_display,
    )


def start_command_server():
    thread = threading.Thread(
        target=handle_commands,
        daemon=True,
    )
    thread.start()


def show_window():
    root.deiconify()
    root.lift()
    root.focus_force()

    if timer_end_time is not None:
        update_timer_display()


def acquire_instance_lock():
    # The first GUI process obtains:
    # ~/.config/break-reminder/break-reminder.lock
    # and holds the lock for its entire lifetime.
    # If another GUI process tries:
    # fcntl.flock(... LOCK_NB)
    # It gets that the lock is already held and returns None

    # The fcntl module is a built-in Python library used to perform file
    # control and I/O control on file descriptors - the operating system
    # releases the lock automatically when the process exits so we don't
    # have to worry about old PID file, crashed process, etc
    RUNTIME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    lock_file = LOCK_FILE.open("w")

    try:
        fcntl.flock(
            lock_file,
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BlockingIOError:
        lock_file.close()
        return None

    return lock_file


def handle_commands():
    RUNTIME_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    SOCKET_FILE.unlink(missing_ok=True)

    server = socket.socket(
        socket.AF_UNIX,
        socket.SOCK_STREAM,
    )

    server.bind(str(SOCKET_FILE))
    server.listen(1)

    while True:
        connection, _ = server.accept()

        with connection:
            command = connection.recv(1024).decode()

        if command == "show":
            root.after(0, show_window)


def show_existing_app():
    try:
        with socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
        ) as sock:
            sock.settimeout(0.5)
            sock.connect(str(SOCKET_FILE))
            sock.sendall(b"show")
        return True
    except OSError:
        return False


def main():
    instance_lock = acquire_instance_lock()
    # Since instance_lock is a local variable in main() and main() doesn't
    # return until the GUI exits, it stays alive for the lifetime of the GUI

    if instance_lock is None:
        show_existing_app()
        return

    global root
    global instruction_label
    global image_label
    global time_entry
    global start_button
    global control_status_button
    global timer_status_label
    global error_label
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

    timer_status_label = tk.Label(
        root,
        font=("Sans", 16),
    )

    timer_status_label.pack(pady=10)

    error_label = tk.Label(
        root,
        text="",
        font=("Sans", 12),
    )

    error_label.pack(pady=5)

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

    start_command_server()
    refresh_timer_display()

    root.mainloop()


if __name__ == "__main__":
    main()
