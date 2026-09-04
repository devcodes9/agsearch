#!/usr/bin/env python3
"""Copy skills/agsearch/SKILL.md into the SKILL_MD literal in the agsearch script.

The repo file is the one people read and edit. The literal is the copy that reaches anyone who
installed through brew, uv or the curl script, none of which put a data file on disk.
tests/test_skill.py fails when the two disagree; this is what fixes it.

    python3 tools/sync-skill.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "agsearch"
SKILL = ROOT / "skills" / "agsearch" / "SKILL.md"

BLOCK = re.compile(r'^SKILL_MD = """\\\n.*?"""$', re.S | re.M)


def main():
    text = SKILL.read_text()
    for bad in ('"""', "\\"):
        if bad in text:
            sys.exit(f"SKILL.md contains {bad!r}, which cannot go in the literal unescaped")
    script = SCRIPT.read_text()
    if not BLOCK.search(script):
        sys.exit("could not find the SKILL_MD literal in the agsearch script")
    SCRIPT.write_text(BLOCK.sub('SKILL_MD = """\\\n' + text + '"""', script, count=1))
    print(f"synced {SKILL.relative_to(ROOT)} -> SKILL_MD")


if __name__ == "__main__":
    main()
