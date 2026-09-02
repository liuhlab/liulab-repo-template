# Changelog

Every change worth knowing about, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Version numbers are CalVer tags
of the form `vYYYY.M.PATCH`, and the tag is where the version comes from — nothing here
sets one.

## [Unreleased]

### Added

- The placeholder package, the pixi workspace, and the three environments.
- `scripts/check.sh`, the gate runner behind `pixi run check`: it runs every static step
  concurrently and reports all failures, not just the first.
- The writing gate: `vale` and `markdownlint` as steps of `check-static`, with the four
  `Lab` rules tracked in `styles/Lab/`.
- The three workflows: `ci.yml` runs the gate on every pull request, `docs.yml` publishes
  the site to `gh-pages`, and `release.yml` publishes to PyPI when a Release is published.
- `scripts/init_repo.py`, the half of `init-repo` a script can do: it renames the
  placeholder, cuts the lanes a new repo said it does not want, deletes the template's own
  files, and tags `v0.0.0`. It asks first about anything you have already edited.
- The `dogfood` job, which renders this template for all three shapes on every pull
  request and proves each new repo passes its own checks and builds its own site.
- `docs/template/index.md`, the page that says what the template ships and how to make a
  repo from it, and `mkdocs.template.yml`, which inherits `mkdocs.yml` and names the site
  after this repo while the shipped config keeps the placeholder. Both are template-only:
  `init-repo` deletes them, takes `-f mkdocs.template.yml` off the two docs tasks, and cuts
  the front page's pointer at the page.
- Docstring examples as tests. `pytest` collects the doctests in `src/` alongside `tests/`,
  so an example that has drifted from the code it documents fails the gate. `docs/api.md`
  says how to mark a line that cannot run offline.
