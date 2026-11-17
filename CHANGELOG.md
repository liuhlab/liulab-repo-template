# Changelog

Every change worth knowing about, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers are CalVer tags
of the form `vYYYY.M.PATCH`, and the tag is where the version comes from — nothing here
sets one.

## [Unreleased]

### Added

- Limits on test time. One test may take 2 s (`timeout`, read by pytest-timeout) and the whole
  run 45 s (`suite_budget`, read by a small plugin in `conftest.py`, which prints the run's
  time against it every time). A test marked `slow` is held to neither: the default run leaves
  it out, and `pixi run test-slow` runs it. pytest-timeout's own session timeout was not used,
  because it stops the run part-way and cannot leave the slow lane out. A conformance rule keeps
  both limits in `[tool.pytest.ini_options]`: it fails a `PYTEST_TIMEOUT` or a `--timeout` in a
  workflow or in a task that runs pytest, and a timeout mark on a test.
- The placeholder package, the pixi workspace, and the three environments.
- `scripts/check.sh`, the gate runner behind `pixi run check`: it runs every static step
  concurrently and reports all failures, not just the first. A step that passes is shown
  as a short tail and one that fails in full, the summary says how long each step took,
  and a run stopped with Ctrl-C takes its steps down with it.
- The writing gate: `vale` and `markdownlint` as steps of `check-static`, with the four
  `Lab` rules tracked in `styles/Lab/`.
- The three workflows: `ci.yml` runs the gate on every pull request, `docs.yml` publishes
  the site to `gh-pages`, and `release.yml` publishes to PyPI when a Release is published.
- `scripts/init_repo.py`, the half of `init-repo` a script can do: it renames the
  placeholder, cuts the lanes a new repo said it does not want, deletes the template's own
  files, and tags `v0.0.0`. It asks first about anything you have already edited.
- The `dogfood` job, which renders this template for all three shapes on every pull
  request and proves each new repo passes its own checks and builds its own site.
- A conformance rule that fails a publishing workflow a tag push can trigger, and the
  workflow reader it is built on: the check now parses every workflow file, its triggers
  and its steps, instead of only reading text.
- A conformance rule that fails a repo where a second resolver has been set up: a
  `poetry.lock`, `uv.lock`, `pdm.lock` or `Pipfile` anywhere in the tree, or a `[tool.poetry]`,
  `[tool.uv]` or `[tool.pdm]` table in `pyproject.toml`. Two resolvers can disagree quietly,
  and what one of them installs is not what the gate runs in.
- A conformance rule for the Python version. The pixi pin has to meet the
  `requires-python` floor, and any tool that writes a language level down has to write that
  floor. It checks that the declarations agree, and does not count them, so a repo that
  supports a range of Python versions still passes.
- A conformance rule that fails a workflow step running a command of its own instead of
  `pixi run <task>`, or naming a task nothing declares. The step list stays in one place,
  so the command CI runs is one you can run too.
- `docs/template/index.md`, the page that says what the template ships and how to make a
  repo from it, and `mkdocs.template.yml`, which inherits `mkdocs.yml` and names the site
  after this repo while the shipped config keeps the placeholder. Both are template-only:
  `init-repo` deletes them, takes `-f mkdocs.template.yml` off the two docs tasks, and cuts
  the front page's pointer at the page.
- Docstring examples as tests. `pytest` collects the doctests in `src/` alongside `tests/`,
  so an example that has drifted from the code it documents fails the gate. Writing an
  example is voluntary; the ones that exist are checked. `docs/api.md` says how to mark a
  line that cannot run offline. Collecting `src/` imports it, so a module that needs an
  absent optional dependency costs one error instead of aborting the whole suite.
- A `validation:` block in `mkdocs.yml` turning on the five link checks the site builder
  ships switched off, and a comment beside it listing, from measurement, which broken links
  a strict build catches and which three it lets through. A `nav:` entry naming a file that
  is not there is one of the three, and no setting catches it.
- `reportMissingParameterType` beside the pyright mode, because `standard` does not check
  that a parameter is annotated at all — the bar was kept by discipline and nothing would
  have noticed a repo dropping it. Its sibling `reportUnknownParameterType` was considered
  and declined: it also fails parameters that *are* annotated when the type belongs to an
  untyped dependency, which is not a bar a lab repo can hold. `tests/` is scoped back to
  plain `standard`, because the rule fired on fixtures and `parametrize` arguments, where
  the annotation it asks for is a claim nothing compares to the fixture.
