#!/usr/bin/env python3
"""check-sources.py — does SOURCES still describe `old/`?

`scripts/check-vendor.sh` proves every directory under `old/` has content. It
never reads `SOURCES`, so the manifest — the file the README calls the
machine-readable list every consumer reads — can say anything at all:

  * an id that resolves to no directory (the vault vendors `xz-master`, the
    manifest says `xz`);
  * a directory with no row, i.e. a vendored source with no recorded upstream,
    licence or integration;
  * the same id twice in the enforced tables.

None of that fails a build today, and none of it is visible unless somebody
reads both sides by hand.

  python3 tools/check-sources.py            # exit 1 if anything is wrong
  python3 tools/check-sources.py --advisory # report, always exit 0

Sections that are not claims about the tree — `Pending Additions`,
`Submodule entries`, `Licence corrections` — are parsed but not enforced.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "old")
SOURCES = os.path.join(ROOT, "SOURCES")

ROW = re.compile(r"^\|\s*([A-Za-z0-9_.+-]+)\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|\s*(\S.*?)\s*\|\s*(\S+)\s*\|\s*$")
NOT_ENFORCED = {"Pending Additions", "Submodule entries", "Licence corrections"}


def section_key(section):
    """The heading without its parenthetical, so `Pending Additions (…)` matches."""
    return re.sub(r"\s*\(.*\)\s*$", "", section).strip()


def read_manifest():
    """[(section, id, url)] for every table row, in file order."""
    rows, section = [], ""
    with open(SOURCES, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            m = ROW.match(line.rstrip("\n"))
            if m and m.group(1) not in ("id",) and set(m.group(1)) != {"-"}:
                rows.append((section, m.group(1), m.group(2)))
    return rows


def read_pins():
    """[(section, id, pin)] — the pin column, which the other readers ignore."""
    out, section = [], ""
    with open(SOURCES, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("## "):
                section = line[3:].strip()
                continue
            m = ROW.match(line.rstrip("\n"))
            if m and m.group(1) != "id" and set(m.group(1)) != {"-"}:
                out.append((section, m.group(1), m.group(3)))
    return out


def resolve_all(rows, dirs):
    """Map every SOURCES id to a directory, and say which directories are left.

    An id resolves exactly, or by the -master/-dev/-main suffix the vault
    actually uses. When two ids could claim the same directory (`preflate` and
    `preflate-rs` against `preflate-master` and `preflate-rs-main`), the longest
    id wins — it is the more specific claim.
    """
    claimed, resolved = {}, {}
    for _section, ident, _url in sorted(rows, key=lambda r: -len(r[1])):
        if ident in dirs and ident not in claimed:
            claimed[ident] = ident
            resolved[ident] = ident
    for _section, ident, _url in sorted(rows, key=lambda r: -len(r[1])):
        if ident in resolved:
            continue
        for d in dirs:
            if d.startswith(ident + "-") and d not in claimed:
                claimed[d] = ident
                resolved[ident] = d
                break
    return resolved, [d for d in dirs if d not in claimed]


# ---- compile check -------------------------------------------------------------------
#
# `--compile` syntax-checks the entry points listed in `tools/compile-check.txt` with the
# compiler on PATH. It exists because on 2026-11-17 this vault described itself perfectly and
# still could not be built: the brunsli glue called a 3-argument BrunsliEncodeJpeg while the
# header beside it declares four. Nothing in this repo compiles anything, so a copied tree can
# sit broken indefinitely and be discovered by whoever syncs it next.

COMPILE_LIST = os.path.join(ROOT, "tools", "compile-check.txt")
COMPILERS = ("c++", "g++", "clang++")


def find_compiler():
    for name in COMPILERS:
        for path in os.environ.get("PATH", "").split(os.pathsep):
            cand = os.path.join(path, name)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
    return None


def compile_entries():
    """(path, include_dirs) pairs from the list file, comments and blanks skipped."""
    entries = []
    if not os.path.exists(COMPILE_LIST):
        return entries
    with open(COMPILE_LIST, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            path, _, incs = line.partition("|")
            entries.append((path.strip(), [i for i in incs.strip().split(":") if i]))
    return entries


def run_compile_check():
    """0 if every entry point agrees with its headers, 1 otherwise."""
    entries = compile_entries()
    if not entries:
        print("compile-check: tools/compile-check.txt lists no entry points")
        return 0
    compiler = find_compiler()
    if compiler is None:
        # Not a failure: this must be runnable on a machine without a toolchain, and a
        # check that fails for want of a compiler teaches people to ignore it.
        print("compile-check: no C++ compiler on PATH — skipped, %d entry point(s) unverified"
              % len(entries))
        return 0

    import subprocess

    failed = 0
    for path, incs in entries:
        if not os.path.exists(os.path.join(ROOT, path)):
            print("compile-check: MISSING  %s" % path)
            failed += 1
            continue
        cmd = [compiler, "-std=c++17", "-fsyntax-only"]
        for inc in incs:
            cmd += ["-I", os.path.join(ROOT, inc)]
        cmd.append(os.path.join(ROOT, path))
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print("compile-check: ok       %s" % path)
        else:
            failed += 1
            print("compile-check: FAILED   %s" % path)
            for line in proc.stderr.strip().splitlines()[:6]:
                print("    %s" % line)
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--advisory", action="store_true",
                    help="report problems but exit 0 (for a tree that is not repaired yet)")
    ap.add_argument("--compile", action="store_true",
                    help="also syntax-check the glue entry points in tools/compile-check.txt")
    args = ap.parse_args()

    compile_rc = run_compile_check() if args.compile else 0

    if not os.path.isdir(VENDOR):
        print("FAIL: no old/ directory — wrong working directory?", file=sys.stderr)
        return 1
    dirs = sorted(d for d in os.listdir(VENDOR) if os.path.isdir(os.path.join(VENDOR, d)))
    rows = read_manifest()

    # The headings carry a parenthetical ("Pending Additions (queued for next
    # commit)"), so an exact match silently enforced sections this script
    # documents as advisory — `csc` was reported as a missing directory from a
    # row that sits under Pending Additions and was never meant to be enforced.
    enforced = [(s, i, u) for (s, i, u) in rows if section_key(s) not in NOT_ENFORCED]
    problems = []

    resolved, unrecorded = resolve_all(rows, dirs)

    seen = {}
    for section, ident, _url in enforced:
        key = (section, ident)
        if key in seen:
            problems.append(f"duplicate id {ident!r} in section {section!r}")
        seen[key] = True
        if ident not in resolved:
            problems.append(f"SOURCES lists {ident!r} but old/ has no such directory "
                            f"(no exact match and no {ident}-* match)")

    # A row must say what is actually vendored: a commit SHA for a submodule,
    # `copy` for a tree that was copied in, `unvendored` for a queued row. `TBD`
    # means nobody knows, which is the state this column was in for every row.
    for section, ident, pin in read_pins():
        if section_key(section) in NOT_ENFORCED:
            continue
        if pin == "TBD":
            problems.append(f"SOURCES row {ident!r} has pin TBD — record the submodule "
                            f"commit, or `copy`, or `unvendored`")
        elif pin not in ("copy", "unvendored") and not re.fullmatch(r"[0-9a-f]{40}", pin):
            problems.append(f"SOURCES row {ident!r} has pin {pin!r}, which is neither a "
                            f"40-character commit SHA nor `copy`/`unvendored`")

    for d in unrecorded:
        problems.append(f"old/{d} is vendored but has no SOURCES row "
                        f"(no upstream, licence or integration recorded)")

    print(f"SOURCES rows: {len(rows)} ({len(enforced)} enforced), old/ directories: {len(dirs)}")
    if not problems:
        print("sources OK: every directory is recorded and every recorded id resolves")
        return 1 if compile_rc else 0
    for p in problems:
        print("  " + p)
    print(f"\n{len(problems)} problem(s).")
    if args.advisory:
        print("advisory: not failing the build")
        return 1 if compile_rc else 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
