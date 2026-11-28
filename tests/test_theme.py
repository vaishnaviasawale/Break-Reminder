from PIL import Image

from break_reminder import theme


def test_colour_photo_is_softened_and_framed():
    photo = Image.new("RGB", (300, 200), (200, 40, 40))

    styled = theme.style_picture(photo)

    pad = theme.PHOTO_MARGIN
    assert styled.size == (300 + 2 * pad, 200 + 2 * pad)
    # The pure red has been veiled towards cream, so it is no longer pure
    centre = styled.getpixel((styled.width // 2, styled.height // 2))
    assert centre != (200, 40, 40)
    assert centre[1] > 40  # less saturated than the original


def test_black_and_white_comic_is_recoloured_to_card_palette():
    comic = Image.new("RGB", (300, 200), "white")
    comic.paste((0, 0, 0), (100, 80, 200, 120))

    styled = theme.style_picture(comic)

    assert styled.getpixel((styled.width // 2, styled.height // 2)) == (
        theme.INK_RGB
    )
    assert styled.getpixel((0, styled.height // 2)) == theme.GOLD_RGB
    assert styled.getpixel((20, 20)) == theme.CREAM_RGB


def test_greyscale_detection_ignores_colour_photos():
    assert theme.is_near_greyscale(Image.new("RGB", (4, 4), "grey"))
    assert not theme.is_near_greyscale(Image.new("RGB", (4, 4), "red"))
