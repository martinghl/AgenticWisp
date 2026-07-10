<h1 align="center">AgenticWisp 🔦</h1>

<p align="center">
  <b>A signal light for a <i>remote</i> Claude Code session — see what your AI is doing, from wherever you are.</b>
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="core deps" src="https://img.shields.io/badge/core-stdlib%20only-brightgreen">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
</p>

---

Most of the time your Claude Code isn't running on your laptop — it's on a **remote Linux box** you reach over SSH (often behind a corporate VPN). You can't glance at a terminal on your desk to know whether it's **thinking**, **running a tool**, or **waiting for you**.

**AgenticWisp** turns Claude's live state into a light. Claude's hooks report state to a tiny hub on the server; the light travels back to you over the **SSH tunnel you already have** — no cloud, no exposed ports, no extra services.

```
Claude is:   🟢 idle      🟡 thinking     🟣 running a tool     🔵 waiting on you     🔴 error
```

The "light" can be a **cinematic terminal panel** (the *Reactor Core*), a **browser page**, or — down the road — a **physical Arduino traffic light** on your desk.

```
              ╭──────────────────────────╮
       · ✦    │       ────────────        │    ✦ ·
     ✦        │        T O O L            │        ✦        ← Reactor Core: the aggregate
       · ✦    │       ────────────        │    ✦ ·            state as a hue-locked plasma
              ╰──────────────────────────╯                   glow that breathes + sparks

   ▸ 1  agentic-wisp   ● tool · Bash    ▁▂▃▅▇▆▃▂▁▂         ← one numbered row per live
     2  data-pipeline  ● thinking       ▂▁▁▂▃▂▁▁▂▃           Claude session, each with a
     3  api-server     ● idle           ▁▁▁▁▂▁▁▁▁▁           live "heartbeat" sparkline

   1–9 focus a session   ·   0 / Esc overview   ·   q quit
```

## Features

- **Multi-session aware** — sees every live Claude Code session on the machine, by its real name (from `/rename`) and working directory.
- **Aggregate light** — one glance tells you the "busiest" state across all sessions; or press a number to **focus one session**.
- **5 states, animated** — hue is always the state (glanceable); only brightness/texture animate.
- **Three display ends**: a `textual` terminal panel, a self-contained browser page, and a stdlib-only fallback lamp.
- **Never breaks Claude** — the hook client has a 0.3 s timeout, swallows every error, and always exits 0.
- **No cloud, no exposed ports** — everything rides your existing SSH tunnel; the hub binds `127.0.0.1` only.
- **Zero dependencies for the core** — hub, hooks, and browser lamp are pure Python standard library. Only the fancy terminal panel needs `textual`.

## How it works

```
[ remote server (behind your VPN) ]                    [ your local machine ]

  Claude Code hooks
     └─ wisp signal <event> ──▶  wispd  ── the state hub ──┐
        (reads session_id/tool          127.0.0.1:9099     │  displays subscribe:
         from the hook's stdin)         + joins Claude's    │
                                        session roster      ├─ terminal lamp  → shown in your SSH window
                                        ~/.claude/sessions   │  (runs on the server)
                                                             └─ browser lamp   ◀─ ssh -L ─ your browser
```

- **`wisp signal`** (hook client) posts `{session_id, state, tool}` to the hub and exits.
- **`wispd`** (hub) keeps per-session state and joins it with Claude Code's own live-session registry (`~/.claude/sessions/*.json`) to get real names/cwd. It serves `GET /sessions`, `GET /aggregate`, and `GET /state`.
- **Displays** poll the hub. The terminal lamp runs *on the server* and paints your SSH window; the browser lamp is a page the hub serves, reached via a one-line `ssh -L` forward.

## Requirements

