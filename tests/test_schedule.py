"""The system schedule: the right command for each operating system, replaced rather than duplicated, never real,
and never another copy's: a second copy of the radar on the same computer leaves the first one's schedule alone."""

import plistlib
from pathlib import Path

import pytest

from radar import schedule


class Done:
    def __init__(self, code=0, out=""):
        self.returncode, self.stdout = code, out


def recorder(crontab_text="", task_xml=None):
    """A fake scheduler: crontab -l gives crontab_text; the Windows task query gives task_xml, or no task when None."""
    calls = []

    def run(args, **kw):
        calls.append((args, kw.get("input")))
        if args[:2] == ["crontab", "-l"]:
            return Done(0 if crontab_text else 1, crontab_text)
        if args[:2] == ["schtasks", "/Query"]:
            return Done(1) if task_xml is None else Done(0, task_xml)
        return Done()

    return run, calls


def task_for(folder):
    """The Windows task as schtasks /XML prints it, starting the radar in folder."""
    args = f"/c cd /d {folder} &amp;&amp; python run.py &gt;&gt; logs\\run.log 2&gt;&amp;1"
    return f"<Task><Actions><Exec><Command>cmd</Command><Arguments>{args}</Arguments></Exec></Actions></Task>"


def test_windows_task_points_at_a_script_in_the_repo(tmp_path):
    run, calls = recorder()
    assert schedule.install("07:05", system="Windows", run=run, root=tmp_path)
    args = calls[-1][0]
    assert args[:5] == ["schtasks", "/Create", "/SC", "DAILY", "/ST"] and "07:05" in args and "/F" in args
    script = (tmp_path / ".cache" / "run-daily.cmd").read_text(encoding="utf-8")
    assert f'cd /d "{tmp_path}"' in script and "run.py >> logs\\run.log" in script


def test_mac_writes_a_launch_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(schedule, "PLIST", tmp_path / "agent.plist")
    run, calls = recorder()
    assert schedule.install("06:45", system="Darwin", run=run, root=tmp_path)
    spec = plistlib.loads((tmp_path / "agent.plist").read_bytes())
    assert spec["StartCalendarInterval"] == {"Hour": 6, "Minute": 45} and "run.py" in spec["ProgramArguments"][2]
    assert calls[-1][0][:3] == ["launchctl", "load", "-w"] and schedule.status(system="Darwin", root=tmp_path)
    assert not schedule.status(system="Darwin", root=tmp_path / "other")


def copy_at(folder):
    """Another copy of the radar that still exists."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "run.py").write_text("", encoding="utf-8")
    return folder


def test_linux_replaces_its_own_cron_line_and_keeps_others(tmp_path):
    copy_at(Path(f"{tmp_path}-2"))
    mine = f'30 7 * * * cd "{tmp_path}" && python run.py {schedule.MARK}'
    other = f'0 6 * * * cd "{tmp_path}-2" && python run.py {schedule.MARK}'
    run, calls = recorder("\n".join(["0 1 * * * backup.sh", mine, other]) + "\n")
    assert schedule.install("08:10", system="Linux", run=run, root=tmp_path)
    written = calls[-1][1]
    assert "backup.sh" in written and mine not in written and other in written  # another copy keeps its line
    assert written.splitlines()[-1].startswith("10 8 * * * ") and written.count(schedule.MARK) == 2


def test_a_task_that_starts_another_copy_is_not_this_ones(tmp_path):
    run, calls = recorder(task_xml=task_for(copy_at(tmp_path.parent / f"{tmp_path.name}-2")))
    assert not schedule.status(system="Windows", run=run, root=tmp_path)
    assert schedule.remove(system="Windows", run=run, root=tmp_path)  # nothing of this folder's to remove
    assert not schedule.install("07:30", system="Windows", run=run, root=tmp_path)  # would replace the other's
    assert not any(args[1] in ("/Delete", "/Create") for args, _ in calls)


def test_this_folders_task_is_found_and_removed(tmp_path):
    run, calls = recorder(task_xml=task_for(tmp_path))
    assert schedule.status(system="Windows", run=run, root=tmp_path)
    assert schedule.remove(system="Windows", run=run, root=tmp_path)
    assert calls[-1][0][:2] == ["schtasks", "/Delete"]


ROOT = Path("C:/Users/jane/Downloads/job-radar")


@pytest.mark.parametrize(
    "text",
    [
        f'"{ROOT}\\.cache\\run-daily.cmd"',  # the task setup makes
        f"/c cd /d {ROOT} &amp;&amp; python run.py &gt;&gt; logs\\run.log",  # one made by hand
        f'cd "{ROOT}" && "python" run.py >> logs/run.log 2>&1',  # launchd and cron
    ],
)
def test_this_folders_entries_are_recognized(text):
    assert schedule.here(text, ROOT)


@pytest.mark.parametrize(
    "folder",
    [
        f"{ROOT} - Copy",  # Windows Explorer's copy
        f"{ROOT} (1)",  # a zip downloaded twice
        f"{ROOT} copy",  # Finder's copy
        f"{ROOT}-2",
        f"{ROOT}\\.claude\\worktrees\\fix",  # a copy nested inside this one
    ],
)
def test_lookalike_and_nested_folders_are_other_copies(folder):
    assert not schedule.here(f'"{folder}\\.cache\\run-daily.cmd"', ROOT)
    assert not schedule.here(f'cd "{folder}" && "python" run.py', ROOT)
    assert not schedule.here(f"/c cd /d {folder} &amp;&amp; python run.py", ROOT)


def test_a_task_whose_folder_is_gone_can_be_replaced_or_removed(tmp_path):
    gone = tmp_path.parent / f"{tmp_path.name}-moved"  # never created: the copy was moved or deleted
    run, calls = recorder(task_xml=task_for(gone))
    assert not schedule.elsewhere(system="Windows", run=run, root=tmp_path)
    assert schedule.install("07:30", system="Windows", run=run, root=tmp_path)
    assert calls[-1][0][:2] == ["schtasks", "/Create"]
    assert schedule.remove(system="Windows", run=run, root=tmp_path)
    assert calls[-1][0][:2] == ["schtasks", "/Delete"]


def test_cron_lines_for_folders_that_are_gone_are_cleared(tmp_path):
    gone = f'0 6 * * * cd "{tmp_path}-gone" && python run.py {schedule.MARK}'
    run, calls = recorder("0 1 * * * backup.sh\n" + gone + "\n")
    assert schedule.remove(system="Linux", run=run, root=tmp_path)
    assert calls[-1][1] == "0 1 * * * backup.sh\n"


def test_status_is_false_without_a_scheduler_command():
    def missing(args, **kw):
        raise FileNotFoundError(args[0])

    assert schedule.status(system="Linux", run=missing) is False


def test_the_setup_switch_says_when_another_copy_has_the_task(tmp_path, monkeypatch):
    import server

    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text('{"run_time": "07:30"}', encoding="utf-8")
    monkeypatch.setattr(schedule, "elsewhere", lambda: True)
    monkeypatch.setattr(schedule, "install", lambda at: pytest.fail("would replace the other copy's task"))
    reply = server.daily_schedule({"on": True})
    assert reply["ok"] is False and "another copy" in reply["why"]
