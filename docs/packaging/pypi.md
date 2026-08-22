# PyPI and `uvx`

`uvx agsearch -n "stripe tax id"` runs agsearch with **nothing installed**.

That matters more than it looks. In this niche — read-only inspectors of a
directory the user already has — zero-install is what converts:

| Tool | Lead install | Stars |
|---|---|---|
| ccusage | `npx` | 18,084 |
| claude-code-viewer | `npx` | 1,274 |
| claude-code-log | **`uvx`** | 1,198 |
| cass | `curl \| bash` | 1,077 |
| search-sessions | brew, cargo | 38 |
| clauhist | `cargo install` | 7 |

Zero-install takes the top three slots; nothing leading with a package-manager
install has cleared 40 stars. `ccusage`'s GitHub repo *description* is literally
the string `npx ccusage`.

The reason is about intent, not preference: someone trying one of these tools is
thinking "peek at my logs," not "adopt a tool." Anything implying permanent
installation is mismatched to that.

## The honest caveat

`uvx` cannot express a dependency on `fzf`, because fzf is not a Python package.
So the two channels do different jobs and both statements are true:

- **`uvx agsearch -n "query"`** — the try-it surface. Non-interactive mode is
  stdlib-only, so this works with genuinely zero setup.
- **`brew install devcodes9/tap/agsearch`** — the real install, which resolves
  fzf and gives you the TUI.

The README's install ladder reflects that ordering.

## How the build works

agsearch ships as an **extensionless executable at the repo root**, because that
is what `curl | sh` drops onto a PATH. Python needs it importable as
`agsearch.py`. Rather than rename the file and break the raw-URL install, the
wheel maps it:

```toml
[tool.hatch.build.targets.wheel]
bypass-selection = true
force-include = { "agsearch" = "agsearch.py" }
```

One source of truth, both distribution shapes.

`sources = {...}` looks like it would do this and does not — it strips path
prefixes without renaming, and produces a wheel containing an extensionless
`agsearch` that nothing can import. That failure surfaces when the console
script runs, not when the wheel builds, so it will pass CI and ship.

The version comes from the same literal the CLI prints:

```toml
[tool.hatch.version]
path = "agsearch"
pattern = '^__version__ = "(?P<version>[^"]+)"'
```

`tests/test_packaging.py` asserts that pattern still matches, that the entry
point target exists and takes no arguments, and that the dependency list is
still empty.

## One-time setup

1. **Claim the name.** `agsearch` is currently unclaimed on PyPI — first come.
2. On PyPI, add a **trusted publisher** (no API token in the repo):
   - Owner `devcodes9`, repository `agsearch`
   - Workflow `publish-pypi.yml`
   - Environment `pypi`
3. Create a `pypi` environment in the repo settings. Protect it if you want a
   manual approval gate on every publish.

## Releasing

`publish-pypi.yml` fires on a `v*` tag: builds sdist + wheel, asserts the built
filename matches the tag, installs the wheel into a clean venv and runs it, then
publishes.

The version assertion is deliberately *before* the upload. PyPI uploads are
irreversible — a file published under the wrong version can be yanked but never
replaced.

## Verify a build locally

```sh
python3 -m venv /tmp/v && /tmp/v/bin/pip install build
/tmp/v/bin/python -m build
/tmp/v/bin/pip install dist/*.whl
/tmp/v/bin/agsearch --version
```
