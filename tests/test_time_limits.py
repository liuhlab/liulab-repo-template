"""The suite budget, the per-test timeout, its warning and the slow lane, through pytest itself.

Each test runs pytest over a scratch tree carrying this repo's own `conftest.py` and
`[tool.pytest.ini_options]`, with the limits shrunk so a short sleep crosses them.
"""

from __future__ import annotations

import json
import shlex
import time
import tomllib
from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

REPO = Path(__file__).resolve().parents[1]
MANIFEST = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))

SLOW_TEST = """
import time

import pytest


@pytest.mark.slow
def test_takes_its_time():
    time.sleep(0.3)
"""


def scratch(
    pytester: pytest.Pytester,
    tests: str,
    *,
    timeout: float,
    budget: float,
    share: float = 0,
    where: str = "tests/test_scratch.py",
) -> None:
    """A tree with this repo's pytest configuration, these limits, and one test file."""
    ini = dict(
        MANIFEST["tool"]["pytest"]["ini_options"],
        timeout=timeout,
        suite_budget=budget,
        timeout_warn_share=share,
    )
    lines = "".join(f"{key} = {json.dumps(value)}\n" for key, value in ini.items())
    pytester.makepyprojecttoml(f"[tool.pytest.ini_options]\n{lines}")
    pytester.makeconftest((REPO / "conftest.py").read_text(encoding="utf-8"))
    path = pytester.path / where
    path.parent.mkdir(parents=True)
    path.write_text(tests, encoding="utf-8")


def slow_lane() -> list[str]:
    """The arguments `pixi run test-slow` hands pytest."""
    command = shlex.split(MANIFEST["tool"]["pixi"]["tasks"]["test-slow"])
    assert command[0] == "pytest"
    return command[1:]


def test_a_suite_inside_its_budget_passes_and_says_so(pytester: pytest.Pytester) -> None:
    scratch(pytester, "def test_quick():\n    pass\n", timeout=1, budget=30)
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(["suite time: * s of its 30 s budget"])


class SlowFinish:
    """Session-finish work that runs before the budget's, as pytest's temp-folder clean-up does."""

    def pytest_sessionfinish(self) -> None:
        time.sleep(0.4)


def test_the_budget_stops_where_the_tests_end(pytester: pytest.Pytester) -> None:
    scratch(pytester, "def test_quick():\n    pass\n", timeout=1, budget=0.3)
    result = pytester.runpytest(plugins=[SlowFinish()])
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(["suite time: * s of its 0.3 s budget"])


# An unmarked test is not exempted by a parametrize id or a directory named `slow`.
@pytest.mark.parametrize("where", ["tests/test_scratch.py", "tests/slow/test_scratch.py"])
def test_a_suite_past_its_budget_fails_the_run(pytester: pytest.Pytester, where: str) -> None:
    tests = """
import time

import pytest


@pytest.mark.parametrize("case", ["slow"])
def test_sleeps(case):
    time.sleep(0.3)
"""
    scratch(pytester, tests, timeout=1, budget=0.1, where=where)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(["suite time: * s, over its 0.1 s budget*"])


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_a_test_past_the_timeout_fails_in_any_phase(pytester: pytest.Pytester, phase: str) -> None:
    tests = f"""
import time

import pytest


@pytest.fixture
def phases():
    if "{phase}" == "setup":
        time.sleep(0.5)
    yield
    if "{phase}" == "teardown":
        time.sleep(0.5)


def test_sleeps(phases):
    if "{phase}" == "call":
        time.sleep(0.5)
"""
    scratch(pytester, tests, timeout=0.1, budget=30)
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(["*Timeout*"])


def test_a_slow_test_is_deselected_by_default(pytester: pytest.Pytester) -> None:
    scratch(pytester, SLOW_TEST + "\n\ndef test_quick():\n    pass\n", timeout=0.1, budget=0.2)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1, deselected=1)
    assert result.ret == pytest.ExitCode.OK


def test_the_slow_lane_holds_a_slow_test_to_neither_limit(pytester: pytest.Pytester) -> None:
    scratch(pytester, SLOW_TEST, timeout=0.1, budget=0.2)
    result = pytester.runpytest(*slow_lane())
    result.assert_outcomes(passed=1)
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(["suite time: not checked, because slow tests ran"])


def test_the_slow_lane_passes_and_says_so_when_no_test_is_slow(pytester: pytest.Pytester) -> None:
    scratch(pytester, "def test_quick():\n    pass\n", timeout=1, budget=30)
    result = pytester.runpytest(*slow_lane())
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(["no test is marked slow"])


@pytest.mark.parametrize(
    ("tests", "args"),
    [("", []), ("def test_quick():\n    pass\n", ["-k", "matches_nothing"])],
    ids=["empty suite", "unmatched -k"],
)
def test_any_other_run_that_collects_nothing_still_fails(
    pytester: pytest.Pytester, tests: str, args: list[str]
) -> None:
    scratch(pytester, tests, timeout=1, budget=30)
    result = pytester.runpytest(*args)
    assert result.ret == pytest.ExitCode.NO_TESTS_COLLECTED


# Neither phase alone crosses the share of the timeout; the two together do.
NEAR_THE_TIMEOUT = """
import time

import pytest


@pytest.fixture
def setup_half():
    time.sleep(0.15)


def test_near_the_limit(setup_half):
    time.sleep(0.15)
"""

NAMED = "*test_scratch.py::test_near_the_limit: 0.* s of its 0.5 s timeout"


def test_a_test_past_the_share_of_the_timeout_is_named_and_passes(
    pytester: pytest.Pytester,
) -> None:
    scratch(pytester, NEAR_THE_TIMEOUT, timeout=0.5, budget=30, share=0.4)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(["*over 40% of the 0.5 s timeout*", NAMED])


def test_a_test_under_the_share_is_not_named(pytester: pytest.Pytester) -> None:
    scratch(pytester, NEAR_THE_TIMEOUT, timeout=1, budget=30, share=0.4)
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.OK
    result.stdout.no_fnmatch_line("*of its * s timeout")


def test_a_slow_test_is_not_named(pytester: pytest.Pytester) -> None:
    slow = NEAR_THE_TIMEOUT.replace("def test_near", "@pytest.mark.slow\ndef test_near")
    scratch(pytester, slow, timeout=0.5, budget=30, share=0.4)
    result = pytester.runpytest(*slow_lane())
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*of its * s timeout")


def test_a_share_of_0_warns_of_nothing(pytester: pytest.Pytester) -> None:
    scratch(pytester, NEAR_THE_TIMEOUT, timeout=0.5, budget=30, share=0)
    result = pytester.runpytest()
    assert result.ret == pytest.ExitCode.OK
    result.stdout.no_fnmatch_line("*of its * s timeout")
