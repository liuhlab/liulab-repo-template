"""Negative tests for `scripts/conformance.py` — one tree per rule that VIOLATES it.

A rule that checks nothing passes the happy path, and a gate that fires on nothing looks exactly
like a gate that passes. That already happened once here: overlapping Vale globs left every ADR
checked by no rule at all, with zero alerts and green CI. So the claim these tests make is not
"the template conforms" — `pixi run check` already says that — but "each rule can still fail".

Every test builds a tmp_path tree that is correct in every respect but one, and asserts the run
marks THAT rule FAIL and names the offending file. The rule name alone would prove nothing: the
status table prints all eleven names on every run, passing or failing, so the assertions
read the status word out of the table rather than grepping the output for a name.

Conformance is invoked as a SUBPROCESS, so what is under test is the command an agent runs and
CI runs, not an internal function that could be refactored into something the command no longer
calls.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CONFORMANCE = REPO / "scripts" / "conformance.py"
INSTALLER = REPO / "skills" / "install.py"

# Spelled in two pieces for the same reason `conformance.py` spells it that way: `init-repo`
# substitutes the placeholder through the whole tree and the dogfood job then greps a rendered
# repo for it. A literal here would be rewritten, and would be found.
PLACEHOLDER = "new" + "pkg"

FRONT_MATTER = "---\nsearch:\n  exclude: true\n---\n\n"

PYPROJECT = """\
[project]
name = "example"

[tool.liulab.agent-docs]
"AGENTS.md" = "LengthDoc"
"CONTEXT.md" = "LengthDoc"
"docs/agents/" = "LengthDoc"
"skills/" = "LengthDoc"
"docs/adr/" = "LengthAdr"
"docs/research/" = false

[tool.liulab.waived]
"""

# Four sections, every Length rule named in every one, exactly as the real `.vale.ini` does and
# for the same reason: Vale accumulates per-rule settings across the sections that match a file.
VALE_INI = """\
StylesPath = styles
MinAlertLevel = error

[{README.md,CHANGELOG.md,docs/**/*.md}]
BasedOnStyles = Lab
Lab.LengthDoc = NO
Lab.LengthAdr = NO

[{AGENTS.md,CONTEXT.md,docs/agents/**/*.md,skills/**/SKILL.md}]
BasedOnStyles = Lab
Lab.LengthDoc = YES
Lab.LengthAdr = NO

[docs/adr/**/*.md]
BasedOnStyles = Lab
Lab.LengthDoc = NO
Lab.LengthAdr = YES

[docs/research/**/*.md]
BasedOnStyles = Lab
Lab.LengthDoc = NO
Lab.LengthAdr = NO
"""

# The nav is NESTED, which the template's is not. A flat walk would pass every one of these tests
# and let an agent-facing page into a derived repo's navbar.
MKDOCS = """\
site_name: example
nav:
  - Home: index.md
  - Reference:
      - API: api.md
