from break_reminder import cli


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