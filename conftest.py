"""The suite budget and the slow lane.

`suite_budget` in `[tool.pytest.ini_options]` is the most seconds a run may take, and
`timeout`, read by pytest-timeout, the most one test may take. A test marked `slow` is held
to neither, and the default run deselects it.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

SLOW = "slow"
# What a `slow` test's reports carry. The marker itself, not `report.keywords`, which also holds
# parametrize ids and folder names; xdist carries `user_properties` from worker to controller.
SLOW_PROPERTY = (SLOW, True)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Tag each report of a `slow` test with `SLOW_PROPERTY`."""
    report = yield
    if item.get_closest_marker(SLOW):
        report.user_properties.append(SLOW_PROPERTY)
    return report


class SuiteBudget:
    """Times one run and fails it when that is over budget; a run with a `slow` test is not timed.

    Workers run slow tests side by side, so no sum of their durations can be taken off the wall
    time.
    """

    def __init__(self, budget: float) -> None:
        self.budget = budget
        self.started = time.perf_counter()
        self.slow = False
        self.over = False
        self.verdict = ""

    def pytest_sessionstart(self) -> None:
        """Start the clock where pytest starts its own."""
        self.started = time.perf_counter()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Note that a `slow` test ran."""
        if SLOW_PROPERTY in report.user_properties:
            self.slow = True

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        """Fail a run with no `slow` test that took longer than its budget."""
        if self.slow:
            self.verdict = "suite time: not checked, because slow tests ran"
            return
        took = time.perf_counter() - self.started
        self.over = took > self.budget
        if not self.over:
            self.verdict = f"suite time: {took:.1f} s of its {self.budget:g} s budget"
            return
        self.verdict = (
            f"suite time: {took:.1f} s, over its {self.budget:g} s budget. "
            "Find the slowest tests with --durations=10, then make them faster or mark them slow."
        )
        if session.exitstatus == pytest.ExitCode.OK:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Print the time against the budget."""
        terminalreporter.write_line(self.verdict, red=self.over, bold=self.over)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register `suite_budget`."""
    parser.addini(
        "suite_budget",
        "Most seconds a run without slow tests may take. 0 or unset: no budget.",
        type="float",
        default=0.0,
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the `slow` marker, and the budget when one is set."""
    config.addinivalue_line(
        "markers",
        f"{SLOW}: exempt from timeout and suite_budget, and deselected unless -m {SLOW}",
    )
    budget = config.getini("suite_budget")
    # The controller alone: an xdist worker times only its share of the run.
    if budget and not hasattr(config, "workerinput"):
        config.pluginmanager.register(SuiteBudget(budget), "suite-budget")


def pytest_timeout_set_timer(item: pytest.Item) -> bool | None:
    """Set no timer for a `slow` test; pytest-timeout sets one for every other."""
    return True if item.get_closest_marker(SLOW) else None
