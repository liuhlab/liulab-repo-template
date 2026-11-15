"""The suite budget and the slow lane.

`suite_budget` in `[tool.pytest.ini_options]` is the most seconds a run may take, and
`timeout`, read by pytest-timeout, the most one test may take. A test marked `slow` is held
to neither, and the default run deselects it.
"""

from __future__ import annotations

import time

import pytest

SLOW = "slow"


class SuiteBudget:
    """Times one run, less its `slow` tests, and fails it when that is over budget."""

    def __init__(self, budget: float) -> None:
        self.budget = budget
        self.started = time.perf_counter()
        self.slow = 0.0
        self.verdict = ""

    def pytest_sessionstart(self) -> None:
        """Start the clock where pytest starts its own."""
        self.started = time.perf_counter()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Count a `slow` test's setup, call and teardown, so the budget leaves them out."""
        if SLOW in report.keywords:
            self.slow += report.duration

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        """Fail a run that took longer than its budget."""
        took = time.perf_counter() - self.started - self.slow
        excluded = f" ({self.slow:.1f} s of slow tests not counted)" if self.slow else ""
        if took <= self.budget:
            self.verdict = f"suite time: {took:.1f} s of its {self.budget:g} s budget{excluded}"
            return
        self.verdict = (
            f"suite time: {took:.1f} s, over its {self.budget:g} s budget{excluded}. "
            "Find the slowest tests with --durations=10, then make them faster or mark them slow."
        )
        if session.exitstatus == pytest.ExitCode.OK:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Print the time against the budget."""
        over = "over its" in self.verdict
        terminalreporter.write_line(self.verdict, red=over, bold=over)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register `suite_budget`."""
    parser.addini(
        "suite_budget",
        "Most seconds a run may take, slow tests excluded. 0 or unset: no budget.",
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
    if budget:
        config.pluginmanager.register(SuiteBudget(budget), "suite-budget")


def pytest_timeout_set_timer(item: pytest.Item) -> bool | None:
    """Set no timer for a `slow` test; pytest-timeout sets one for every other."""
    return True if item.get_closest_marker(SLOW) else None
