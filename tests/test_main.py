import requests

from break_reminder import main


def test_start_timer_does_nothing_when_reminder_disabled(
    monkeypatch,
):
    monkeypatch.setattr(main.config, "is_enabled", lambda: False)

    class FakeEntry:
        def get(self):
            return "10"

    monkeypatch.setattr(
        main,
        "time_entry",
        FakeEntry(),
        raising=False,
    )

    called = False

    def fake_after(*args):
        nonlocal called
        called = True

    class FakeRoot:
        def after(self, *args):
            fake_after(*args)

    monkeypatch.setattr(
        main,
        "root",
        FakeRoot(),
        raising=False,
    )

    main.start_timer()

    assert called is False


def test_start_timer_schedules_timer_when_enabled(
    monkeypatch,
):
    monkeypatch.setattr(main.config, "is_enabled", lambda: True)

    class FakeEntry:
        def get(self):
            return "10"

    monkeypatch.setattr(
        main,
        "time_entry",
        FakeEntry(),
        raising=False,
    )

    scheduled_delay = None
    scheduled_callback = None

    class FakeRoot:
        def after(self, delay, callback):
            nonlocal scheduled_delay
            nonlocal scheduled_callback

            scheduled_delay = delay
            scheduled_callback = callback

        def withdraw(self):
            pass

    monkeypatch.setattr(
        main,
        "root",
        FakeRoot(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "disable_inputs",
        lambda: None,
    )

    main.start_timer()

    assert scheduled_delay == 10 * 60 * 1000
    assert scheduled_callback == main.timer_finished


def test_timer_finished_does_not_show_break_if_disabled(
    monkeypatch,
):
    monkeypatch.setattr(main.config, "is_enabled", lambda: False)

    content_updated = False

    def fake_update_content():
        nonlocal content_updated
        content_updated = True

    monkeypatch.setattr(
        main,
        "update_content",
        fake_update_content,
    )

    window_restored = False

    class FakeRoot:
        def deiconify(self):
            nonlocal window_restored
            window_restored = True

    monkeypatch.setattr(
        main,
        "root",
        FakeRoot(),
        raising=False,
    )

    inputs_enabled = False

    def fake_enable_inputs():
        nonlocal inputs_enabled
        inputs_enabled = True

    main.enable_inputs = fake_enable_inputs

    main.timer_finished()

    assert content_updated is False
    assert window_restored is True
    assert inputs_enabled is True


def test_timer_finished_shows_break_if_enabled(
    monkeypatch,
):
    monkeypatch.setattr(main.config, "is_enabled", lambda: True)

    content_updated = False

    def fake_update_content():
        nonlocal content_updated
        content_updated = True

    monkeypatch.setattr(
        main,
        "update_content",
        fake_update_content,
    )

    window_restored = False

    class FakeRoot:
        def deiconify(self):
            nonlocal window_restored
            window_restored = True

    monkeypatch.setattr(
        main,
        "root",
        FakeRoot(),
        raising=False,
    )

    inputs_enabled = False

    def fake_enable_inputs():
        nonlocal inputs_enabled
        inputs_enabled = True

    main.enable_inputs = fake_enable_inputs

    main.timer_finished()

    assert content_updated is True
    assert window_restored is True
    assert inputs_enabled is True


def test_get_image_uses_online_image(monkeypatch):
    class FakeImage:
        def thumbnail(self, size):
            assert size == (450, 300)

    fake_image = FakeImage()

    monkeypatch.setattr(
        main,
        "get_xkcd_image",
        lambda: (fake_image, "XKCD title"),
    )

    monkeypatch.setattr(
        main.random,
        "choice",
        lambda sources: "xkcd",
    )

    fake_photo = object()

    monkeypatch.setattr(
        main.ImageTk,
        "PhotoImage",
        lambda image: fake_photo,
    )

    photo, title = main.get_image()

    assert photo is fake_photo
    assert title == "XKCD title"


def test_get_image_uses_fallback_when_online_image_fails(
    monkeypatch,
):
    class FakeImage:
        def thumbnail(self, size):
            assert size == (450, 300)

    fallback_image = FakeImage()

    def fake_online_image():
        raise requests.RequestException("Network error")

    monkeypatch.setattr(
        main,
        "get_xkcd_image",
        fake_online_image,
    )

    monkeypatch.setattr(
        main.random,
        "choice",
        lambda sources: "xkcd",
    )

    monkeypatch.setattr(
        main,
        "get_fallback_image",
        lambda: (fallback_image, "Time for a break!"),
    )

    fake_photo = object()

    monkeypatch.setattr(
        main.ImageTk,
        "PhotoImage",
        lambda image: fake_photo,
    )

    photo, title = main.get_image()

    assert photo is fake_photo
    assert title == "Time for a break!"


def test_get_image_returns_text_only_when_no_fallback_exists(
    monkeypatch,
):
    def fake_online_image():
        raise requests.RequestException("Network error")

    monkeypatch.setattr(
        main,
        "get_xkcd_image",
        fake_online_image,
    )

    monkeypatch.setattr(
        main.random,
        "choice",
        lambda sources: "xkcd",
    )

    monkeypatch.setattr(
        main,
        "get_fallback_image",
        lambda: None,
    )

    photo, title = main.get_image()

    assert photo is None
    assert title == "Time for a break!"


def test_update_content_handles_missing_image(monkeypatch):
    class FakeInstructionLabel:
        def __init__(self):
            self.config_calls = []

        def config(self, **kwargs):
            self.config_calls.append(kwargs)

    class FakeImageLabel:
        def __init__(self):
            self.image = "old image"
            self.config_calls = []

        def config(self, **kwargs):
            self.config_calls.append(kwargs)

    instruction_label = FakeInstructionLabel()
    image_label = FakeImageLabel()

    monkeypatch.setattr(
        main,
        "instruction_label",
        instruction_label,
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "image_label",
        image_label,
        raising=False,
    )

    def fake_get_image():
        return None, "Time for a break!"

    monkeypatch.setattr(main, "get_image", fake_get_image)

    main.update_content()

    assert instruction_label.config_calls
    assert instruction_label.config_calls[0]["text"] == "Time for a break!"

    assert image_label.config_calls
    assert image_label.config_calls[0]["image"] == ""

    assert image_label.image is None
