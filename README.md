<h1 align="center">AgenticWisp 🔦</h1>

<p align="center">
  <b>A signal light for a <i>remote</i> Claude Code session — see what your AI is doing, from wherever you are.</b>
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="core deps" src="https://img.shields.io/badge/core-stdlib%20only-brightgreen">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
</p>

<p align="center">
  <b>English</b> | <a href="README.zh-CN.md">简体中文</a>
</p>

---

> Think **Claude Traffic Light** — the glanceable red/yellow/green idea everyone loves — fused with Claude Code's built-in **status line** (model · context · tokens · cost). The traffic light gives you the state at a glance; the status line gives you the rich per-session detail. AgenticWisp does both — for a Claude that lives on a **remote** machine, over the SSH tunnel you already have open.

---

## The problem, and the fix

Your Claude Code session almost certainly isn't running on the laptop in front of you. It's on a GPU box down the hall, a cloud dev instance, a shared research server behind a VPN — reached over SSH, in a terminal tab you keep alt-tabbing back to. Is it still thinking? Running a tool? Sitting there quietly waiting on a permission prompt it asked you for five minutes ago? From a stale terminal window, you genuinely cannot tell.

AgenticWisp turns Claude's live state into a light. The **traffic-light** side is the aggregate glow — one glance tells you the busiest thing happening across every session on the box. The **status-line** side is what you get when you look closer — model, reasoning effort, context-window usage, tokens, and running cost, per session, updated live. Claude's hooks report state to a tiny hub on the server; the signal rides back to you over **the SSH tunnel you already have** — no cloud, no exposed ports, nothing new to trust.

## Who's this for?

Anyone whose Claude lives on a box they reach over SSH or a VPN: grad students and researchers running things on a shared GPU box, ML folks on a compute cluster, developers on a cloud or remote dev machine, or just anyone who kicks off a long autonomous agent session and then has to walk away. If you've ever alt-tabbed to a dead-looking SSH window wondering "is it still thinking, or is it waiting on *me*?" — that's exactly the itch this scratches.

## What it looks like

```
              ╭──────────────────────────────────────╮
       · ✦    │            // TOOL //                  │    ✦ ·
     ✦        │           ───────────────              │        ✦
       · ✦    │           ▀█▀ ▄▀▄ ▄▀▄ █                 │    ✦ ·      ← Reactor Core: neon
              │            █  █ █ █ █ █                 │               plasma + data-rain +
              │            █  ▀▄▀ ▀▄▀ █▄▄               │               scanline, state spelled
              │           ───────────────              │               out big, HUD-titled
              ╰──────────────────────────────────────╯

 #  session          model       state        effort   ctx           heart          time   token
▸1  agentic-wisp     sonnet-5    ● tool        high     ██████░░ 74%  ▂▄▆█▆▄▂▁▂▄▆█   0:42  18.4k    ← one row per live
    ↳ Explore                   ● thinking    medium   ███░░░░░ 31%  ▁▂▃▂▁▁▂▃▁▂▃▂   0:05   2.1k       session, subagents
 2  data-pipeline    opus-4-8    ● thinking    medium   ██░░░░░░ 22%  ▂▁▁▂▃▂▁▁▂▃▁▂   1:03  41.2k       nested underneath
 3  api-server       haiku-4-5   ● idle        —        █░░░░░░░  9%  ▁▁▁▁▂▁▁▁▁▁▁▁   3:20   5.0k

【 ＵＳＡＧＥ / ＧＬＯＢＡＬ 】  USAGE  $2.14   IN 128.4k ▸ OUT 22.7k ▸ CACHE 610.2k ▸ 9 TURNS ▸ 3 LIVE   ← Usage HUD: running $ cost
```

The "light" can be that cinematic terminal panel (the *Reactor Core*), a browser page for a second monitor, or — once the office IT department approves a USB device — a physical Arduino traffic light on your desk.

## Features

- **Multi-session aware** — sees every live Claude Code session on the box, by its real name (from `/rename`) and working directory, so you never have to guess which window is which.
- **Aggregate light, or zoom in** — one glance shows the "busiest" state across everything; press a number to focus a single session when you need the detail.
- **5 states, animated, always readable** — hue is always the state, so you can tell at a glance even mid-animation; only brightness/texture move.
- **A cyberpunk neon look built for the long haul** — the panel is a neon HUD on black, tuned for cross-continental SSH (low frame rate, deterministic frames, forced truecolor) so it stays smooth instead of turning into a slideshow.
- **Subagent tracking** — spun-up subagents show up as their own live sub-rows, each with its own state and heartbeat, so you can see delegation happening in real time.
- **Live neon heartbeats** — every row pulses by state, and pulses harder the moment that session's token usage jumps — a busy agent visibly *looks* busy.
- **Rich per-row telemetry** — model, reasoning effort, a context-window gauge (**cyan → amber → pink** as it fills), time-in-state, and cumulative tokens, per session and per subagent. This is the status-line half of the idea.
- **Usage HUD** — a running total-cost estimate across every session, broken down by model, with cheap cache reads de-weighted so the number reflects what you actually spent.
- **English or Chinese, your call** — set `WISP_LANG` once and every surface (panel, browser page, simple lamp, CLI) follows.
- **Three display ends for wherever you're looking** — a full `textual` terminal panel, a self-contained browser page, and a zero-dependency fallback lamp.
- **Never breaks Claude** — the hook client has a 0.3-second timeout, swallows every error, and always exits 0. The light can fail; your session never will.
- **No cloud, no exposed ports** — everything rides your existing SSH tunnel; the hub binds `127.0.0.1` only.
- **Stdlib-only core** — the hub, hooks, and browser lamp need nothing beyond the Python standard library. Only the fancy terminal panel needs `textual`.

