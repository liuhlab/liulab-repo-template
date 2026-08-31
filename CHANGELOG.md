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
