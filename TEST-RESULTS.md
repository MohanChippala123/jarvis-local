# v0.3.0 validation

Validated on Windows on October 4, 2026. This is early-access software, not a claim that every third-party app works.

## Automated checks

**25 passing tests** cover:

- File-scope and protected-state restrictions.
- Declined and cancelled writes producing no file changes.
- Backups of overwritten files and recoverable removal.
- Revoking access while an action awaits approval.
- Shell tools being disabled by default.
- Per-launch API authentication, Origin checks, and Host validation.
- Loopback-only LM Studio endpoints.
- Local model capability checks and rejecting unknown models.
- Assembly of streamed function names and JSON arguments.
- Cancelling a blocked inference stream without waiting for generation to finish.

## Actual desktop tests

**Nine checks passed** in a disposable test window:

1. Window discovery, handles, and control rectangles.
2. Window focusing.
3. Clicking the text area and pasting Unicode text.
4. Ctrl+A followed by replacement typing.
5. Button clicking with a recorded click counter.
6. Double-clicking with a recorded event.
7. Right-clicking with a recorded event.
8. Scrolling with a recorded wheel event.
9. Blocking a click outside the approved target window.

The tests exposed and resolved Windows DPI-coordinate mismatches and wheel-event scaling. Mouse scrolling now moves to the approved point and uses Windows' 120-unit wheel delta. Desktop input checks the foreground window and rejects points outside or obscuring its target.

## LM Studio integration

- A real local **google/gemma-4-e4b** model discovered the scratch window, requested mouse and keyboard tools, waited for approvals, and entered the expected text.
- The local vision model correctly read a synthetic test image.
- The standalone Windows executable opened its app window and passed local chat plus system-information tool execution.
- The standalone Windows executable also completed the approved mouse-and-keyboard workflow against the scratch window.
- No cloud model or LM Link was used.

## Natural request regression

The screenshot request, “control my screen, then open google chrome, then open reddit, then find new ai integrated project ideas,” completed against real Chrome and LM Studio, with the preceding failed clarification messages included in context. The model opened public browser pages, searched Reddit, and returned project findings with actual source links. Tests also cover provider fallback, browser capability checks, conversational tool evidence, and bounded completion repair.

## Limits

These checks do not certify control of elevated apps, games, multiple displays, inaccessible controls, or arbitrary third-party programs. Model choices can be wrong. Drag and pointer movement are implemented but were not included in the nine recorded desktop checks. Review approvals and start with disposable tasks.
