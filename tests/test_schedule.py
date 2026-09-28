"""The system schedule: the right command for each operating system, replaced rather than duplicated, never real."""

import plistlib

from radar import schedule


class Done:
    def __init__(self, code=0, out=""):
        self.returncode, self.stdout = code, out


def recorder(crontab_text=""):
    calls = []

    def run(args, **kw):
        calls.append((args, kw.get("input")))
        if args[:2] == ["crontab", "-l"]:
            return Done(0 if crontab_text else 1, crontab_text)
        return Done()

    return run, calls


def test_windows_task_points_at_a_script_in_the_repo(tmp_path):
    run, calls = recorder()
    assert schedule.install("07:05", system="Windows", run=run, root=tmp_path)
    args = calls[0][0]
    assert args[:5] == ["schtasks", "/Create", "/SC", "DAILY", "/ST"] and "07:05" in args and "/F" in args
    script = (tmp_path / ".cache" / "run-daily.cmd").read_text(encoding="utf-8")
    assert f'cd /d "{tmp_path}"' in script and "run.py >> logs\\run.log" in script


def test_mac_writes_a_launch_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "PLIST", tmp_path / "agent.plist")
    run, calls = recorder()
    assert schedule.install("06:45", system="Darwin", run=run, root=tmp_path)
    spec = plistlib.loads((tmp_path / "agent.plist").read_bytes())
    assert spec["StartCalendarInterval"] == {"Hour": 6, "Minute": 45} and "run.py" in spec["ProgramArguments"][2]
    assert calls[-1][0][:3] == ["launchctl", "load", "-w"] and schedule.status(system="Darwin")


def test_linux_replaces_its_own_cron_line_and_keeps_others(tmp_path):
    existing = f"0 1 * * * backup.sh\n30 7 * * * old command {schedule.MARK}\n"
    run, calls = recorder(existing)
    assert schedule.install("08:10", system="Linux", run=run, root=tmp_path)
    written = calls[-1][1]
    assert "backup.sh" in written and "old command" not in written and written.count(schedule.MARK) == 1
    assert written.splitlines()[-1].startswith("10 8 * * * ")


def test_status_is_false_without_a_scheduler_command():
    def missing(args, **kw):
        raise FileNotFoundError(args[0])

    assert schedule.status(system="Linux", run=missing) is False
