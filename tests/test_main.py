import main


def test_start_timer_does_nothing_when_reminder_disabled(
    monkeypatch,
):
    monkeypatch.setattr(main.config, "is_enabled", lambda: False)

    class FakeEntry:
        def get(self):
            return "10"

    main.time_entry = FakeEntry()

    called = False

    def fake_after(*args):
        nonlocal called
        called = True

    class FakeRoot:
        def after(self, *args):
            fake_after(*args)

    main.root = FakeRoot()

    main.start_timer()

    assert called is False


def test_start_timer_schedules_timer_when_enabled(
    monkeypatch,
):
    monkeypatch.setattr(main.config, "is_enabled", lambda: True)

    class FakeEntry:
        def get(self):
            return "10"

    main.time_entry = FakeEntry()

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

    main.root = FakeRoot()

    main.disable_inputs = lambda: None

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

    main.update_content = fake_update_content

    window_restored = False

    class FakeRoot:
        def deiconify(self):
            nonlocal window_restored
            window_restored = True

    main.root = FakeRoot()

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

    main.update_content = fake_update_content

    window_restored = False

    class FakeRoot:
        def deiconify(self):
            nonlocal window_restored
            window_restored = True

    main.root = FakeRoot()

    inputs_enabled = False

    def fake_enable_inputs():
        nonlocal inputs_enabled
        inputs_enabled = True

    main.enable_inputs = fake_enable_inputs

    main.timer_finished()

    assert content_updated is True
    assert window_restored is True
    assert inputs_enabled is True