## Quick start

```bash
git clone https://github.com/martinghl/AgenticWisp.git
cd AgenticWisp

# (optional but recommended) a virtualenv the launcher will auto-detect:
python3 -m venv .venv
.venv/bin/pip install textual        # or: .venv/bin/pip install -r requirements-tui.txt

# 1. start the state hub (backgrounds itself; binds 127.0.0.1 only)
bin/wisp up

# 2. in another SSH window, open the light:
bin/wisp watch                        # fancy Reactor Core (auto-finds a python with textual)
#   bin/wisp watch --simple           # stdlib-only fallback (no textual needed)

bin/wisp status                       # what's the current aggregate state?
bin/wisp down                         # stop the hub
```

> `bin/wisp watch` automatically picks the first interpreter that has `textual`
> (checking `$WISP_PYTHON`, then a couple of fallback candidates), so you
> don't have to type a long interpreter path every time.

## Connect it to Claude Code

Wire Claude's hooks to the light with **one command** — it fills in its own absolute path and merges into your `~/.claude/settings.json` (with a backup, idempotent):

```bash
bin/wisp install-hooks
# then restart your Claude Code session to activate the hooks
```

Prefer to do it by hand? Copy the `hooks` block from [`hooks/settings-snippet.json`](hooks/settings-snippet.json) into `~/.claude/settings.json`, replacing the placeholder path in each hook command with the path to your own clone.

Now the light follows Claude automatically: you type → 🟡, it runs a tool → 🟣, it needs your approval → 🔵, it finishes → 🟢.

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

- **`wisp signal`** (hook client) posts `{session_id, state, tool, effort}` — plus `agent_id`/`agent_type` when the event comes from a subagent — to the hub and exits. Model and context-window usage are read separately by the hub from the session transcripts.
- **`wispd`** (hub) keeps per-session state (and per-subagent state), joins it with Claude Code's own live-session registry (`~/.claude/sessions/*.json`) for real names/cwd, and parses each session's transcript for token usage. It serves `GET /sessions`, `GET /aggregate` (alias `GET /state`), `GET /usage` (per-model tokens + estimated cost), and `GET /` (the browser lamp page).
- **Displays** poll the hub. The terminal lamp runs *on the server* and paints your SSH window; the browser lamp is a page the hub serves, reached via a one-line `ssh -L` forward.

## Using the terminal panel

| key | action |
|-----|--------|
| `1`–`9` | **focus** the Nth session (the Reactor Core tracks only that one) |
| `0` / `Esc` | back to the **aggregate** overview |
| `q` | quit |

The panel is a neon HUD on black, in three zones top to bottom:

- a big animated **Reactor Core** — a magenta/cyan/purple plasma field with a faint katakana **data-rain**, a moving **scanline**, an occasional **glitch**, a `// STATE //`-style HUD title, and the aggregate (or focused) state spelled out **big, in 3-row half-block ASCII art** (falling back to a small one-line label if the panel is too narrow or short);
- a **numbered session table** — each row shows **model**, **state**, **reasoning effort**, a **context-window gauge**, a neon heartbeat, **time in state**, and **cumulative tokens**; a session's running **subagents** appear beneath it as `↳`-prefixed sub-rows with the same telemetry;
- a **Usage HUD** — a glowing running cost total, an input/output/cache token breakdown, and a per-model neon energy bar for the top models by spend.

Tuned for cross-continental SSH: low frame rate, deterministic per-cell updates, forced truecolor, bright text on dark fills so it stays readable over a laggy link.

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
| `WISP_LANG` | `en` | `en` \| `zh` — sets the language of every surface: terminal panel, browser page, simple lamp, and CLI output |

**Frame rate:** the Reactor Core and Usage HUD run at 6 fps by default (tuned for rendering over a long-distance SSH link). Edit the `set_interval(1 / 6, ...)` calls in `agenticwisp/tui/app.py` — raise them (`1 / 10`) on a fast/local connection, or lower them (`1 / 3`) to save CPU.

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

- **Physical light** — a real Arduino traffic-light module driven over USB, mapping to red/yellow/green for the one session you care about most (the architecture already exposes `GET /aggregate` for exactly this) — waiting on IT to approve the USB device.
- Per-tool colors, custom palettes, and richer browser animations.

## License

[MIT](LICENSE) — do whatever you like; a copyright notice is appreciated.

---

<sub>AgenticWisp is a couple of overworked PhD students scratching their own itch — a for-fun side project born out of one too many "wait, is my Claude still running?" moments, not a company product. Enjoy it in that spirit.</sub>
