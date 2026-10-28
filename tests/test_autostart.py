import pytest

from break_reminder import autostart


@pytest.fixture
def desktop_file(tmp_path, monkeypatch):
    desktop_file = tmp_path / "autostart" / "break-reminder.desktop"

    monkeypatch.setattr(autostart, "AUTOSTART_DIR", tmp_path / "autostart")
    monkeypatch.setattr(autostart, "DESKTOP_FILE", desktop_file)
    monkeypatch.setattr(
        autostart.shutil,
        "which",
        lambda name: f"/usr/local/bin/{name}",
    )

    return desktop_file


def test_enable_and_disable_print_what_they_did(desktop_file, capsys):
    autostart.enable()
    assert autostart.is_enabled() is True
    assert capsys.readouterr().out == "Break Reminder autostart enabled.\n"

    autostart.disable()
    assert autostart.is_enabled() is False
    assert capsys.readouterr().out == "Break Reminder autostart disabled.\n"


def test_disable_when_already_disabled_is_fine(desktop_file, capsys):
    autostart.disable()

    assert autostart.is_enabled() is False
    assert "already disabled" in capsys.readouterr().out


def test_enable_raises_instead_of_exiting_without_executable(
    desktop_file,
    monkeypatch,
):
    monkeypatch.setattr(autostart.shutil, "which", lambda name: None)

    with pytest.raises(FileNotFoundError):
        autostart.enable()

    assert desktop_file.exists() is False
