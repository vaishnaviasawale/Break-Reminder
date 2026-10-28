import socket
import threading
import time

import pytest
import requests

from break_reminder import main


@pytest.fixture(autouse=True)
def reset_timer_state():
    main.timer_id = None
    main.timer_end_time = None
    main.refresh_id = None

    yield

    main.timer_id = None
    main.timer_end_time = None
    main.refresh_id = None


class FakeLabel:
    def __init__(self):
        self.text = None

    def config(self, **kwargs):
        self.text = kwargs.get("text")


class FakeWidget:
    def __init__(self):
        self.options = {}

    def config(self, **kwargs):
        self.options.update(kwargs)


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

    # start_timer() schedules the break and also starts the once-a-second
    # countdown refresh, so record every after() call.
    scheduled = []
    withdrawn = False

    class FakeRoot:
        def after(self, delay, callback):
            scheduled.append((delay, callback))
            return f"timer-id-{len(scheduled)}"

        def after_cancel(self, timer_id):
            pass

        def withdraw(self):
            nonlocal withdrawn
            withdrawn = True

    monkeypatch.setattr(
        main,
        "root",
        FakeRoot(),
        raising=False,
    )

    main.start_timer()

    assert scheduled[0] == (10 * 60 * 1000, main.timer_finished)
    assert (1000, main.refresh_timer_display) in scheduled
    assert main.timer_id == "timer-id-1"
    assert main.timer_end_time is not None
    assert withdrawn is True


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
    assert window_restored is False
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


def test_get_image_uses_duckduckgo_for_topics(monkeypatch):
    class FakeImage:
        def thumbnail(self, size):
            pass

    requested_topics = []

    def fake_duckduckgo_image(topic):
        requested_topics.append(topic)
        return FakeImage(), topic

    monkeypatch.setattr(
        main,
        "get_duckduckgo_image",
        fake_duckduckgo_image,
    )

    monkeypatch.setattr(
        main.random,
        "choice",
        lambda sources: "puppies",
    )

    monkeypatch.setattr(
        main.ImageTk,
        "PhotoImage",
        lambda image: object(),
    )

    _, title = main.get_image()

    assert requested_topics == ["puppies"]
    assert title == "puppies"


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


def test_get_image_uses_fallback_when_duckduckgo_fails(monkeypatch):
    class FakeImage:
        def thumbnail(self, size):
            pass

    def fake_duckduckgo_image(topic):
        raise main.DDGSException("Ratelimit")

    monkeypatch.setattr(
        main,
        "get_duckduckgo_image",
        fake_duckduckgo_image,
    )

    monkeypatch.setattr(
        main.random,
        "choice",
        lambda sources: "puppies",
    )

    monkeypatch.setattr(
        main,
        "get_fallback_image",
        lambda: (FakeImage(), "Time for a break!"),
    )

    monkeypatch.setattr(
        main.ImageTk,
        "PhotoImage",
        lambda image: object(),
    )

    _, title = main.get_image()

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


def test_get_fallback_image_returns_none_without_assets(monkeypatch):
    monkeypatch.setattr(main, "FALLBACK_IMAGES", [])

    assert main.get_fallback_image() is None


def test_fallback_images_are_packaged():
    assert main.FALLBACK_IMAGES

    image, title = main.get_fallback_image()

    assert image.size[0] > 0
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


@pytest.mark.parametrize(
    ("entry_text", "expected_error"),
    [
        ("", "Please enter the number of minutes."),
        ("   ", "Please enter the number of minutes."),
        ("abc", "Please enter a whole number of minutes."),
        ("1.5", "Please enter a whole number of minutes."),
        ("0", "Please enter a number greater than 0."),
        ("-5", "Please enter a number greater than 0."),
    ],
)
def test_start_timer_shows_error_for_invalid_input(
    monkeypatch,
    entry_text,
    expected_error,
):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

    class FakeEntry:
        def get(self):
            return entry_text

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

    assert error_label.text == expected_error
    assert main.timer_id is None
    assert main.timer_end_time is None


def test_start_timer_clears_previous_error(monkeypatch):
    monkeypatch.setattr(
        main.config,
        "is_enabled",
        lambda: True,
    )

    class FakeEntry:
        def get(self):
            return " 5 "

    error_label = FakeLabel()
    error_label.text = "Please enter the number of minutes."

    class FakeRoot:
        def after(self, delay, callback):
            return "timer-id"

        def withdraw(self):
            pass

    monkeypatch.setattr(main, "time_entry", FakeEntry(), raising=False)
    monkeypatch.setattr(main, "error_label", error_label, raising=False)
    monkeypatch.setattr(
        main,
        "timer_status_label",
        FakeLabel(),
        raising=False,
    )
    monkeypatch.setattr(main, "root", FakeRoot(), raising=False)

    main.start_timer()

    assert error_label.text == ""
    assert main.timer_id == "timer-id"


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
        main.datetime(2026, 1, 1, 14, 5, 0),
    )

    class FakeDatetime(main.datetime):
        @classmethod
        def now(cls):
            return cls(2026, 1, 1, 13, 54, 30)

    monkeypatch.setattr(main, "datetime", FakeDatetime)

    main.update_timer_display()

    assert label.text == "Next break in 10:30\nBreak at 2:05 PM"


