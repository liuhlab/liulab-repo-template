# liulab-newpkg

> **Replace this file.** This is the template's generic copy: it says how *any* Liu Lab repo
> works, not what *this* one does. Run `/init`, then delete this line.

One paragraph: what this package is for, who uses it, and the one thing that is easy to get
wrong. Distribution name **`liulab-newpkg`**, import name **`newpkg`**.

## Toolchain

- **pixi** is the only supported toolchain. Never bare pip, uv, or conda. `pyproject.toml`
  is the single source of truth for dependencies, environments, and tasks.
- **Python 3.13**, declared in exactly two places: `requires-python` and the pixi pin.
- **hatchling + hatch-vcs**. The version comes from the newest git tag, CalVer
  `vYYYY.M.PATCH`. Never hand-edit a version.
- Platforms: `osx-arm64` and `linux-64`.

## Layout

```text
src/newpkg/       the package — rename this directory first
tests/            pytest, mirroring src/
docs/             the published site; docs/adr/ and docs/agents/ are agent-facing
skills/           repo-local agent skills; `python skills/install.py --help`
scripts/check.sh  the gate runner
CONTEXT.md        the glossary — the words this repo uses
```

## Gates

`pixi run check` must be green before you commit. It is `check-static` plus `test`:

| Step | Tool |
| --- | --- |
| `lint`, `fmt-check` | ruff |
| `typecheck` | pyright, `standard` mode |
| `vale`, `markdownlint` | the writing rules |
| `conformance` | the repo still matches the template's rules |
| `test` | pytest |

`check.sh` runs every step and reports **all** failures, not just the first — so read to the
bottom before fixing anything. The docs build is not part of `check`; it needs its own pixi
environment and runs as its own CI job.

## Writing rules

Three rules, all enforced by `vale`: be concise; agent-facing documents have word caps;
human-facing prose avoids jargon and stays readable. Read `docs/agents/writing.md` before
writing either kind — the caps are lower than you expect, and this file is subject to one.

## Read next

| When | Read |
| --- | --- |
| Before changing code | `CONTEXT.md`, then any ADR covering the area |
| Recording vocabulary or a decision | `docs/agents/domain.md` |
| Filing or working an issue | `docs/agents/issue-tracker.md` |
| Labelling someone else's issue | `docs/agents/triage-labels.md` |
| Writing anything | `docs/agents/writing.md` |
