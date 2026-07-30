from __future__ import annotations

import importlib.util
from pathlib import Path


def _runner_module():
    runner_path = Path(__file__).parents[1] / "research_lab_runner" / "app.py"
    spec = importlib.util.spec_from_file_location("test_research_lab_runner", runner_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_executes_bounded_code_and_returns_artifacts() -> None:
    runner = _runner_module()

    receipt = runner.execute(
        {
            "code": (
                "from pathlib import Path\n"
                "import os\n"
                "Path(os.environ['LAB_ARTIFACTS_DIR']).joinpath('answer.txt').write_text('4')\n"
                "print(2 + 2)\n"
            ),
            "sources": [],
        }
    )

    assert receipt["status"] == "completed"
    assert receipt["stdout"] == "4\n"
    assert receipt["stderr"] == ""
    assert receipt["exit_code"] == 0
    assert receipt["timed_out"] is False
    assert receipt["artifacts"][0]["name"] == "answer.txt"