def test_update_timer_display_never_shows_negative_time(monkeypatch):
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
        main.datetime.now() - main.timedelta(minutes=1),
    )

    main.update_timer_display()

    assert label.text.startswith("Next break in 0:00\n")


def test_update_timer_display_is_blank_without_timer(monkeypatch):
    label = FakeLabel()
    label.text = "Next break in 1:00"

    monkeypatch.setattr(
        main,
        "timer_status_label",
        label,
        raising=False,
    )

    main.update_timer_display()

    assert label.text == ""


def test_refresh_timer_display_stops_without_timer(monkeypatch):
    called = False

    class FakeRoot:
        def after(self, *args):
            nonlocal called
            called = True

    monkeypatch.setattr(main, "root", FakeRoot(), raising=False)

    main.refresh_timer_display()

    assert called is False


def test_toggle_enabled_flips_reminder_and_button(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(main.config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(
        main.config,
        "CONFIG_FILE",
        tmp_path / "config.json",
    )

    button = FakeLabel()

    monkeypatch.setattr(
        main,
        "control_status_button",
        button,
        raising=False,
    )
    monkeypatch.setattr(
        main,
        "timer_status_label",
        FakeLabel(),
        raising=False,
    )
    monkeypatch.setattr(main, "start_button", FakeWidget(), raising=False)
    monkeypatch.setattr(
        main, "disabled_hint_label", FakeWidget(), raising=False
    )

    main.toggle_enabled()

    assert main.config.is_enabled() is False
    assert button.text == "Enable Reminder"

    main.toggle_enabled()

    assert main.config.is_enabled() is True
    assert button.text == "Disable Reminder"


def test_quit_app_cancels_timer_and_destroys_window(monkeypatch):
    cancelled_timer = None
    destroyed = False

    class FakeRoot:
        def after_cancel(self, timer_id):
            nonlocal cancelled_timer
            if timer_id == "timer-id":
                cancelled_timer = timer_id

        def destroy(self):
            nonlocal destroyed
            destroyed = True

    monkeypatch.setattr(main, "root", FakeRoot(), raising=False)
    monkeypatch.setattr(
        main,
        "timer_status_label",
        FakeLabel(),
        raising=False,
    )

    main.timer_id = "timer-id"
    main.timer_end_time = object()

    main.quit_app()

    assert cancelled_timer == "timer-id"
    assert destroyed is True
    assert main.timer_id is None
    assert main.timer_end_time is None


class FakeScheduler:
    # Behaves like Tk's after()/after_cancel(): keeps every pending callback
    # until it runs or is cancelled.
    def __init__(self):
        self.pending = {}
        self.next_id = 0

    def after(self, delay, callback):
        self.next_id += 1
        after_id = f"after#{self.next_id}"
        self.pending[after_id] = callback
        return after_id

    def after_cancel(self, after_id):
        self.pending.pop(after_id, None)

    def withdraw(self):
        pass

    def destroy(self):
        pass

    def tick(self):
        # Run the countdown refreshes that are due; leave the break alone.
        due = {
            after_id: callback
            for after_id, callback in self.pending.items()
            if callback == main.refresh_timer_display
        }
        for after_id, callback in due.items():
            del self.pending[after_id]
            callback()

    def count(self, callback):
        return list(self.pending.values()).count(callback)


@pytest.fixture
def scheduler(monkeypatch):
    monkeypatch.setattr(main.config, "is_enabled", lambda: True)
    monkeypatch.setattr(main, "error_label", FakeLabel(), raising=False)
    monkeypatch.setattr(
        main,
        "timer_status_label",
        FakeLabel(),
        raising=False,
    )

    monkeypatch.setattr(main, "start_button", FakeWidget(), raising=False)
    monkeypatch.setattr(
        main, "disabled_hint_label", FakeWidget(), raising=False
    )

    scheduler = FakeScheduler()
    monkeypatch.setattr(main, "root", scheduler, raising=False)

    return scheduler


def set_entry(monkeypatch, text):
    class FakeEntry:
        def get(self):
            return text

    monkeypatch.setattr(main, "time_entry", FakeEntry(), raising=False)


def test_replacing_timer_keeps_one_countdown_loop(monkeypatch, scheduler):
    for minutes in ["20", "10", "5"]:
        set_entry(monkeypatch, minutes)
        main.start_timer()

        # Let a couple of seconds tick by between changes.
        scheduler.tick()
        scheduler.tick()

    assert scheduler.count(main.refresh_timer_display) == 1


def test_quit_app_stops_countdown_loop(monkeypatch, scheduler):
    set_entry(monkeypatch, "10")
    main.start_timer()

    assert scheduler.count(main.refresh_timer_display) == 1

    main.quit_app()

    assert scheduler.pending == {}
    assert main.refresh_id is None


def test_countdown_loop_stops_when_timer_ends(monkeypatch, scheduler):
    set_entry(monkeypatch, "10")
    main.start_timer()

    main.timer_end_time = None
    scheduler.tick()

    assert scheduler.count(main.refresh_timer_display) == 0
    assert main.refresh_id is None


def test_disabling_cancels_running_timer(monkeypatch, scheduler):
    set_entry(monkeypatch, "10")
    main.start_timer()

    button = FakeLabel()
    monkeypatch.setattr(
        main,
        "control_status_button",
        button,
        raising=False,
    )
    monkeypatch.setattr(main.config, "is_enabled", lambda: False)

    main.apply_config()

    assert scheduler.pending == {}
    assert main.timer_id is None
    assert main.timer_end_time is None
    assert main.timer_status_label.text == ""
    assert button.text == "Enable Reminder"
    assert main.start_button.options["state"] == main.tk.DISABLED


def test_enabling_keeps_running_timer(monkeypatch, scheduler):
    set_entry(monkeypatch, "10")
    main.start_timer()
    running_timer = main.timer_id

    button = FakeLabel()
    monkeypatch.setattr(
        main,
        "control_status_button",
        button,
        raising=False,
    )

    main.apply_config()

    assert main.timer_id == running_timer
    assert main.timer_finished in scheduler.pending.values()
    assert button.text == "Disable Reminder"


def test_show_window_restores_and_focuses_window(monkeypatch):
    calls = []

    class FakeRoot:
        def deiconify(self):
            calls.append("deiconify")

        def lift(self):
            calls.append("lift")

        def focus_force(self):
            calls.append("focus_force")

    monkeypatch.setattr(main, "root", FakeRoot(), raising=False)

    main.show_window()

    assert calls == ["deiconify", "lift", "focus_force"]


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


def test_instance_lock_is_released_when_owner_closes(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(main, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(
        main,
        "LOCK_FILE",
        tmp_path / "break-reminder.lock",
    )

    first_lock = main.acquire_instance_lock()
    first_lock.close()

    second_lock = main.acquire_instance_lock()

    assert second_lock is not None

    second_lock.close()


def test_show_existing_app_returns_false_without_server(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(main, "SOCKET_FILE", tmp_path / "missing.sock")

    assert main.show_existing_app() is False


@pytest.mark.parametrize(
    ("command", "handler"),
    [
        (b"show", "show_window"),
        (b"config-changed", "apply_config"),
        (b"quit", "quit_app"),
    ],
)
def test_command_reaches_running_gui(monkeypatch, tmp_path, command, handler):
    socket_file = tmp_path / "br.sock"
    received = threading.Event()
    calls = []

    class FakeRoot:
        def after(self, delay, callback):
            calls.append((delay, callback))
            received.set()

    monkeypatch.setattr(main, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(main, "SOCKET_FILE", socket_file)
    monkeypatch.setattr(main, "root", FakeRoot(), raising=False)

    main.start_command_server()

    # The server thread needs a moment to bind and listen.
    deadline = time.monotonic() + 2
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.connect(str(socket_file))
                sock.sendall(command)
            break
        except OSError:
            assert time.monotonic() < deadline, "command server never started"
            time.sleep(0.01)

    assert received.wait(timeout=2)
    assert calls == [(0, getattr(main, handler))]


def test_start_button_greyed_out_with_hint_when_disabled(monkeypatch):
    start_button = FakeWidget()
    hint_label = FakeWidget()

    monkeypatch.setattr(main.config, "is_enabled", lambda: False)
    monkeypatch.setattr(main, "start_button", start_button, raising=False)
    monkeypatch.setattr(main, "disabled_hint_label", hint_label, raising=False)
    monkeypatch.setattr(
        main, "control_status_button", FakeWidget(), raising=False
    )

    main.update_control_button()

    assert start_button.options["state"] == main.tk.DISABLED
    assert "Enable" in hint_label.options["text"]


def test_start_button_active_without_hint_when_enabled(monkeypatch):
    start_button = FakeWidget()
    hint_label = FakeWidget()

    monkeypatch.setattr(main.config, "is_enabled", lambda: True)
    monkeypatch.setattr(main, "start_button", start_button, raising=False)
    monkeypatch.setattr(main, "disabled_hint_label", hint_label, raising=False)
    monkeypatch.setattr(
        main, "control_status_button", FakeWidget(), raising=False
    )

    main.update_control_button()

    assert start_button.options["state"] == main.tk.NORMAL
    assert hint_label.options["text"] == ""