- A conformance rule that fails a `nav:` entry naming a file the repo does not track, or one
  that sits outside the site source. That is the broken site the builder does not validate
  at all — it reports no issues, exits 0, and publishes a menu item that 404s — so the check
  had to go somewhere it could be one. It reads every site config, so a repo building more
  than one site from one docs tree has both navs checked.

### Changed

- CI skips a draft pull request and runs when it is marked ready, so a pull request opened as
  a draft and readied once the local gate passes runs CI once. Pushes to a ready pull request
  still run it, and so does a run started by hand.
- CI is one job, run on pull requests and by hand, and no longer on a push to `main`. GitHub
  bills each job rounded up to a whole minute, so five short jobs billed far more than one. Each
  step after the first runs even when an earlier one failed, so a run still reports every
  failure, and a new repo's branch ruleset requires that one `check`.
- A new repo no longer ships the template's tests of its own settings,
  `tests/test_conformance.py` and `tests/test_quoted_evidence.py`. They tested the template,
  not the new repo, and they made every test run there slower. The template keeps both and
  still runs them. A repo made earlier can delete both files, and drop any `--ignore` it
  added for them.
- The glossary is now `GLOSSARY.md`, the name the upstream skills read and write, and its
  conformance rule checks more. A repo whose glossary is still `CONTEXT.md`, or whose map is
  still `CONTEXT-MAP.md`, fails, and the fix is one `git mv`. The 200-word cap on each entry
  is unchanged. Where a `GLOSSARY-MAP.md` splits the glossary by context, the rule says it did
  not check it. It is now named `glossary-format`.
- The conformance rule about skill names now fails a repo skill that takes any name the `lab`
  plugin ships, not only one that starts with `lab-`. The plugin now ships upstream skills
  under their own names, and in Kimi Code a repo skill of the same name replaces the
  plugin's without a word. The names come from Claude Code's copy of the plugin on your
  machine. Where there is none, as in CI, only the `lab-` prefix is checked, and the rule
  says it did not check the rest. It is now named `skill-name-clash`, so a waiver under the
  old name waives nothing until you rename it.

- The conformance rule about a second resolver now looks for four things instead of eight: a
  `poetry.lock`, `uv.lock`, `pdm.lock` or `Pipfile`, and the three tables that configure those
  resolvers. It no longer says anything about `requirements.txt`, `environment.yml`, `setup.py`
  or `.pre-commit-config.yaml`, each of which was measured failing a repo doing correct work —
  a notebook that runs on Colab needs a requirements file and cannot run pixi, and the old
  advice was to delete it. The four that remain are files a resolver writes for itself, and
  they now fail wherever they sit rather than only at the top of the repo.
- The conformance rule about the publishing trigger now reads a tag filter instead of refusing
  every one. A `push:` with no branch filter and a `create:` still fail, because an absent
  filter is every ref and neither has a correct form. A `tags:` or `tags-ignore:` filter is
  read, and it fails only where it lets the first-day `v0.0.0` tag through — so `tags:
  ['v20*']`, which CalVer versions can never match, now passes. The rule reads one path,
  `.github/workflows/release.yml`, and its own report says so: the same trigger under another
  filename is outside it.
- The conformance rule about workflow steps now lets a step pass arguments to its task, after
  `--`, and prints them on every run instead of failing. The clause that forbade them had no
  failing fixture and was refuted by the fix it prescribed: moving the flag into a task of its
  own passes the rule, so the divergence it named was already allowed through the compliant
  path. A token after the task with no `--` still fails, because pixi reads it as its own
  option, and so does a shell operator anywhere after the task. The list of pixi options that
  take a separate value was measured off `pixi run --help` and had eight spellings of twelve
  options, so `pixi run -p linux-64 build` — a step that literally is `pixi run <task>` — was
  being told it ran a command.
- The conformance rule about `nav:` entries now resolves only the entries that name a page —
  ending `.md`, `.ipynb` or `.html` — and strips a trailing `#anchor` first. A directory entry,
  an `...`, and `guide.md#install` were each measured failing a correct site, and the fix printed
  for the second was "add docs/...". Whatever it did not resolve is listed in the notes, so a
  passed-over entry is visible rather than silently uncounted.
- A site configuration that declares a page-generating plugin — `gen-files`, `literate-nav`,
  `awesome-pages`, `macros` — now reports that rule not checked, with the reason. Such a repo had
  to waive the whole rule on first contact, and a waiver is per rule: one generated section
  turned the check off for every hand-written entry it exists to protect, dead links included.
