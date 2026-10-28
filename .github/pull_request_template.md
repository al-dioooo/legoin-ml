<!--
PR title: <type>(<scope>): <description> (#<issue>)
Example:  feat(detection): add YOLO11 brick detection notebook (#2)
-->

## Summary

<!-- Brief description of the change. -->

## Problem

<!-- What issue or limitation this PR addresses. -->

## Solution

<!-- How the change solves the problem. -->

## Test Evidence

<!-- Where the notebook ran (Colab T4, server, CPU smoke test), with which config, and the metrics or plots it produced. -->

## Deployment Prerequisite / Breaking Changes

<!-- New weights release, changed image size or thresholds the backend must follow, renamed outputs. Write "None" if there are none. -->

## Notes

<!-- Additional context and what reviewers should focus on. -->

Closes #

### Checklist

- [ ] PR title carries the issue number
- [ ] `ruff check .` and `python scripts/check_repo.py` pass
- [ ] Notebook outputs are cleared (`python scripts/check_repo.py --fix`)
- [ ] No datasets, logs or weights committed; weights go to a GitHub Release
