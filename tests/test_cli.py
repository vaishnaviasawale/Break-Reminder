import pytest

from break_reminder import cli


@pytest.fixture(autouse=True)
def fake_executable(monkeypatch):
    # enable_autostart() looks up the installed command on PATH; don't depend
    # on how the test environment was installed.
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda name: f"/usr/local/bin/{name}",
    )


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"
    config_dir = tmp_path / "config"
    runtime_dir = tmp_path / "runtime"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)
    monkeypatch.setattr(cli.config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cli.config, "CONFIG_FILE", config_dir / "config.json")
    monkeypatch.setattr(cli, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(cli, "SOCKET_FILE", runtime_dir / "br.sock")

    return desktop_file


def run_cli(monkeypatch, *args):
    monkeypatch.setattr(cli.sys, "argv", ["break-reminder", *args])
    cli.main()


def test_autostart_is_disabled_by_default(tmp_path, monkeypatch):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)

    assert desktop_file.exists() is False


def test_enable_autostart_creates_desktop_file(tmp_path, monkeypatch):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)

    cli.enable_autostart()

    assert desktop_file.exists() is True


def test_disable_autostart_removes_desktop_file(tmp_path, monkeypatch):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)

    cli.enable_autostart()
    assert desktop_file.exists() is True

    cli.disable_autostart()

    assert desktop_file.exists() is False


def test_enable_then_disable_autostart(tmp_path, monkeypatch):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)

    cli.enable_autostart()
    assert desktop_file.exists() is True

    cli.disable_autostart()
    assert desktop_file.exists() is False


def test_autostart_enable_does_not_enable_reminder(tmp_path, monkeypatch):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)
    monkeypatch.setattr(cli.config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cli.config, "CONFIG_FILE", config_file)

    cli.config.disable()
    assert cli.config.is_enabled() is False

    cli.enable_autostart()

    assert desktop_file.exists() is True
    assert cli.config.is_enabled() is False


def test_autostart_disable_does_not_change_reminder(tmp_path, monkeypatch):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)
    monkeypatch.setattr(cli.config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cli.config, "CONFIG_FILE", config_file)

    cli.config.enable()
    cli.enable_autostart()

    cli.disable_autostart()

    assert desktop_file.exists() is False
    assert cli.config.is_enabled() is True


def test_reminder_disable_does_not_disable_autostart(
    tmp_path,
    monkeypatch,
):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)
    monkeypatch.setattr(cli.config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cli.config, "CONFIG_FILE", config_file)

    cli.enable_autostart()
    cli.config.disable()

    assert desktop_file.exists() is True
    assert cli.config.is_enabled() is False


def test_reminder_enable_does_not_change_autostart(
    tmp_path,
    monkeypatch,
):
    autostart_dir = tmp_path / "autostart"
    desktop_file = autostart_dir / "break-reminder.desktop"
    config_dir = tmp_path / "config"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", autostart_dir)
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)
    monkeypatch.setattr(cli.config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cli.config, "CONFIG_FILE", config_file)

    cli.config.disable()
    cli.enable_autostart()

    cli.config.enable()

    assert desktop_file.exists() is True
    assert cli.config.is_enabled() is True


def test_desktop_file_launches_installed_command(tmp_path, monkeypatch):
    desktop_file = tmp_path / "autostart" / "break-reminder.desktop"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", tmp_path / "autostart")
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)

    cli.enable_autostart()

    assert "Exec=/usr/local/bin/break-reminder\n" in desktop_file.read_text()


def test_enable_autostart_fails_without_executable(tmp_path, monkeypatch):
    desktop_file = tmp_path / "autostart" / "break-reminder.desktop"

    monkeypatch.setattr(cli, "AUTOSTART_DIR", tmp_path / "autostart")
    monkeypatch.setattr(cli, "DESKTOP_FILE", desktop_file)
    monkeypatch.setattr(cli.shutil, "which", lambda name: None)

    with pytest.raises(SystemExit) as error:
        cli.enable_autostart()

    assert error.value.code == 1
    assert desktop_file.exists() is False


def test_no_arguments_launches_gui(monkeypatch):
    launched = False

    def fake_launch_gui():
        nonlocal launched
        launched = True

    monkeypatch.setattr(cli, "launch_gui", fake_launch_gui)

    run_cli(monkeypatch)

    assert launched is True


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_lists_commands(monkeypatch, capsys, flag):
    run_cli(monkeypatch, flag)

    output = capsys.readouterr().out

    assert "Usage:" in output
    assert "quit" in output
    assert "autostart enable" in output


