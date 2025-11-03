from types import SimpleNamespace

import pytest

from dwgmagic.integrations.autocad import AutoCadCoordinator, AutoCadJob, AutoCadResult, AutoCadRunner
from dwgmagic.settings import Settings


def test_runner_builds_command_with_input(tmp_path, monkeypatch):
    executable = tmp_path / "accoreconsole.exe"
    executable.write_text("stub")
    settings = Settings(project_root=tmp_path, autocad_executable=executable)
    runner = AutoCadRunner(settings)

    recorded = {}

    def fake_run(command, capture_output, text, encoding, timeout, check):
        recorded["command"] = command
        return SimpleNamespace(returncode=0, stdout="out", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)

    script = tmp_path / "script.scr"
    script.write_text("script")
    input_dwg = tmp_path / "input.dwg"
    input_dwg.write_text("dwg")

    result = runner.run_script(
        script_path=script,
        input_path=input_dwg,
        logger=SimpleNamespace(debug=lambda *args, **kwargs: None, error=lambda *args, **kwargs: None, info=lambda *args, **kwargs: None),
    )
    assert result.returncode == 0
    assert recorded["command"] == [str(executable), "/i", str(input_dwg), "/s", str(script)]
    assert result.command == tuple(recorded["command"])


def test_runner_discover_raises_when_missing(tmp_path):
    settings = Settings(project_root=tmp_path, autocad_executable=None, autocad_candidates=())
    runner = AutoCadRunner(settings)
    with pytest.raises(FileNotFoundError):
        runner.discover()


def test_coordinator_executes_jobs(tmp_path):
    class RecordingRunner:
        def __init__(self):
            self.calls = []

        def run_script(self, *, script_path, logger, input_path=None):
            self.calls.append((script_path, input_path))
            return AutoCadResult(
                name=script_path.stem,
                returncode=0,
                stdout="",
                stderr="",
                command=(str(script_path),),
            )

    runner = RecordingRunner()
    coordinator = AutoCadCoordinator(runner, max_workers=2)
    jobs = [
        AutoCadJob(name="a", script_path=tmp_path / "a.scr", input_path=None),
        AutoCadJob(name="b", script_path=tmp_path / "b.scr", input_path=tmp_path / "b.dwg"),
    ]
    logger = SimpleNamespace(info=lambda *args, **kwargs: None, error=lambda *args, **kwargs: None)
    results = list(coordinator.execute(jobs, logger))
    assert len(results) == 2
    assert sorted(result.name for result in results) == ["a", "b"]
    assert set(runner.calls) == {
        (tmp_path / "a.scr", None),
        (tmp_path / "b.scr", tmp_path / "b.dwg"),
    }


def test_coordinator_notifies_listener(tmp_path):
    events = []

    class RecordingRunner:
        def run_script(self, *, script_path, logger, input_path=None):
            return AutoCadResult(
                name=script_path.stem,
                returncode=0,
                stdout="stdout",
                stderr="stderr",
                command=(str(script_path),),
            )

    class Listener:
        def on_job_queued(self, job):
            events.append(("queued", job.name))

        def on_job_started(self, job):
            events.append(("started", job.name))

        def on_job_completed(self, result):
            events.append(("completed", result.name, result.stdout, result.stderr))

        def on_job_failed(self, job, error):  # pragma: no cover - not exercised here
            events.append(("failed", job.name, str(error)))

    runner = RecordingRunner()
    coordinator = AutoCadCoordinator(runner, max_workers=1)
    job = AutoCadJob(name="demo", script_path=tmp_path / "demo.scr", input_path=None)
    logger = SimpleNamespace(info=lambda *args, **kwargs: None, error=lambda *args, **kwargs: None)

    list(coordinator.execute([job], logger, listener=Listener()))

    assert ("queued", "demo") in events
    assert ("started", "demo") in events
    completed_events = [event for event in events if event[0] == "completed"]
    assert completed_events and completed_events[0][1:] == ("demo", "stdout", "stderr")
