from break_reminder import config


def test_default_config_is_enabled(tmp_path, monkeypatch):
    config_dir = tmp_path / "break-reminder"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    assert config.is_enabled() is True


def test_disable_reminder(tmp_path, monkeypatch):
    config_dir = tmp_path / "break-reminder"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    config.disable()

    assert config.is_enabled() is False


def test_enable_reminder(tmp_path, monkeypatch):
    config_dir = tmp_path / "break-reminder"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    config.disable()
    config.enable()

    assert config.is_enabled() is True


def test_enable_disable_enable(tmp_path, monkeypatch):
    config_dir = tmp_path / "break-reminder"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    assert config.is_enabled() is True

    config.disable()
    assert config.is_enabled() is False

    config.enable()
    assert config.is_enabled() is True


def test_disable_enable_disable(tmp_path, monkeypatch):
    config_dir = tmp_path / "break-reminder"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    config.disable()
    assert config.is_enabled() is False

    config.enable()
    assert config.is_enabled() is True

    config.disable()
    assert config.is_enabled() is False


def test_config_file_is_created(tmp_path, monkeypatch):
    config_dir = tmp_path / "break-reminder"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    config.is_enabled()

    assert config_file.exists()


def test_saved_config_is_loaded(tmp_path, monkeypatch):
    config_dir = tmp_path / "break-reminder"
    config_file = config_dir / "config.json"

    monkeypatch.setattr(config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config, "CONFIG_FILE", config_file)

    config.disable()

    loaded_config = config.load_config()

    assert loaded_config["enabled"] is False
