import fcntl
import requests

from break_reminder import main

LOCK_FILE = RUNTIME_DIR / "break-reminder.lock"


def test_start_timer_does_nothing_when_reminder_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: False,
    )

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

    class FakeRoot:
        def after(self, *args):
            nonlocal called
            called = True

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
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

    class FakeEntry:
        def get(self):
            return "10"

    class FakeLabel:
        def config(self, **kwargs):
            pass

    monkeypatch.setattr(
        main,
        "time_entry",
        FakeEntry(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "error_label",
        FakeLabel(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "timer_status_label",
        FakeLabel(),
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

            return "timer-id"

        def after_cancel(self, timer_id):
            pass

        def withdraw(self):
            pass

    monkeypatch.setattr(
        main,
        "root",
        FakeRoot(),
        raising=False,
    )

    main.start_timer()

    assert scheduled_delay == 10 * 60 * 1000
    assert scheduled_callback == main.timer_finished
    assert main.timer_id == "timer-id"
    assert main.timer_end_time is not None


def test_timer_finished_does_not_show_break_if_disabled(
    monkeypatch,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: False,
    )

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

    main.timer_id = "timer-id"
    main.timer_end_time = object()

    main.timer_finished()

    assert content_updated is False
    assert window_restored is True
    assert main.timer_id is None
    assert main.timer_end_time is None


def test_timer_finished_shows_break_if_enabled(
    monkeypatch,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

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

    main.timer_id = "timer-id"
    main.timer_end_time = object()

    main.timer_finished()

    assert content_updated is True
    assert window_restored is True
    assert main.timer_id is None
    assert main.timer_end_time is None


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


def test_start_timer_shows_error_for_empty_input(
    monkeypatch,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

    class FakeEntry:
        def get(self):
            return ""

    class FakeLabel:
        def __init__(self):
            self.text = None

        def config(self, **kwargs):
            self.text = kwargs.get("text")

    error_label = FakeLabel()

    monkeypatch.setattr(
        main,
        "time_entry",
        FakeEntry(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "error_label",
        error_label,
        raising=False,
    )

    main.start_timer()

    assert error_label.text == (
        "Please enter the number of minutes."
    )


def test_start_timer_shows_error_for_non_number(
    monkeypatch,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

    class FakeEntry:
        def get(self):
            return "abc"

    class FakeLabel:
        def __init__(self):
            self.text = None

        def config(self, **kwargs):
            self.text = kwargs.get("text")

    error_label = FakeLabel()

    monkeypatch.setattr(
        main,
        "time_entry",
        FakeEntry(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "error_label",
        error_label,
        raising=False,
    )

    main.start_timer()

    assert error_label.text == (
        "Please enter a whole number of minutes."
    )


def test_start_timer_shows_error_for_zero(
    monkeypatch,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

    class FakeEntry:
        def get(self):
            return "0"

    class FakeLabel:
        def __init__(self):
            self.text = None

        def config(self, **kwargs):
            self.text = kwargs.get("text")

    error_label = FakeLabel()

    monkeypatch.setattr(
        main,
        "time_entry",
        FakeEntry(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "error_label",
        error_label,
        raising=False,
    )

    main.start_timer()

    assert error_label.text == (
        "Please enter a number greater than 0."
    )


def test_start_timer_replaces_existing_timer(
    monkeypatch,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

    class FakeEntry:
        def get(self):
            return "20"

    class FakeLabel:
        def config(self, **kwargs):
            pass

    monkeypatch.setattr(
        main,
        "time_entry",
        FakeEntry(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "error_label",
        FakeLabel(),
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "timer_status_label",
        FakeLabel(),
        raising=False,
    )

    cancelled_timer = None

    class FakeRoot:
        def after_cancel(self, timer_id):
            nonlocal cancelled_timer
            cancelled_timer = timer_id

        def after(self, delay, callback):
            return "new-timer"

        def withdraw(self):
            pass

    monkeypatch.setattr(
        main,
        "root",
        FakeRoot(),
        raising=False,
    )

    main.timer_id = "old-timer"

    main.start_timer()

    assert cancelled_timer == "old-timer"
    assert main.timer_id == "new-timer"
    assert main.timer_end_time is not None


def test_update_timer_display_shows_remaining_time(
    monkeypatch,
):
    class FakeLabel:
        def __init__(self):
            self.text = None

        def config(self, **kwargs):
            self.text = kwargs.get("text")

    label = FakeLabel()

    monkeypatch.setattr(
        main,
        "timer_status_label",
        label,
        raising=False,
    )

    monkeypatch.setattr(
        main,
        "timer_end_time",
        main.datetime.now() + main.timedelta(
            minutes=10,
            seconds=30,
        ),
    )

    main.update_timer_display()

    assert label.text.startswith("Next break in ")
    assert "Break at " in label.text


def acquire_instance_lock():
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


def test_instance_lock_allows_only_one_owner(
    monkeypatch,
    tmp_path,
):
    lock_file = tmp_path / "break-reminder.lock"

    monkeypatch.setattr(
        main,
        "RUNTIME_DIR",
        tmp_path,
    )

    monkeypatch.setattr(
        main,
        "LOCK_FILE",
        lock_file,
    )

    first_lock = main.acquire_instance_lock()

    assert first_lock is not None

    second_lock = main.acquire_instance_lock()

    assert second_lock is None

    first_lock.close()
