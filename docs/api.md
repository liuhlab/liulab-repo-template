# API reference

Built from the docstrings in `src/newpkg/`, so this page and the code cannot drift apart.
Write the docstring; this page follows.

## newpkg

::: newpkg.core.greet

## The command line

The whole module, because typer makes every verb a plain function with a docstring, and
`newpkg.cli:app` — the object `[project.scripts]` registers — is built from them.

::: newpkg.cli
