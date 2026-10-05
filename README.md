# Jarvis Local

A local Windows AI assistant powered by **LM Studio**. Chat, research the web, inspect your screen, and perform approved desktop and file actions through a simple interface.

**Early access · v0.7.0 · Windows x64 · MIT licensed**

## Windows download

Download the Windows ZIP from [GitHub Releases](https://github.com/MohanChippala123/jarvis-local/releases/tag/v0.7.0), extract it, and run **Jarvis.exe**. Python is bundled; models are separate. Jarvis opens an isolated Edge or Chrome app window, with an embedded fallback. This is an unsigned build, so review the source/release if Windows blocks it. You can run the source version instead.

## Prepare LM Studio

1. Install [LM Studio](https://lmstudio.ai/download).
2. Download a model trained for tools. **google/gemma-4-e4b** is the default and supports both tools and vision. Choose a quantization that fits your machine.
3. Load your model and start LM Studio's local server on port **1234** in its Developer tab.
4. Open Jarvis, choose your chat model above the conversation and your screenshot model in Settings, and try a small task.

For CLI users:

```powershell
lms server start
lms load google/gemma-4-e4b --context-length 16384 --yes
```

Jarvis accepts only a loopback HTTP server address. The default is `http://127.0.0.1:1234`. It checks LM Studio's local model library and rejects models without the required tool or vision capabilities. LM Link is not used. If you enabled LM Studio server authentication, set the `JARVIS_LM_STUDIO_TOKEN` environment variable before starting Jarvis.

## Live coding workspace

The **Live workspace** above the conversation opens automatically for coding tasks and command execution. File changes appear only after a successful save. Choose a changed file and switch between a red/green diff and saved source. The terminal shows the exact PowerShell command, working folder, stdout/stderr as the process writes them, and final exit code, Stop or timeout status. Preview logs continue while their server runs. This is an output viewer, not an interactive terminal.

The current task’s view remains available until the next task; refreshing during an active task replays its events. Events are also stored in the local activity log. Large file/diff views and console output are bounded and indicate clipping; the command’s final result retains its output tail. Terminal output depends on the subprocess flushing its buffers.

## Automatic actions

Settings & access includes **Auto-approve actions**. When enabled, Jarvis executes enabled desktop, file, PowerShell, and coding tools without approval dialogs, including project edit grants and terminal commands. The activity log records each automatic approval. Commands can change your PC as your Windows user. Stop, file scopes, protected state, backups, capability toggles, and timeouts still apply. Turn the setting off to resume manual review. Fresh installations default to manual approval.

The approval descriptions below describe manual mode; auto-approval skips those dialogs. This setting does not guarantee that the model can complete every task.

## Coding agent and model selection

Choose **Coding agent** above the conversation, enter an absolute **Project folder** (existing or new), and describe what to build or fix. Jarvis inspects the project, reads/searches source files, creates directories, writes complete files or exact edits, runs commands, diagnoses failures, and continues toward passing builds/tests. Each coding task has a bounded step budget (30 by default; configurable up to 60).

Approve project edits once per task. This permits directory creation and file edits only inside the selected project; existing files are backed up. Terminal build/test/install/preview commands ask for separate approval and display their exact working directory. They run as your Windows user, **not in a security sandbox**, and are independent of the general PowerShell toggle. Turning off Coding agent or Files blocks subsequent coding actions. Private environment/key files and Git internals are excluded from project file tools.

Python and Node.js must be installed separately when your project uses them; the Python bundled in Jarvis.exe is for Jarvis itself. The agent reports installed runtimes. A managed local web preview can be started by the agent and opened/stopped from the project controls; preview servers stop when Jarvis closes. Commands time out after at most three minutes, so very long installs may need manual execution.

Use the **LM Studio model** dropdown directly above the chat. It lists downloaded models with tool support and marks loaded models. **Refresh** updates the list; **Load model** loads the selected model into LM Studio. Selection persists and applies to the next task. Screenshot models are selected separately in Settings, filtered for vision support. Model size and quality still matter; choose a model that fits your RAM/VRAM. Models must be downloaded through LM Studio first.

Example: “Run the tests, fix the failing code without changing tests, and rerun until they pass.” Or: “Build a todo app in this project, verify it, and start a local preview.”

## Features

- Streaming chat and a bounded multi-step agent using local model tool calls.
- Live web search and HTML/text-page reading, without a paid search API key.
- Folder listing, filename search, text-file reading, file writing, moving, and recoverable removal.
- Local screenshot interpretation with a vision model; visible-window and accessibility-control inspection.
- Targeted mouse clicks, double clicks, right clicks, pointer movement, dragging, scrolling, Unicode pasting, and keyboard shortcuts.
- App launching and focus, subject to your approval.
- Optional PowerShell execution, disabled by default and always approved per command.
- Windows offline speech output and push-to-dictate input, using installed speech languages.
- Local history, saved preferences, activity, backups, and recovery files.

## Try it

“Check my PC's memory usage and running apps.”

“Find filenames containing invoice in my Downloads folder.”

“Inspect my screen and describe the current task.”

“Open Notepad, inspect its window controls, and type a packing checklist.”

“Research the latest Python release and cite the official source.”

## You control access

Files, internet, and PC tools have individual toggles. File access starts in your Windows user folder. Add other absolute folders or drives in Settings if you want broader access. Windows permissions still apply; Jarvis does not elevate to administrator.

Changes, saved preferences, app launches, focus changes, and desktop input require one-time approval of the exact arguments. Read-only enabled tools run automatically. Declined actions do not run; approvals expire after five minutes. Revoked capabilities block pending actions too.

Desktop input restores a uniquely matching target window after approval. Mouse points must belong to that window, so an out-of-window or obscured point is rejected. Coordinate handling uses physical primary-screen pixels and supports Windows display scaling. Primary-screen screenshots are resized for vision; the tool reports both original and resized dimensions.

**Stop task** cancels ongoing chat inference and prevents subsequent actions. It kills an app-started PowerShell process tree. Completed actions and launched apps remain; this is not an undo button. A read or screenshot description already underway may take time to finish. Moving the pointer to the top-left corner triggers PyAutoGUI's input fail-safe.

This is early-access software. Models can select incorrect actions. Elevated apps, games, minimized windows, multiple displays, and apps with poor accessibility support may need manual help. PC control runs as your normal Windows user. The website is a download page and does not control visitor computers.

## Local data and internet use

The executable stores its data in `%LOCALAPPDATA%/JarvisLocal`; the source version uses `data/` beside `app.py`.

- `settings.json`: models, loopback server address, and access controls.
- `history.json`: recent messages and completed replies.
- `memory.json`: explicitly saved preferences.
- `activity.jsonl`: tools, arguments, results, approval requests, and screenshot images.
- `backups/`: original copies of files overwritten through the write tool.
- `recovery/`: files/folders removed through the recoverable removal tool. Move them back manually to restore.
- `runtime.log`: launch diagnostics for the desktop build.

These are ordinary unencrypted local files. New conversation clears chat history; logs and backups remain. Forget preferences clears saved memory. Close Jarvis before manually removing logs. Screenshots may contain everything visible on the primary display.

Model inference and Windows speech stay on the PC. Web search sends queries to public search providers; page reading contacts the requested sites. Jarvis does not configure a cloud model, user account, or paid API. It treats web pages, screen text, and file contents as untrusted data. Model behavior is not a security boundary: review approvals before consequential actions.

The local app server listens on `127.0.0.1`, uses a random port and per-launch API token, checks Host/Origin, and does not serve arbitrary filesystem paths. This does not protect against another malicious program running as your Windows user.

## Run from source

Install Python **3.12+**, clone this repo, and run `Setup.cmd`. It creates a virtual environment and installs Python dependencies. Prepare LM Studio separately as described above. Then double-click `Start Jarvis.cmd`.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe app.py
```

For a browser-only session, add `--server`. Closing the desktop window shuts down that session. Starting a second copy opens the existing session in a browser. Windows dictation needs a working default microphone and installed speech recognizer; there is no wake word or continuous recording.

## Tests and Windows build

```powershell
.venv/Scripts/python.exe -m unittest discover -v
```

Tests cover permissions, cancellation, recoverable file actions, endpoint restrictions, streamed tool-argument assembly, and inference cancellation. Actual mouse/keyboard tests were also run against a disposable scratch window. See `TEST-RESULTS.md` for release validation and limits.

Build on Windows with `build_windows.py`. It uses PyInstaller and bundles only app code, UI assets, runtime libraries, and dependency metadata—not models or personal data. `website/` is the static Vercel landing page; its downloadable ZIP is also published as a GitHub Release asset.

## License and attribution

Jarvis app source is MIT licensed. Runtime dependencies retain their own licenses; see the bundled THIRD-PARTY-NOTICES file and package metadata. Model weights are not distributed and have their own licenses. Jarvis is not affiliated with Marvel, LM Studio, or model publishers.

References: [LM Studio tool use](https://lmstudio.ai/docs/developer/openai-compat/tools), [local model API](https://lmstudio.ai/docs/developer/rest/list), [PyAutoGUI](https://pyautogui.readthedocs.io/en/latest/quickstart.html), [DDGS](https://github.com/deedy5/ddgs).

## Image prompts

Click **+** beside the microphone to attach images, paste an image into the prompt box, or drag files onto the composer. Preview attachments and use the remove button before sending. You can send up to **3 images**, including an image-only message. PNG, JPEG, WebP and GIF are supported; GIFs use the first frame. The picker accepts files up to 10 MB and 20 megapixels, and resizes them to 1600 pixels on the longest edge before upload.

Choose the local vision model in **Settings > Images & screenshot understanding**. Jarvis reads each image locally with that model, then provides its observations to your chosen chat/coding/screen agent. A text-only chat model can therefore use image context. Image interpretation can miss fine details; crop or send a clearer image when necessary. Stop interrupts image inference too.

Images are normalized to JPEG without original EXIF metadata and saved in the local Jarvis data folder. Chat history retains attachment previews and the vision observations for follow-up questions. Image retrieval requires the current app token; image data is not embedded in history JSON. New conversation clears the conversation; stored images remain in the local data folder.

## Screen control mode

Choose **Mode → Screen control** above the chat, then describe what to do in an app. The agent reads Windows accessibility controls first, targets fresh control IDs instead of guessed coordinates, and automatically observes again after each action. Local screenshot vision remains available for controls that Windows cannot expose.

The **Screen control** panel shows the latest real capture, target window, control count and inspection time. It updates after tool actions; it is not a continuous video stream. Focused windows are cropped for readability; unfocused observations show the desktop. **Stop task** interrupts the agent and model inference, including vision. You can set a separate screen task step limit in Settings.

Mouse input uses Windows virtual-desktop coordinates, including secondary monitors with negative positions. Foreground and target-window checks still apply. Control IDs expire after one action or 45 seconds, and stale controls require a new observation. The mode exposes desktop and enabled web tools; coding and arbitrary shell tools stay in their respective modes.

In a packaged Gemma 4 E4B test, the agent inspected a real Windows form, typed the requested text, clicked its button and verified the result in **12.7 seconds**. Warm accessibility observations took **36–40 ms**, excluding screenshots and local-model decision time. Your app, hardware and chosen model affect performance.
