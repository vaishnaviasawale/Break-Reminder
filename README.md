## pyproject.toml
```
[project.scripts]
break-reminder = "break_reminder.main:main"
break-reminder-cli = "break_reminder.cli:main"
```
This means that after installation, Python will create executable commands:
break-reminder
break-reminder-cli

The build-system section tells Python/uv how to build the package, and:
[tool.hatch.build.targets.wheel]
packages = ["src/break_reminder"]
tells the build system that your actual Python package lives under src/.

[tool.pytest.ini_options]
pythonpath = ["src"]
because main.py, cli.py, and config.py are now inside src/break_reminder.