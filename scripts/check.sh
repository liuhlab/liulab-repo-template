#!/usr/bin/env bash
#
# The gate runner. Usage: bash scripts/check.sh <pixi-task>...
#
# Each argument names a task in [tool.pixi.tasks]. The steps all start at once and
# each one's output is captured to its own file, because interleaved concurrent
# output is unreadable. Nothing is printed until every step has finished; then each
# step gets a labelled block, in the order it was named, followed by a summary.
# The exit status is non-zero if any step failed.
#
# The step list lives in the `check-static` task in pyproject.toml and nowhere else,
# so adding a step is one more word in one place and the local gate cannot drift
# from CI, which invokes the same task names.
#
# `set -e` is DELIBERATELY ABSENT. It is exactly what would stop the runner at the
# first failing step, and telling you everything that is wrong in a single run is
# the entire point of this file.
#
# Portable to bash 3.2, which is what macOS ships: no `wait -n`, no associative
# arrays, nothing beyond coreutils.

set -uo pipefail

if [ "$#" -eq 0 ]; then
    printf 'usage: %s <pixi-task>...\n' "$0" >&2
    exit 2
fi

steps=("$@")
count=$#

capture_dir=$(mktemp -d "${TMPDIR:-/tmp}/liulab-check.XXXXXX") || exit 2
trap 'rm -rf "$capture_dir"' EXIT

rule="--------------------------------------------------------------------"

# Start every step.
pids=()
i=0
while [ "$i" -lt "$count" ]; do
    pixi run "${steps[$i]}" >"$capture_dir/$i" 2>&1 &
    pids[$i]=$!
    i=$((i + 1))
done

# Collect every status. Without `wait -n` this waits in launch order, which costs
# nothing: the steps are already running, and no failure short-circuits the loop.
statuses=()
i=0
while [ "$i" -lt "$count" ]; do
    wait "${pids[$i]}"
    statuses[$i]=$?
    i=$((i + 1))
done

# One labelled block per step, output in full, pass or fail.
failed=0
i=0
while [ "$i" -lt "$count" ]; do
    if [ "${statuses[$i]}" -eq 0 ]; then
        verdict="PASS"
    else
        verdict="FAIL"
        failed=$((failed + 1))
    fi
    printf '\n%s\n%s  %s\n%s\n' "$rule" "$verdict" "${steps[$i]}" "$rule"
    cat "$capture_dir/$i"
    i=$((i + 1))
done

# The summary, so a long run does not have to be re-read to find what broke.
printf '\n%s\nsummary\n%s\n' "$rule" "$rule"
i=0
while [ "$i" -lt "$count" ]; do
    if [ "${statuses[$i]}" -eq 0 ]; then
        printf '  pass  %s\n' "${steps[$i]}"
    else
        printf '  FAIL  %s (exit %s)\n' "${steps[$i]}" "${statuses[$i]}"
    fi
    i=$((i + 1))
done

if [ "$failed" -gt 0 ]; then
    printf '\n%s of %s steps failed. Every failure is above; read to the bottom.\n' \
        "$failed" "$count" >&2
    exit 1
fi

printf '\nAll %s steps passed.\n' "$count"