- `ci.yml`'s header no longer says CI and a laptop cannot drift. The rule reads the `run:` line
  and nothing else, so `env:`, `working-directory:`, `shell:` and a local composite action can
  each change what a step does without changing that line. Those limits are now written down in
  the rule rather than implied away.
- `conformance` now exits 2 when it could not run at all: no `.git`, no `pyproject.toml`, or
  a `pyproject.toml` it cannot read. It still exits 1 when it ran and a rule failed, and 0
  when every rule passed. Both used to exit 1, so a bad checkout looked just like a repo that
  broke a rule. The two want opposite answers: one is a repo to fix, the other is a repo that
  nothing checked. `scripts/check.sh` already used 2 that way.

### Removed

- The pixi `test` environment. It had the same packages as `default`, and only a separate CI
  test job used it. CI is now one job that runs in `default`, so every new repo carried the
  environment and its part of `pixi.lock` for nothing.
- The pages on the issue tracker, the triage labels and the domain docs are gone from
  `docs/agents/`. A machine set up with `/lab-setup` gives every agent all three as lab
  defaults, so a new repo needs none of them. Write your own page only where your repo is
  different, and it replaces that one default and no other. The writing page stays, and so
  does the step that copies the lab's labels to a new repo.

### Fixed

- `nodejs` has a floor of 22 beside `markdownlint-cli2`. The conda package does not bound it, so
  a fresh solve on linux-64 paired the linter with a Node.js from 2019 that cannot run it. The
  floor is the minimum in the linter's own `engines.node`. `pixi.lock` is unchanged. A repo made
  earlier can copy the line.
- A new repo's README now names the lab's plugin as it is published:
  `/plugin marketplace add liuhlab/liulab-skills`, then `/plugin install lab@liulab`. The
  template's own README does too.
- No comment a new repo keeps cites an issue number from this template's tracker. Each says
  its reason in words, and the dogfood render now fails on a `(#NN)` in any file it keeps.
- `docs.yml` skips the deploy in a private repo, where a free plan cannot serve GitHub Pages. The
  closing checklist and the new README say the site is for a public repo.
- `pixi run check` now runs the tests when a static step fails, and exits non-zero if either
  failed. It used to stop at the first failing task, so one lint error hid every failing test.
  A repo made earlier with tests can copy the `check` line from this one.
- The glossary rule now measures a glossary written the way the `domain-modeling` skill writes
  it, and no longer fails it. A line that is only a bold term and a colon, `**Order**:`, starts
  an entry under any `##` section, and the entry runs to the next such line or the next
  heading. Each entry is held to the same 200-word cap as a `###` entry under `## Glossary`,
  which is still measured as before. A glossary in the skill's layout used to fail on every
  term line.
- A new repo with no package no longer describes tests it does not have. `init-repo` now cuts
  the test step from the gate in `AGENTS.md`: the words "plus `test`", the `test` row, and the
  four traps, which are all about pytest or typer. It also drops `mkdocstrings-python` from the
  docs environment and from `pixi.lock`. That repo's site has no API page, so nothing used it.
- `conformance` no longer passes a `[tool.liulab.agent-docs]` key that checks nothing. A key
  with `*`, `?` or `[` in it now fails, because keys are plain path prefixes and a pattern
  matches no file. Where the keys under the site source match no Markdown page, the check of
  those pages reports `--` (not checked) and names the keys, where it used to say `ok`.
- `init-repo` now makes the first commit and the `v0.0.0` tag under the name and email your
  git already has. It used to sign both as `init-repo <init-repo@localhost>` whatever git had,
  so every new repo began with a commit linked to no GitHub account. That stand-in is now used
  only when git has no name or no email, as on a fresh CI runner.
- The suite budget works under pytest-xdist. The process that reports a parallel run collects
  no tests, so it never learned which tests were marked `slow` and counted their time against
  the budget. A slow test's report now carries the mark. A run in which any slow test ran is
  not timed at all, and prints `suite time: not checked, because slow tests ran`, so a run of
  every test with `-m ""` is not timed either. Only the reporting process keeps a budget,
  not each worker. A repo made earlier can copy `conftest.py` from this one.
- The suite budget's clock stops when the last test ends. pytest deletes its old temporary
  folders after that, and on a machine that keeps many of them, the deletion used to push a
  local run past a budget that CI met.
- Marking a draft pull request ready right after a push now runs CI. The push and the ready
  event arrived in the same second, and the two runs shared one concurrency group, so the
  draft's run could cancel the real one and then skip itself, leaving no run at all. The draft
  state is now part of the group's key. A repo made earlier can copy the `concurrency:` block
  from `ci.yml` in this one.
