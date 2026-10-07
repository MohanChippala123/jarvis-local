# v0.8.0 screen agent and UI validation

October 7, 2026. **85 automated tests passed**, plus JavaScript syntax validation.

- Exact label/type targeting resolves a fresh control and rejects ambiguity. Query filtering searches deeper accessibility trees; returned controls include automation IDs.
- replace_text is scoped to an editable control and executes select-all/paste with a fresh observation afterward. Noneditable targets cannot receive that operation.
- The executor permits one attempted screen mutation per model response and rejects additional mutations until the next turn.
- Actual packaged LM Studio Gemma 4 E4B test: replaced **old value** with **Jarvis agent passed**, clicked **Apply test** by its exact Button label, and verified the Result label. Four calls, zero tool errors, 25.4 seconds overall. This is a behavioral regression check, not a universal performance guarantee.
- Chat UI: centered messages and composer, neutral colors, collapsible sidebar, optional activity drawer, copyable fenced code and named Markdown links. Desktop and 390px responsive checks recorded; earlier layout issues were corrected before final verification.
- Existing settings, image history and auto-approval remain in effect. Model weights are unchanged.

Historical validations follow.

# v0.7.0 image-prompt validation

October 5, 2026. **81 automated tests passed**, plus JavaScript syntax validation.

- Image count/size/type validation, malformed data rejection, normalized JPEG encoding, transparency flattening, aspect ratio and path safety.
- Agent integration: local vision observations reach the chosen agent and persist as context; cancellation prevents image inference.
- Attachment retrieval requires authentication, serves JPEG with no-store headers, and rejects invalid IDs. Browser CSP permits the private blob previews.
- Real packaged UI: picker attachment, preview removal, reattachment and prompt submission passed. Local Gemma 4 E4B correctly read **IMAGE TEST 47** and identified the **red square** in the uploaded image.
- Reloaded app restored the stored 700x460 image as an authenticated blob preview. Browser console had no errors.

Paste/drop handlers are implemented using browser image/file events. The recorded browser interaction used the picker. Previous validations follow.

# v0.6.0 screen-control validation

October 5, 2026. **72 automated tests passed** and JavaScript syntax validation passed.

- Dedicated screen mode and a separate screen-step limit; file/shell/coding mutations are absent from its tool catalog.
- Fresh accessibility IDs; stale, expired, disabled, password and wrong-window targets are rejected. COM wrappers are re-resolved at input time rather than retained across tool calls.
- Cancel and denied-action checks execute before input. Local vision uses the same cancellable inference stream as chat.
- Fast native window inventory, reduced pointer delays, virtual-desktop coordinates and all-monitor capture. A foreground target is cropped for a readable live view.
- Latest accessibility observations survive context compaction. Active screen task events replay after a UI reload.
- Real packaged Gemma 4 E4B agent: list_windows → inspect_window → type → click → verified Result label. Two successful runs, **12.6–12.7 seconds** overall (four calls in the first, six in the repeat with stale-ID recovery); warm inspections **36–42 ms**, type **167–174 ms**, click **137–139 ms** (input timings exclude screenshot/model inference). The test window was on a monitor with negative Y coordinates.
- Browser QA: Screen control selectable and task controls disabled while running; screen image, target, control count and timings appeared; no browser console errors.

These are measured test results, not a guarantee that every third-party app or model behaves correctly. Screens are snapshots after observations/actions, not video. Historical tests and limitations follow.

# v0.5.1 validation

Validated on Windows on October 4, 2026. This is early-access software, not a claim that every third-party app works.

## October 5 audit fixes

- Malformed or non-object model tool arguments now return a tool error so the agent can recover, rather than ending the whole task. Context compaction tolerates these calls.
- Coding tasks check for actual source edits and command execution instead of accepting promises after read-only tools. Project instructions now require preserving real integrations and working functionality.
- General PowerShell execution propagates a native program's nonzero exit code and displays it in the terminal.
- General file writes are atomic and retain backups, protecting original contents if replacement fails.
- Browser launch rechecks internet access after approval; missing project edit targets and oversized text edits are rejected before saving.
- Terminal Stop/timeouts have bounded output-drain time, including when a subprocess leaves pipes open.
- Live task polling returns only new events instead of repeatedly transferring all tokens, screenshots and output.
- Rapid submissions are guarded while a task request is pending. Model loading excludes concurrent tasks and releases the lock on failure.
- Unsaved settings survive refreshes; model/config controls are disabled during a task. Missing/unauthorized jobs no longer poll forever.
- New conversation resets live workspace/activity; replay removes the stale empty-file option; clearing the terminal resets its stream labels.
- Stale successful coding history is labeled as previous context. Action requests require fresh tool execution, with a fallback when a model/backend does not return a required tool call. Offline and model-load errors now offer actionable messages. Preview-state reads tolerate concurrent changes.
- Approval hints reflect the enabled automatic/manual policy instead of contradicting auto-approval.

Validation: **60 automated tests passed**, including recovery after a malformed tool call with a real file write, atomic-replace failure, native command exit 7, browser permission revocation, incremental HTTP events, and model-load lock release. The packaged local-model workflow was repeated against deliberately broken source with stale successful history present: actual test exit codes were 1 then 0, and tests were unchanged. UI checks verified unsaved settings survive Refresh and stale file placeholders are removed. Prior desktop validations below were recorded on October 4.

## Automated checks

**60 passing tests** cover:

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

Additional automatic-action checks verify an actual file write without a dialog and with its original backup, cancellation, scope/capability enforcement, and switching a waiting action into automatic mode then restoring manual review.

Live-view checks verify output arrives before process exit, separate stdout/stderr and nonzero status, split UTF-8 decoding, large-output bounds without pipe deadlock, timeout/Stop end states, exact saved-file diffs, and no edit event after a failed edit.

The packaged executable's real LM Studio bug-fix task emitted the saved calculator diff, streamed terminal output, and matching exit codes **1 → 0**. Browser checks verified both diff and saved-source views. A real local preview served the project, streamed its log, and emitted its terminal end state when stopped.

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

## Coding agent validation

- A real local LM Studio coding agent ran three failing calculator tests, inspected source, fixed subtraction to addition, and reran the same unchanged tests successfully. Recorded command exit codes: **1 → 0**.
- The packaged Windows executable independently repeated the failing-test, source-edit, passing-test workflow through its authenticated HTTP API; all three tests remained unchanged.
- A local preview server served the selected project and stopped its own process tree successfully.
- Automated checks cover project path escapes, private/Git files, one edit grant per task, recoverable edits, ambiguous replacements, denied commands, permission revocation, source search line numbers, observable command failures, context compaction with paired function results, and LM Studio model loading.

## Limits

These checks do not certify control of elevated apps, games, multiple displays, inaccessible controls, or arbitrary third-party programs. Model choices can be wrong. Drag and pointer movement are implemented but were not included in the nine recorded desktop checks. Review approvals and start with disposable tasks.
