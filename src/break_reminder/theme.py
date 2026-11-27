"""The look of the window: a cream card on a painted pastel background."""

import random
import tkinter as tk

from PIL import Image, ImageDraw, ImageFilter, ImageTk

# The window is a square of this size, and only grows taller when the content
# (a picture) doesn't fit
WINDOW_SIZE = 760
MARGIN = 44  # Painted border visible around the card

CREAM = "#fdf8f1"
BLUSH = "#f4d3d9"
BLUSH_DARK = "#eab9c4"
POWDER = "#d6e4ee"
POWDER_DARK = "#bdd2e2"
GOLD = "#c2a060"
INK = "#5b4650"
ROSE = "#a0405c"

SCRIPT_FONT = ("Z003", 21)
BODY_FONT = ("P052", 13)
SMALL_FONT = ("P052", 11, "italic")
COUNTDOWN_FONT = ("P052", 15, "italic")
ENTRY_FONT = ("P052", 16)

LABEL_STYLE = {"bg": CREAM, "fg": INK}


def button_style(color, active_color):
    return {
        "font": BODY_FONT,
        "bg": color,
        "fg": INK,
        "activebackground": active_color,
        "activeforeground": INK,
        "disabledforeground": "#a8979d",
        "relief": tk.FLAT,
        "borderwidth": 0,
        "highlightthickness": 1,
        "highlightbackground": GOLD,
        "highlightcolor": GOLD,
        "padx": 22,
        "pady": 4,
        "cursor": "hand2",
    }


def draw_sparkle(draw, x, y, radius, color):
    waist = radius / 5
    draw.polygon(
        [
            (x, y - radius),
            (x + waist, y - waist),
            (x + radius, y),
            (x + waist, y + waist),
            (x, y + radius),
            (x - waist, y + waist),
            (x - radius, y),
            (x - waist, y - waist),
        ],
        fill=color,
    )


def draw_butterfly(draw, x, y, size, color):
    # Two large upper wings, two small lower wings and a thin body
    for side in (-1, 1):
        for width, top, bottom in ((1.0, -0.8, 0.1), (0.7, 0.0, 0.7)):
            left, right = sorted((x, x + side * width * size))
            draw.ellipse(
                (left, y + top * size, right, y + bottom * size),
                fill=color,
                outline=(194, 160, 96, 255),
                width=2,
            )
    draw.line(
        (x, y - 0.5 * size, x, y + 0.5 * size),
        fill=(122, 94, 80, 255),
        width=3,
    )


def paint_background(width, height):
    # A fixed seed, so the painting looks the same every time
    rng = random.Random(7)
    image = Image.new("RGBA", (width, height), (250, 238, 232, 255))

    washes = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(washes)
    colors = [
        (240, 180, 196, 170),  # blush
        (170, 200, 228, 170),  # powder blue
        (204, 188, 228, 150),  # lilac
        (186, 214, 190, 130),  # sage
        (250, 214, 170, 140),  # peach
    ]
    for index in range(90):
        x = rng.randrange(width)
        y = rng.randrange(height)
        radius = rng.randrange(30, 100)
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=colors[index % len(colors)],
        )
    image.alpha_composite(washes.filter(ImageFilter.GaussianBlur(28)))

    details = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(details)

    # Falling "snow" and gold sparkles
    for _ in range(width * height // 3500):
        x = rng.randrange(width)
        y = rng.randrange(height)
        radius = rng.choice((1, 1, 2, 3))
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(255, 255, 255, 210),
        )
    for index in range(44):
        # Alternate between the four borders so the card doesn't hide them
        along_x = rng.randrange(width)
        along_y = rng.randrange(height)
        near = rng.randrange(16, MARGIN - 6)
        x, y = [
            (along_x, near),
            (width - near, along_y),
            (along_x, height - near),
            (near, along_y),
        ][index % 4]
        color = (194, 160, 96, 230) if index % 3 else (255, 255, 255, 240)
        draw_sparkle(draw, x, y, rng.randrange(5, 12), color)

    # Thin double gold frame
    for inset, line_width in ((8, 3), (15, 1)):
        draw.rectangle(
            (inset, inset, width - inset - 1, height - inset - 1),
            outline=(194, 160, 96, 255),
            width=line_width,
        )

    draw_butterfly(draw, 36, 38, 24, (244, 196, 210, 240))
    draw_butterfly(draw, width - 36, height - 38, 24, (190, 214, 236, 240))

    image.alpha_composite(details)
    return image.convert("RGB")


def build_card(root):
    """Paint the window and return the frame the widgets belong in."""
    root.configure(bg=CREAM)
    root.resizable(False, False)
    root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")

    background = tk.Label(root, borderwidth=0, bg=CREAM)
    background.place(x=0, y=0, relwidth=1, relheight=1)

    card = tk.Frame(
        root,
        bg=CREAM,
        padx=36,
        pady=14,
        highlightthickness=2,
        highlightbackground=GOLD,
        highlightcolor=GOLD,
    )
    card.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def fit_window(event=None):
        width = max(WINDOW_SIZE, card.winfo_reqwidth() + 2 * MARGIN)
        height = max(WINDOW_SIZE, card.winfo_reqheight() + 2 * MARGIN)

        if getattr(background, "size", None) == (width, height):
            return

        photo = ImageTk.PhotoImage(paint_background(width, height))
        background.config(image=photo)
        background.image = photo  # Keep a reference, see set_photo()
        background.size = (width, height)
        root.geometry(f"{width}x{height}")

    # Fires whenever the card changes size, e.g. a picture or the countdown
    # appears
    card.bind("<Configure>", fit_window)
    fit_window()

    return card