def test_enable_and_disable_notify_running_gui(
    isolated_paths,
    monkeypatch,
):
    sent = []

    monkeypatch.setattr(
        cli,
        "send_command",
        lambda command: sent.append(command) or True,
    )

    run_cli(monkeypatch, "disable")
    run_cli(monkeypatch, "enable")

    assert sent == ["config-changed", "config-changed"]


def test_quit_stops_running_gui(isolated_paths, monkeypatch, capsys):
    sent = []

    monkeypatch.setattr(
        cli,
        "send_command",
        lambda command: sent.append(command) or True,
    )

    run_cli(monkeypatch, "quit")

    assert sent == ["quit"]
    assert "stopped" in capsys.readouterr().out


def test_quit_when_gui_not_running(isolated_paths, monkeypatch, capsys):
    run_cli(monkeypatch, "quit")

    assert "not running" in capsys.readouterr().out


def test_disable_and_enable_commands(isolated_paths, monkeypatch, capsys):
    run_cli(monkeypatch, "disable")
    assert cli.config.is_enabled() is False

    run_cli(monkeypatch, "status")
    assert "disabled" in capsys.readouterr().out

    run_cli(monkeypatch, "enable")
    assert cli.config.is_enabled() is True

    run_cli(monkeypatch, "status")
    assert "enabled" in capsys.readouterr().out


def test_autostart_commands(isolated_paths, monkeypatch, capsys):
    desktop_file = isolated_paths

    run_cli(monkeypatch, "autostart", "enable")
    assert desktop_file.exists() is True

    run_cli(monkeypatch, "autostart", "status")
    assert "autostart is enabled" in capsys.readouterr().out

    run_cli(monkeypatch, "autostart", "disable")
    assert desktop_file.exists() is False

    run_cli(monkeypatch, "autostart", "status")
    assert "autostart is disabled" in capsys.readouterr().out


@pytest.mark.parametrize(
    "args",
    [
        ("bogus",),
        ("enable", "extra"),
        ("disable", "extra"),
        ("status", "extra"),
        ("quit", "extra"),
        ("autostart",),
        ("autostart", "bogus"),
        ("autostart", "enable", "extra"),
    ],
)
def test_invalid_commands_exit_with_error(isolated_paths, monkeypatch, args):
    with pytest.raises(SystemExit) as error:
        run_cli(monkeypatch, *args)

    assert error.value.code == 1


def test_launch_gui_shows_existing_app_instead_of_starting_another(
    isolated_paths,
    monkeypatch,
):
    started = False

    def fake_popen(*args, **kwargs):
        nonlocal started
        started = True

    monkeypatch.setattr(cli, "show_existing_app", lambda: True)
    monkeypatch.setattr(cli.subprocess, "Popen", fake_popen)

    cli.launch_gui()

    assert started is False


def test_launch_gui_starts_detached_gui_when_none_running(
    isolated_paths,
    monkeypatch,
):
    popen_calls = []

    monkeypatch.setattr(cli, "show_existing_app", lambda: False)
    monkeypatch.setattr(
        cli.subprocess,
        "Popen",
        lambda *args, **kwargs: popen_calls.append((args, kwargs)),
    )

    cli.launch_gui()

    assert len(popen_calls) == 1
    (command,), kwargs = popen_calls[0]
    assert command == [cli.sys.executable, "-m", "break_reminder.main"]
    assert kwargs["start_new_session"] is True


def test_show_existing_app_leaves_unreachable_socket(isolated_paths):
    # The CLI must not delete the socket: the GUI may have bound it but not
    # yet called listen(). The GUI cleans up stale sockets on startup.
    cli.ensure_runtime_dir()
    cli.SOCKET_FILE.write_text("")  # nobody listening

    assert cli.show_existing_app() is False
    assert cli.SOCKET_FILE.exists() is True


def test_show_existing_app_sends_show(isolated_paths):
    cli.ensure_runtime_dir()

    with cli.socket.socket(cli.socket.AF_UNIX, cli.socket.SOCK_STREAM) as srv:
        srv.bind(str(cli.SOCKET_FILE))
        srv.listen(1)

        assert cli.show_existing_app() is True

        connection, _ = srv.accept()
        with connection:
            assert connection.recv(1024) == b"show"
