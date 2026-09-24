#!/usr/bin/env python3
"""Reindent the content inside top-level numbered list items so it stays
attached to the list item in Pandoc/Quarto's HTML output.

Why this exists: Pandoc only treats a paragraph, code fence, math block,
etc. as *part of* a list item if it is indented to at least the column
where the item's text starts (3 spaces for "1. ", 4 spaces for "34. ").
The item's own first paragraph is allowed to wrap unindented (lazy
continuation), but everything after the first blank line -- a code chunk,
the paragraph that follows it, an image, a nested bullet list -- needs
that indentation or Pandoc silently kicks it out of the list. When that
happens the list item still *looks* numbered correctly (each broken-out
chunk quietly restarts its own one-item list), but the trailing content
renders flush-left in HTML instead of aligned under the item.

This script finds every block after a top-level "N. " marker and shifts
it (preserving its own internal/relative indentation) so its minimum
indentation matches the marker width. It's idempotent -- rerun it after
editing and already-correct blocks are left untouched.

Exception: ```{ojs} fences. Quarto extracts ojs cells with a raw-text
preprocessing pass that runs before Pandoc's list-aware parsing, and its
generated `::: {.cell}` wrapper is always emitted unindented -- no source
indentation keeps an ojs cell nested inside a list item. Worse, only the
first `//| label: ...` line has its indentation stripped by Quarto; every
other `//| ...` line and the code body are passed through verbatim, so
indenting them (to match the list) breaks option parsing and leaks raw
`//| ...` comments into the rendered output. So ojs fences -- and anything
after them in the same item, which can no longer be pulled back into the
list either -- are dedented to column 0 instead of shifted to the list
target. This necessarily breaks the enclosing list at that point -- run
renumber_lists.py afterward to patch up the numbering, same as for any
other content that escapes a list item.

Companion to renumber_lists.py, which fixes the literal item numbers for
the same underlying reason (blocks breaking the list). Run either one
first; they don't interfere with each other.

Usage:
    python reindent_lists.py FILE.qmd [FILE2.qmd ...]
    python reindent_lists.py --check FILE.qmd     # show a diff, don't write
"""
import difflib
import re
import sys
from pathlib import Path

MARKER_RE = re.compile(r'^(\d+)([.)])(\s+)(.*)$')
HEADING_RE = re.compile(r'^#{1,6}\s')
FENCE_RE = re.compile(r'^\s*(```+|~~~+)(.*)$')
OJS_INFO_RE = re.compile(r'^\{\s*ojs\b', re.IGNORECASE)


def fence_ranges(lines):
    """Inclusive (start, end, is_ojs) ranges covered by fenced code blocks."""
    ranges = []
    in_code = False
    fence_char = None
    start = None
    is_ojs = False
    for i, raw in enumerate(lines):
        line = raw.rstrip('\n')
        m = FENCE_RE.match(line)
        if m:
            char = m.group(1)[0]
            if not in_code:
                in_code, fence_char, start = True, char, i
                is_ojs = bool(OJS_INFO_RE.match(m.group(2).strip()))
            elif char == fence_char:
                ranges.append((start, i, is_ojs))
                in_code = False
    if in_code:
        ranges.append((start, len(lines) - 1, is_ojs))
    return ranges


def leading_spaces(line):
    return len(line) - len(line.lstrip(' '))


def is_blank(line):
    return line.strip() == ''


def reindent(lines):
    protected = [False] * len(lines)
    ojs_line = [False] * len(lines)
    for start, end, is_ojs in fence_ranges(lines):
        for i in range(start, end + 1):
            protected[i] = True
            ojs_line[i] = is_ojs

    out = []
    target = None       # required indent width for the active item's continuation blocks
    mode = None          # None | 'lazy' (first paragraph, untouched) | 'reindent'
    block = []
    # Once an {ojs} fence appears in the current item, it breaks out of the
    # list (see module docstring) and can never be pulled back in. Everything
    # after it -- until the next list marker or heading -- is no longer list
    # content either, so it must also dedent to column 0: leaving it at the
    # list's indent width would make Pandoc read it as an indented code block.
    after_ojs = False
    in_frontmatter = False

    def flush_block():
        nonlocal block
        if not block:
            return
        non_blank = [l for l in block if not is_blank(l.rstrip('\n'))]
        if not non_blank:
            out.extend(block)
            block = []
            return
        cur_min = min(leading_spaces(l) for l in non_blank)
        block_target = 0 if after_ojs else target
        delta = block_target - cur_min
        for l in block:
            if is_blank(l.rstrip('\n')) or delta == 0:
                out.append(l)
            elif delta > 0:
                out.append(' ' * delta + l)
            else:
                strip_n = min(-delta, leading_spaces(l))
                out.append(l[strip_n:])
        block = []

    for i, raw in enumerate(lines):
        line = raw.rstrip('\n')

        if i == 0 and line.strip() == '---':
            in_frontmatter = True
            out.append(raw)
            continue
        if in_frontmatter:
            out.append(raw)
            if line.strip() == '---':
                in_frontmatter = False
            continue

        if protected[i]:
            if mode == 'reindent':
                block.append(raw)
                if ojs_line[i]:
                    after_ojs = True
            else:
                out.append(raw)
            continue

        if HEADING_RE.match(line):
            if mode == 'reindent':
                flush_block()
            target, mode = None, None
            after_ojs = False
            out.append(raw)
            continue

        m = MARKER_RE.match(line)
        if m:
            if mode == 'reindent':
                flush_block()
            num, sep, _space, _rest = m.groups()
            target = len(num) + len(sep) + 1
            mode = 'lazy'
            after_ojs = False
            out.append(raw)
            continue

        if target is None:
            out.append(raw)
            continue

        if mode == 'lazy':
            out.append(raw)
            if is_blank(line):
                mode = 'reindent'
            continue

        # mode == 'reindent'
        if is_blank(line):
            flush_block()
            out.append(raw)
        else:
            block.append(raw)

    if mode == 'reindent':
        flush_block()

    return out


def process_file(path: Path, check: bool):
    text = path.read_text()
    lines = text.splitlines(keepends=True)
    new_text = ''.join(reindent(lines))

    if new_text == text:
        print(f'{path}: already correct')
        return

    if check:
        sys.stdout.writelines(difflib.unified_diff(
            text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f'{path} (reindented)',
        ))
    else:
        path.write_text(new_text)
        print(f'{path}: reindented')


def main():
    args = sys.argv[1:]
    check = '--check' in args
    if check:
        args.remove('--check')
    if not args:
        print(__doc__)
        sys.exit(1)
    for arg in args:
        process_file(Path(arg), check=check)


if __name__ == '__main__':
    main()
