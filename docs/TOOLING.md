# Tooling and MCP capabilities (inventory taken 2026-10-30)

## MCP servers connected to this Claude Code session

| server | can it control Blender? | edit Unity scenes? | execute scripts? | capture previews? |
|---|---|---|---|---|
| claude-in-chrome | no | no | JavaScript in a browser tab only | screenshots of web pages only |
| Claude Docs, Gmail, Google Calendar, Google Drive, Indeed (claude.ai connectors) | no | no | no | no |
| project-scoped `exa` (only in `~/team`) | no | no | no | no |

There is no Blender MCP server and no Unity MCP server on this machine. Nothing in `~/.claude.json`, `settings.json` or `settings.local.json` registers one.

## What was used instead (supported, scriptable, reproducible)

- **Blender 5.2.3 LTS** installed with Homebrew. Driven headless: `blender -b -P blender/build_hall_of_doors.py -- ...`. This gives full control of geometry, materials, lighting, baking, glTF export and Cycles renders, and it is deterministic, which an interactive MCP session is not.
- **Unity 6000.3.27f2** installed through Unity Hub's headless CLI with Android Build Support, OpenJDK, SDK and NDK. Driven with `Unity -batchmode -executeMethod ...` for package installation, scene construction, lightmap baking and APK builds (`unity/Fable/Assets/Fable/Editor/FableBuild.cs`).
- **adb** (android-platform-tools) for installing to the Quest, pulling headset screenshots (`adb shell screencap`), logcat and OVR Metrics.
- **Go 1.24** for the interpreter service.

## Optional MCP servers, if interactive control is wanted later

- Blender: `blender-mcp` (ahujasid), a Blender add-on plus `uvx blender-mcp`; register under `mcpServers` in `~/.claude.json`. Adds live scene inspection and viewport screenshots from Claude.
- Unity: `unity-mcp` (CoplayDev) or similar; a UPM package plus a local server. Adds live hierarchy edits, console reading and Play Mode control. Both would require a Claude Code restart to appear and were not needed for the batch pipeline above.

## Blocked on the user

- **Unity licence.** The editor starts but reports `No valid Unity Editor license found`. The entitlement file in `~/Library/Unity/licenses` dates from April 2026 and no longer validates. Unity Hub has been launched; signing in there once activates a Personal licence for this machine and every batch command in this repo works afterwards.
- **Headset.** No Quest was attached over USB during this session (`adb devices` empty). Headset captures and measured frame timings require it.
- **Claude API key.** `ANTHROPIC_API_KEY` is unset and the `ant` CLI is not installed, so the interpreter was exercised with the validator only; live generation runs with `fable-interpreter generate` once a key is present.
