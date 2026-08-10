"""Fail when a CI job reports green because a test skipped.

The gap analysis named this failure: a run that says "all tests passed" while the
one test that would have caught the problem never ran. Skips are legal in the
pre-push hook, which needs local secrets. They are not legal in CI, where every
selected test must actually execute.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET


def main(path: str) -> int:
    root = ET.parse(path).getroot()
    skipped: list[str] = []
    for case in root.iter("testcase"):
        if case.find("skipped") is not None:
            skipped.append(f"{case.get('classname')}::{case.get('name')}")

    if skipped:
        print("These tests skipped, and no CI job may skip:", file=sys.stderr)
        for name in skipped:
            print(f"  {name}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
