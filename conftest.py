"""The suite budget, the timeout warning and the slow lane.

`suite_budget` in `[tool.pytest.ini_options]` is the most seconds a run may take, and
`timeout`, read by pytest-timeout, the most one test may take, setup and teardown included. A
passing test that takes `near_timeout_share` of `timeout` or more is named in the summary, and
the run still passes, so a slower runner's margin shows before it fails the test. A test marked
`slow` is held to none of them: the default run deselects it, and a run in which one ran is not
timed. A `-m slow` run that finds no test marked `slow` passes.
"""

from __future__ import annotations

import time
from collections.abc import Generator

import pytest

SLOW = "slow"

#: Rides on a `slow` test's reports, which pytest-xdist carries from a worker to the controller.
SLOW_TAG = (SLOW, True)

#: Rides, the same way, on the reports of a test that `untimed` frees from `timeout`.
UNTIMED_TAG = ("untimed", True)


def untimed(item: pytest.Item) -> bool:
    """Whether pytest-timeout sets no timer for this test, and so whether it is never near one."""
    return item.get_closest_marker(SLOW) is not None


class SuiteBudget:
    """Times one run's tests, and fails the run when that is over budget, unless a `slow` test ran."""

    def __init__(self, budget: float) -> None:
        self.budget = budget
        self.started = time.perf_counter()
        self.ended: float | None = None
        self.slow_ran = False
        self.over = False
        self.verdict = ""

    def pytest_sessionstart(self) -> None:
        """Start the clock where pytest starts its own."""
        self.started = time.perf_counter()

    @pytest.hookimpl(wrapper=True)
    def pytest_runtestloop(self) -> Generator[None, object, object]:
        """Stop the clock where the tests end, so later session-finish work is not counted."""
        try:
            return (yield)
        finally:
            self.ended = time.perf_counter()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Note a `slow` test."""
        if SLOW_TAG in report.user_properties:
            self.slow_ran = True

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        """Fail a run that took longer than its budget."""
        if self.slow_ran:
            self.verdict = "suite time: not checked, because slow tests ran"
            return
        took = (self.ended or time.perf_counter()) - self.started
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


class NearTheTimeout:
    """Names each passing test that took a share of `timeout` or more, and never fails the run."""

    def __init__(self, timeout: float, share: float) -> None:
        self.timeout = timeout
        self.threshold = timeout * share
        self.took: dict[str, float] = {}
        self.failed: set[str] = set()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Sum a test's setup, call and teardown, which pytest-timeout times together."""
        # A subtest's report is a subclass, and its time is already inside the call's.
        if type(report) is not pytest.TestReport or UNTIMED_TAG in report.user_properties:
            return
        self.took[report.nodeid] = self.took.get(report.nodeid, 0.0) + report.duration
        if report.failed:
            self.failed.add(report.nodeid)

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Print one line for each test at or above the threshold, slowest first."""
        for test, took in sorted(self.took.items(), key=lambda pair: pair[1], reverse=True):
            if took >= self.threshold and test not in self.failed:
                terminalreporter.write_line(
                    f"near the timeout: {test} took {took:.2f} s, "
                    f"at or above {self.threshold:g} s of its {self.timeout:g} s",
                    yellow=True,
                )


class EmptySlowLane:
    """Turns "no tests collected" into a pass for a `-m slow` run when no test is marked `slow`."""

    def __init__(self) -> None:
        self.any_slow = False
        self.said = False

    @pytest.hookimpl(tryfirst=True)
    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        """Look at every collected test, before `-m` and `-k` deselect any."""
        self.any_slow = any(item.get_closest_marker(SLOW) for item in items)

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        """Pass a `-m slow` run that had no slow test to select."""
        if session.exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED and not self.any_slow:
            session.exitstatus = pytest.ExitCode.OK
            self.said = True

    def pytest_terminal_summary(self, terminalreporter: pytest.TerminalReporter) -> None:
        """Say why the run passed."""
        if self.said:
            terminalreporter.write_line(f"no test is marked {SLOW}")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register `suite_budget` and `near_timeout_share`."""
    parser.addini(
        "suite_budget",
        "Most seconds a run may take; a run in which a slow test ran is not timed. "
        "0 or unset: no budget.",
        type="float",
        default=0.0,
    )
    parser.addini(
        "near_timeout_share",
        "Share of timeout at which a passing test is named in the summary; the run still passes. "
        "0 or unset: no warning.",
        type="float",
        default=0.0,
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the `slow` marker, and the time-limit and slow-lane plugins off xdist's workers."""
    config.addinivalue_line(
        "markers",
        f"{SLOW}: exempt from the time limits and their warning, and deselected unless -m {SLOW}",
    )
    if hasattr(config, "workerinput"):
        return
    budget = config.getini("suite_budget")
    if budget:
        config.pluginmanager.register(SuiteBudget(budget), "suite-budget")
    share = config.getini("near_timeout_share")
    if share and float(config.getini("timeout") or 0):
        timeout = float(config.getini("timeout"))
        config.pluginmanager.register(NearTheTimeout(timeout, share), "near-the-timeout")
    if config.option.markexpr.replace(" ", "") == SLOW:
        config.pluginmanager.register(EmptySlowLane(), "empty-slow-lane")


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(
    item: pytest.Item,
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Tag the report of a `slow` test, and of one with no timer."""
    report = yield
    if item.get_closest_marker(SLOW):
        report.user_properties.append(SLOW_TAG)
    if untimed(item):
        report.user_properties.append(UNTIMED_TAG)
    return report


def pytest_timeout_set_timer(item: pytest.Item) -> bool | None:
    """Set no timer for an `untimed` test; pytest-timeout sets one for every other."""
    return True if untimed(item) else None