"""

_STATUS_RE = re.compile(
    r"^\s+(?:rule|warn) \d+\s+(?P<name>\S+)\s+(?P<status>ok|FAIL|--|warn|waived)(\s|$)"
)


def write(root: Path, rel: str, text: str) -> Path:
    """Put one file in the tree, making its parents."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def add_skill(root: Path, name: str) -> None:
    """A skill and both committed discovery symlinks, relative, as `install.py` writes them."""
    write(root, f"skills/{name}/SKILL.md", f"---\nname: {name}\n---\n\n# {name}\n")
    for discovery in (".claude/skills", ".agents/skills"):
        link = root / discovery / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(f"../../skills/{name}", target_is_directory=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A tree that passes every rule, for one test to break in exactly one way.

    It has no `src/` and no release workflow, so rule 8's two conditionals are both vacuous here;
    the tests that care add the premise. It has no `skills/init-repo/`, so rule 1 and warning 9
    are both live — the state a derived repo is in, and the only state where they check anything.
    """
    root = tmp_path / "repo"
    write(root, "pyproject.toml", PYPROJECT)
    write(root, ".vale.ini", VALE_INI)
    write(root, "mkdocs.yml", MKDOCS)
    write(root, "AGENTS.md", "# example\n\nWhat this repo is and how to work in it.\n")
    write(root, "CONTEXT.md", "# Context\n\n## Glossary\n\n### Term\n\nWhat the word means here.\n")
    write(root, "docs/index.md", "# example\n\nThe front page.\n")
    write(root, "docs/api.md", "# API\n\nThe reference.\n")
    write(root, "docs/agents/writing.md", f"{FRONT_MATTER}# Writing rules\n\nBe concise.\n")
    write(root, "docs/adr/0001-a-decision.md", f"{FRONT_MATTER}# A decision\n\nWe chose this.\n")
    write(root, "docs/research/a-note.md", f"{FRONT_MATTER}# A note\n\nWhat was found.\n")
    # The real installer, not a stand-in: rule 7 delegates to this file, so a copy of it is what
    # makes the delegation the thing under test.
    (root / "skills").mkdir(parents=True, exist_ok=True)
    shutil.copy(INSTALLER, root / "skills" / "install.py")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    return root


def conformance(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the checker over one tree, the way a person and CI run it.

    `git add -A` first, because every rule reads `git ls-files`: until a fixture's edit is staged
    it does not exist as far as conformance is concerned. Nothing is committed — no rule reads
    history, and a commit would need an identity this environment may not have.
    """
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    return subprocess.run(
        [sys.executable, str(CONFORMANCE), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def statuses(proc: subprocess.CompletedProcess[str]) -> dict[str, str]:
    """The verdict the run gave each rule, read off its own status table.

    Asserting on the status word rather than on the presence of a rule NAME is the point: the
    table prints all eleven names on every run, so `"repo-shape" in output` is true of a green
    run and would prove nothing at all.
    """
    found: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        match = _STATUS_RE.match(line)
        if match:
            found[match["name"]] = match["status"]
    return found


def flat(text: str) -> str:
    """One long line, so an assertion is not hostage to where a note happened to wrap."""
    return " ".join(text.split())


def test_the_fixture_tree_passes_every_rule(repo: Path) -> None:
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    verdicts = statuses(proc)
    assert set(verdicts) == {
        "placeholder-rename",
        "agent-docs-unpublished",
        "vale-length-sections",
        "glossary-entry-length",
        "skill-file-location",
        "skill-name-prefix",
        "skill-symlinks",
        "repo-shape",
        "init-sentinel",
        "python-version-agreement",
        "waivers",
    }
    assert verdicts["placeholder-rename"] == "ok"  # live, not gated off
    assert verdicts["agent-docs-unpublished"] == "ok"
    assert verdicts["vale-length-sections"] == "ok"


def test_a_tree_that_has_skills_passes_every_rule(repo: Path) -> None:
    # The worktree this was written in had no skills, so the rules that read `skills/` would have
    # been vacuous in every other test here. This is the tree they are written for.
    add_skill(repo, "template-dev")
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    verdicts = statuses(proc)
    assert verdicts["skill-file-location"] == "ok"
    assert verdicts["skill-name-prefix"] == "ok"
    assert verdicts["skill-symlinks"] == "ok"
    assert "1 skill" in proc.stdout


def test_rule_1_fires_on_a_tracked_placeholder(repo: Path) -> None:
    write(repo, "README.md", f"# liulab-{PLACEHOLDER}\n\nA repo that was never renamed.\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["placeholder-rename"] == "FAIL"
    assert f"README.md still names `{PLACEHOLDER}` in its contents" in proc.stderr


def test_rule_1_fires_on_a_placeholder_in_a_path_not_only_in_a_file(repo: Path) -> None:
    # A `py.typed` under the placeholder module holds no text to grep. The directory name is
    # the whole violation. (Spelled around, not out: rule 1 greps this file too.)
    write(repo, f"src/{PLACEHOLDER}/py.typed", "")
    write(repo, "tests/test_it.py", "def test_it() -> None:\n    assert True\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["placeholder-rename"] == "FAIL"
    assert f"src/{PLACEHOLDER}/py.typed still names `{PLACEHOLDER}` in its path" in proc.stderr


def test_rule_1_is_not_checked_while_the_init_skill_is_there(repo: Path) -> None:
    # The template ships the placeholder ON PURPOSE, and `skills/init-repo/` is what says the
    # rename has not happened yet. Same discriminator warning 9 uses.
    write(repo, "README.md", f"# liulab-{PLACEHOLDER}\n\nStill the template.\n")
    add_skill(repo, "init-repo")
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["placeholder-rename"] == "--"
    assert "not checked: skills/init-repo/ is here" in flat(proc.stdout)


def test_rule_1_refuses_to_be_waived(repo: Path) -> None:
    write(repo, "README.md", f"# liulab-{PLACEHOLDER}\n\nA repo that was never renamed.\n")
    write(
        repo,
        "pyproject.toml",
        PYPROJECT + 'placeholder-rename = "we like the name"\n',
    )
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["placeholder-rename"] == "FAIL"
    assert "cannot be waived" in proc.stderr
    assert "REFUSED" in proc.stdout  # and warning 10 still prints it


def test_rule_2_fires_on_a_page_that_is_not_excluded_from_search(repo: Path) -> None:
    write(repo, "docs/agents/writing.md", "# Writing rules\n\nBe concise.\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["agent-docs-unpublished"] == "FAIL"
    assert "docs/agents/writing.md has no `search: exclude: true` front matter" in proc.stderr


def test_rule_2_fires_on_an_agent_page_in_the_nav(repo: Path) -> None:
    # Nav paths are relative to `docs_dir`, so `adr/0001-a-decision.md` here IS
    # `docs/adr/0001-a-decision.md` in `git ls-files`. Compare the two without that prefix and
    # the rule passes vacuously — which is the failure this whole file exists to catch.
    write(repo, "mkdocs.yml", MKDOCS + "      - ADR: adr/0001-a-decision.md\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["agent-docs-unpublished"] == "FAIL"
    assert (
        "docs/adr/0001-a-decision.md appears in mkdocs.yml nav as `adr/0001-a-decision.md`"
        in proc.stderr
    )


def test_rule_2_follows_a_docs_dir_the_site_moved(repo: Path) -> None:
    write(
        repo, "mkdocs.yml", "site_name: example\ndocs_dir: site-source\nnav:\n  - Home: index.md\n"
    )
    proc = conformance(repo)
    # Nothing under `site-source/` is declared agent-facing, so the rule has nothing to check —
    # and says so, rather than reporting a green it did not earn.
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["agent-docs-unpublished"] == "--"
    assert "not checked: no [tool.liulab.agent-docs] key is under site-source/" in flat(proc.stdout)


def test_rule_3_fires_when_a_section_turns_the_declared_cap_off(repo: Path) -> None:
    # The config this reproduces is not hypothetical: it is what left the ADRs checked by
    # nothing. Every rule is present, so asserting mere presence would call this green.
    write(repo, ".vale.ini", VALE_INI.replace("Lab.LengthDoc = YES", "Lab.LengthDoc = NO"))
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["vale-length-sections"] == "FAIL"
    assert "should set Lab.LengthDoc on for `AGENTS.md`, and says `NO`" in proc.stderr


def test_rule_3_fires_when_a_key_has_no_section_at_all(repo: Path) -> None:
    truncated = VALE_INI.split("[docs/adr/**/*.md]")[0]
    write(repo, ".vale.ini", truncated)
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["vale-length-sections"] == "FAIL"
    assert "`docs/adr/` is spelled in 0 .vale.ini section header(s), not 1" in proc.stderr


def test_rule_3_does_not_require_a_key_for_every_header_token(repo: Path) -> None:
    # `CHANGELOG.md` is named in section 1 and is not an agent-docs key. A rule written from the
    # headers inward rather than from the keys outward would fail this tree.
    write(repo, "CHANGELOG.md", "# Changelog\n\nNothing yet.\n")
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["vale-length-sections"] == "ok"


def test_rule_4_fires_on_an_overlong_glossary_entry(repo: Path) -> None:
    body = " ".join(["word"] * 250)
    write(repo, "CONTEXT.md", f"# Context\n\n## Glossary\n\n### Long term\n\n{body}\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["glossary-entry-length"] == "FAIL"
    assert "CONTEXT.md glossary entry `Long term` is 252 words, over 200" in proc.stderr


def test_rule_4_caps_each_entry_and_not_the_file(repo: Path) -> None:
    # Four entries, 150 words each: 600 words of glossary, and no violation. The cap is per
    # entry so a large vocabulary is not punished for the size of its domain.
    body = " ".join(["word"] * 150)
    entries = "".join(f"### Term {n}\n\n{body}\n\n" for n in range(4))
    write(repo, "CONTEXT.md", f"# Context\n\n## Glossary\n\n{entries}")
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["glossary-entry-length"] == "ok"


def test_rule_5_fires_on_a_skill_file_the_installer_cannot_see(repo: Path) -> None:
    write(repo, "docs/SKILL.md", "# A skill in the wrong place\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["skill-file-location"] == "FAIL"
    assert "docs/SKILL.md is a SKILL.md outside skills/<name>/" in proc.stderr


def test_rule_6_fires_on_a_skill_that_shadows_the_shared_plugin(repo: Path) -> None:
    # Correctly installed in both discovery paths, so rule 7 is green and the NAME is the only
    # thing wrong — which is the point: this one is invisible to every other check.
    add_skill(repo, "lab-hpc")
    proc = conformance(repo)
    assert proc.returncode == 1
    verdicts = statuses(proc)
    assert verdicts["skill-name-prefix"] == "FAIL"
    assert verdicts["skill-symlinks"] == "ok"
    assert "is a repo-local skill named `lab-hpc`" in proc.stderr


def test_rule_7_delegates_to_the_installer(repo: Path) -> None:
    # A skill with no symlinks. The assertion is not just that rule 7 fails but that the
    # installer's OWN report comes through, fix line included — proof the rule delegates rather
    # than reimplementing three invariants that would then drift from the installer's.
    write(repo, "skills/demo/SKILL.md", "---\nname: demo\n---\n\n# demo\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["skill-symlinks"] == "FAIL"
    assert ".claude/skills/demo is missing" in proc.stderr
    assert "fix: python skills/install.py --target claude" in proc.stderr


def test_rule_8_fires_on_a_package_with_no_tests(repo: Path) -> None:
    write(repo, "src/example/__init__.py", "")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["repo-shape"] == "FAIL"
    assert "src/ is tracked and tests/ is not" in proc.stderr


def test_rule_8_fires_on_a_release_workflow_with_no_changelog(repo: Path) -> None:
    write(repo, ".github/workflows/release.yml", "on:\n  release:\n    types: [published]\n")
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["repo-shape"] == "FAIL"
    assert ".github/workflows/release.yml is tracked and CHANGELOG.md is not" in proc.stderr


def test_rule_8_is_vacuous_and_not_failing_when_neither_premise_holds(repo: Path) -> None:
    # One lab repo has neither `src/` nor `tests/`. A repo with no package is not a repo that
    # failed to have tests, and the run has to say it checked nothing rather than report a green.
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["repo-shape"] == "--"
    assert "not checked: no tracked src/, so tests/ is not required" in flat(proc.stdout)
    assert "no .github/workflows/release.yml, so CHANGELOG.md is not required" in flat(proc.stdout)


def test_rule_8_is_satisfied_and_not_merely_skipped_when_both_premises_hold(repo: Path) -> None:
    write(repo, "src/example/__init__.py", "")
    write(repo, "tests/test_it.py", "def test_it() -> None:\n    assert True\n")
    write(repo, ".github/workflows/release.yml", "on:\n  release:\n    types: [published]\n")
    write(repo, "CHANGELOG.md", "# Changelog\n\nNothing yet.\n")
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["repo-shape"] == "ok"


def test_warning_9_warns_about_the_sentinel_and_does_not_fail(repo: Path) -> None:
    write(
        repo,
        "AGENTS.md",
        "# example\n\n> **Replace this file.** Run `/init`, then delete this line.\n",
    )
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr  # a warning, never a failure
    assert statuses(proc)["init-sentinel"] == "warn"
    assert "AGENTS.md still carries the `/init` sentinel" in flat(proc.stdout)


def test_warning_9_is_silent_while_the_init_skill_is_the_nag(repo: Path) -> None:
    write(
        repo,
        "AGENTS.md",
        "# example\n\n> **Replace this file.** Run `/init`, then delete this line.\n",
    )
    add_skill(repo, "init-repo")
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["init-sentinel"] == "--"


def test_a_waiver_suppresses_its_rule_and_is_still_printed(repo: Path) -> None:
    body = " ".join(["word"] * 250)
    write(repo, "CONTEXT.md", f"# Context\n\n## Glossary\n\n### Long term\n\n{body}\n")
    reason = "the domain needs one long entry, tracked in issue 41"
    write(repo, "pyproject.toml", PYPROJECT + f'glossary-entry-length = "{reason}"\n')
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["glossary-entry-length"] == "waived"
    assert f"1 problem(s) suppressed: {reason}" in flat(proc.stdout)
    # and warning 10 prints it a second time, in the waiver table
    assert f"glossary-entry-length: 1 problem(s) suppressed — {reason}" in flat(proc.stdout)


def test_every_waiver_is_printed_on_a_green_run_too(repo: Path) -> None:
    # An escape hatch that stops being visible becomes permanent, so a waiver suppressing nothing
    # is printed exactly as loudly as one suppressing a failure.
    reason = "this repo has no package"
    write(repo, "pyproject.toml", PYPROJECT + f'repo-shape = "{reason}"\n')
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert f"repo-shape: 0 problem(s) suppressed — {reason}" in flat(proc.stdout)


def test_a_waiver_naming_no_rule_says_so(repo: Path) -> None:
    write(repo, "pyproject.toml", PYPROJECT + 'no-such-rule = "a rule that was renamed"\n')
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "no-such-rule: matches no rule, so it waives nothing" in flat(proc.stdout)


def test_every_failure_is_reported_and_not_just_the_first(repo: Path) -> None:
    # `check.sh` collects every step and conformance collects every rule, for the same reason:
    # one run has to tell you everything to fix.
    write(repo, "docs/agents/writing.md", "# Writing rules\n\nBe concise.\n")
    write(repo, "docs/SKILL.md", "# A skill in the wrong place\n")
    write(repo, "src/example/__init__.py", "")
    proc = conformance(repo)
    assert proc.returncode == 1
    verdicts = statuses(proc)
    assert verdicts["agent-docs-unpublished"] == "FAIL"
    assert verdicts["skill-file-location"] == "FAIL"
    assert verdicts["repo-shape"] == "FAIL"
    assert "3 of 9 rules failed" in proc.stderr


def pyproject_python(
    *,
    floor: str | None = None,
    pin: str | None = None,
    feature_pin: str | None = None,
    ruff: str | None = None,
    pyright: str | None = None,
) -> str:
    """The fixture's pyproject plus whichever Python declarations one test wants.

    A builder rather than five literals because rule 10 is about the COMBINATION: every test
    below differs only in which sites it fills in and what each of them says.
    """
    text = PYPROJECT
    if floor is not None:
        text = text.replace('name = "example"', f'name = "example"\nrequires-python = "{floor}"')
    if pin is not None:
        text += f'\n[tool.pixi.dependencies]\npython = "{pin}"\n'
    if feature_pin is not None:
        text += f'\n[tool.pixi.feature.floor.dependencies]\npython = "{feature_pin}"\n'
    if ruff is not None:
        text += f'\n[tool.ruff]\ntarget-version = "{ruff}"\n'
    if pyright is not None:
        text += f'\n[tool.pyright]\npythonVersion = "{pyright}"\n'
    return text


def test_rule_10_is_vacuous_when_the_repo_pins_no_interpreter(repo: Path) -> None:
    # The fixture declares no Python at all. With no pinned interpreter there is nothing for the
    # other declarations to agree WITH, so the run has to say it checked nothing.
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["python-version-agreement"] == "--"
    assert "not checked: no `python` in [tool.pixi.dependencies] or in any pixi feature" in flat(
        proc.stdout
    )


def test_rule_10_passes_on_a_floor_and_a_pin_that_agree(repo: Path) -> None:
    # Two declarations, which is what the template ships: ruff takes its target from the floor
    # and pyright takes its version from the interpreter, so neither writes a level down.
    write(repo, "pyproject.toml", pyproject_python(floor=">=3.13", pin="3.13.*"))
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["python-version-agreement"] == "ok"
    assert "2 declaration(s)" in flat(proc.stdout)


def test_rule_10_passes_when_four_declarations_agree(repo: Path) -> None:
    # Writing the derived levels down is allowed; disagreeing with the floor is not. A rule that
    # counted declarations would fail this tree, and this tree is fine.
    write(
        repo,
        "pyproject.toml",
        pyproject_python(floor=">=3.13", pin="3.13.*", ruff="py313", pyright="3.13"),
    )
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["python-version-agreement"] == "ok"
    assert "4 declaration(s)" in flat(proc.stdout)


def test_rule_10_fires_when_a_tool_holds_a_level_the_floor_does_not(repo: Path) -> None:
    write(
        repo,
        "pyproject.toml",
        pyproject_python(floor=">=3.13", pin="3.13.*", ruff="py312", pyright="3.13"),
    )
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["python-version-agreement"] == "FAIL"
    assert (
        "[tool.ruff] target-version `py312` says 3.12, and [project] requires-python `>=3.13` "
        "says 3.13" in proc.stderr
    )
    # Named the site, what it says, and what it should say instead.
    assert 'write `target-version = "py313"`' in flat(proc.stderr)


def test_rule_10_fires_on_a_pin_below_the_floor(repo: Path) -> None:
    # The other direction: the repo runs an interpreter its own metadata refuses to install on.
    write(repo, "pyproject.toml", pyproject_python(floor=">=3.13", pin="3.12.*"))
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["python-version-agreement"] == "FAIL"
    assert (
        "[tool.pixi.dependencies] python `3.12.*` pins 3.12, below the [project] requires-python "
        "floor `>=3.13`" in proc.stderr
    )


def test_rule_10_measures_a_tool_against_the_pin_when_there_is_no_floor(repo: Path) -> None:
    write(repo, "pyproject.toml", pyproject_python(pin="3.13.*", ruff="py312"))
    proc = conformance(repo)
    assert proc.returncode == 1
    assert statuses(proc)["python-version-agreement"] == "FAIL"
    assert "[tool.pixi.dependencies] python `3.13.*` says 3.13" in proc.stderr


def test_rule_10_passes_a_range_that_pixi_actually_resolves(repo: Path) -> None:
    # The case the rule exists to leave alone: a repo supporting 3.10 through 3.13 on purpose. The
    # floor is below the default pin, the tools are held to the floor, and a feature gives 3.10 an
    # environment — so the range is a claim pixi resolves rather than one nothing exercises.
    write(
        repo,
        "pyproject.toml",
        pyproject_python(
            floor=">=3.10", pin="3.13.*", feature_pin="3.10.*", ruff="py310", pyright="3.10"
        ),
    )
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["python-version-agreement"] == "ok"
    assert "the floor 3.10 is itself pinned, so pixi resolves it" in flat(proc.stdout)


def test_rule_10_says_it_cannot_tell_a_range_from_a_floor_nobody_lowered(repo: Path) -> None:
    # Copied from a real Liu Lab repo, which carried exactly this: a >=3.12 floor, a 3.13 pin,
    # ruff and pyright at 3.12, and a lockfile holding only 3.13. The declarations AGREE — the
    # tools are at the floor, which is what a deliberate range looks like — so the rule does not
    # fail it. What it must not do is call that a clean pass in silence: nothing pins 3.12, so the
    # promise of 3.12 support is exercised by nothing, and the notes say so on every run.
    write(
        repo,
        "pyproject.toml",
        pyproject_python(floor=">=3.12", pin="3.13.*", ruff="py312", pyright="3.12"),
    )
    proc = conformance(repo)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert statuses(proc)["python-version-agreement"] == "ok"
    printed = flat(proc.stdout)
    # Every site and what each one says, so the split is readable at a glance.
    for said in (
        "[project] requires-python `>=3.12`",
        "[tool.pixi.dependencies] python `3.13.*`",
        "[tool.ruff] target-version `py312`",
        "[tool.pyright] pythonVersion `3.12`",
    ):
        assert said in printed
    assert "not checked: whether 3.12 is ever resolved or tested" in printed
