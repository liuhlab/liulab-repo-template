---
search:
  exclude: true
---

# Build the docs site with zensical

The site is built by `zensical`, pinned `==0.0.57`, not by mkdocs plus mkdocs-material.
zensical reads the same `mkdocs.yml`, runs the same Python-Markdown extensions in-process,
and renders mkdocstrings, so one repo can move back to mkdocs by changing two lines in
`pyproject.toml`.

## Why this is surprising

zensical is a `0.0.x` alpha. It shipped eight releases in six weeks, and one of them broke
search for a day. The obvious choice is mkdocs-material, which two lab repos already run.
The alpha wins here because the config file is the same either way: the lock-in is one
pixi feature, not a docs tree. That is also why this template takes a risk the research
note declined to take for the three production repos.

## What it costs

Three gaps, each with a named workaround:

- **No `gh-deploy`, and none is planned.** The docs workflow publishes `./site` with
  `peaceiris/actions-gh-pages@v4` and `force_orphan: true` instead, which is what the two
  repos already on `gh-pages` do.
- **`exclude_docs:` is silently ignored.** Every file under `docs/` is published whether
  or not it is listed anywhere. Agent-facing pages therefore carry `search: exclude: true`
  front matter, and `mkdocs.yml` carries an explicit `nav:`. Front matter does nothing
  about the navbar; `nav:` does nothing about search. Both, always.
- **A `nav:` entry naming a missing file no longer fails `--strict`.** `mkdocs build
  --strict` caught that. Dead internal links and unresolved mkdocstrings references still
  fail, so `--strict` is still worth passing.

The research note expected one residue — excluded pages still listed in `sitemap.xml`. With
an explicit `nav:` that does not happen: zensical builds the sitemap from the nav, so the
agent-facing pages are out of the navbar, out of search and out of the sitemap, and still
reachable by URL. That is the whole requirement.

## Why the pin is exact

`0.0.x` promises nothing about `0.0.58`, and the search regression above landed in a patch
release. Bump the pin in a commit of its own and re-run `pixi run docs-build`.