- **Python 3.9+** on the server (the core uses only the standard library).
- **[`textual`](https://textual.textualize.io/)** — only for the fancy `wisp watch` terminal panel. The `--simple` lamp and everything else need nothing extra.
- A terminal that supports **truecolor** for the full plasma effect (most do; there's a plain fallback if not).

## Quick start

```bash
git clone https://github.com/<you>/AgenticWisp.git
cd AgenticWisp

# (optional but recommended) a virtualenv the launcher will auto-detect:
python3 -m venv .venv
.venv/bin/pip install textual        # or:  pip install ".[tui]"

# 1. start the state hub (backgrounds itself; binds 127.0.0.1 only)
bin/wisp up

# 2. in another SSH window, open the light:
bin/wisp watch                        # fancy Reactor Core (auto-finds a python with textual)
#   bin/wisp watch --simple           # stdlib-only fallback (no textual needed)

bin/wisp status                       # what's the current aggregate state?
bin/wisp down                         # stop the hub
```

> `bin/wisp watch` automatically picks the first interpreter that has `textual`
> (checking `$WISP_PYTHON`, a local `.venv`, then `python3`/`python`), so you
> never have to type a long interpreter path.

## Connect it to Claude Code

Wire Claude's hooks to the light with **one command** — it fills in its own absolute path and merges into your `~/.claude/settings.json` (with a backup, idempotent):

```bash
bin/wisp install-hooks
# then restart your Claude Code session to activate the hooks
```

Prefer to do it by hand? Copy the `hooks` block from [`hooks/settings-snippet.json`](hooks/settings-snippet.json) into `~/.claude/settings.json`, replacing `/ABSOLUTE/PATH/TO/AgenticWisp` with your clone path.

Now the light follows Claude automatically: you type → 🟡, it runs a tool → 🟣, it needs your approval → 🔵, it finishes → 🟢.

## Using the terminal panel

| key | action |
|-----|--------|
| `1`–`9` | **focus** the Nth session (the big lamp tracks only that one) |
| `0` / `Esc` | back to the **aggregate** overview |
| `q` | quit |

The panel shows a big animated **Reactor Core** (aggregate state) on top and a **numbered session table** below, each row ending in a live heartbeat sparkline of that session's recent activity.

## Browser lamp

The hub serves a self-contained page at `/`. From your local machine, forward the port over SSH and open it:

```bash
ssh -L 9099:localhost:9099 <your-server>
# then open http://localhost:9099 in your browser
```

Multi-session cards, a breathing canvas lamp, and click-to-focus — nice for a second monitor.

## Configuration

| variable | default | meaning |
|----------|---------|---------|
| `WISP_PORT` | `9099` | hub port (hub always binds `127.0.0.1`) |
| `WISP_PYTHON` | `python3` | interpreter for the hub/hooks; also the first candidate for `watch` |
| `WISP_PLAIN` | unset | set to `1` for a flat color block instead of the plasma effect |
| `WISP_POLL` | `0.25` | poll interval (seconds) for the `--simple` lamp |

**Frame rate:** the Reactor Core runs at 6 fps by default (tuned for rendering over a long-distance SSH link). Edit `set_interval(1 / 6, ...)` in `agenticwisp/tui/app.py` — raise it (`1/10`) on a fast/local connection, or lower it (`1/3`) to save CPU.

> **Tip for slow/remote links:** a full-screen animated terminal is heavy over transcontinental SSH. If it feels choppy, lower the frame rate or use `WISP_PLAIN=1` (or `wisp watch --simple`).

## State → color

| state | color | when |
|-------|-------|------|
| `idle` | 🟢 green `#22a04a` | Claude finished / is waiting for your next prompt |
| `thinking` | 🟡 yellow `#d2aa1e` | reasoning between tool calls |
| `tool` | 🟣 purple `#8b5cf6` | running a tool |
| `waiting` | 🔵 cyan `#22b8cf` | needs your input / a permission decision |
| `error` | 🔴 red `#e5484d` | a tool or turn failed |

When several sessions are live, the aggregate lamp shows the highest-priority state:
`waiting > error > tool > thinking > idle`.

## Tests

```bash
python3 -m unittest discover -s tests          # core suite (stdlib only)
# with textual installed, the terminal-panel tests run too:
.venv/bin/python -m unittest discover -s tests
```

## Roadmap

- **Physical light** — a real Arduino traffic-light module driven over USB, mapping to red/yellow/green for the one session you care about most (the architecture already exposes `GET /aggregate` for exactly this).
- Per-tool colors, custom palettes, and richer browser animations.

## License

[MIT](LICENSE) — do whatever you like; a copyright notice is appreciated.
