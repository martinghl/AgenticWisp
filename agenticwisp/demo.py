"""Self-contained `wisp demo`: an ephemeral in-process hub seeded with a lifelike
scene (6 sessions + 3 subagents), a background thread that cycles the aggregate
state idle -> thinking -> tool -> PENDING -> error while token/cost climb, and the
real `watch` panel in the foreground. No real Claude, no hooks."""
import json
import os
import shutil
import tempfile
import threading

from agenticwisp.wispd import SessionStore, UsageTracker, serve

# (sid, name, effort, tool_when_tool, model, in, out, cache_read, cache_creation)
SESSIONS = [
    ("s-diff", "diffusion-sweep", "high", "Bash", "claude-opus-4-8", 22000, 9000, 600000, 18000),
    ("s-fig", "figure-3-panels", "medium", None, "claude-sonnet-5", 14000, 6000, 320000, 9000),
    ("s-eval", "eval-harness", None, None, "claude-haiku-4-5-20251001", 8000, 3000, 90000, 4000),
    ("s-reb", "rebuttal-draft", "high", "Edit", "claude-opus-4-8", 26000, 11000, 720000, 15000),
    ("s-pipe", "data-pipeline", "low", "Read", "claude-sonnet-5", 12000, 5000, 210000, 7000),
    ("s-sweep", "sweep-runner", None, None, "claude-haiku-4-5-20251001", 5000, 2000, 48000, 3000),
]
SUBAGENTS = [("s-diff", "a-expl", "Explore"), ("s-diff", "a-task", "general-purpose"),
             ("s-pipe", "a-expl2", "Explore")]

STATE_CYCLE = ["idle", "thinking", "tool", "waiting", "error"]

# session states + subagent states per target; the group max equals the target,
# so protocol.aggregate(session + subagent states) == target (waiting renders as red PENDING).
STAGE = {
    "idle":     (["idle"] * 6, ["idle", "idle", "idle"]),
    "thinking": (["thinking", "thinking", "idle", "thinking", "idle", "thinking"], ["thinking", "idle", "thinking"]),
    "tool":     (["tool", "thinking", "idle", "tool", "thinking", "idle"], ["thinking", "tool", "thinking"]),
    "waiting":  (["waiting", "thinking", "idle", "tool", "thinking", "idle"], ["thinking", "tool", "idle"]),
    "error":    (["error", "thinking", "idle", "tool", "thinking", "idle"], ["thinking", "tool", "idle"]),
}


def _append_usage(proj, sid, model, i, o, cr, cc):
    line = {"message": {"model": model, "usage": {
        "input_tokens": i, "output_tokens": o,
        "cache_read_input_tokens": cr, "cache_creation_input_tokens": cc}}}
    with open(os.path.join(proj, sid + ".jsonl"), "a") as f:
        f.write(json.dumps(line) + "\n")


def seed(roster_dir, projects_dir):
    proj = os.path.join(projects_dir, "proj")
    os.makedirs(proj, exist_ok=True)
    for sid, name, eff, tool, model, i, o, cr, cc in SESSIONS:
        with open(os.path.join(roster_dir, sid + ".json"), "w") as f:
            json.dump({"sessionId": sid, "name": name, "cwd": "/home/you/research/" + name}, f)
        _append_usage(proj, sid, model, i, o, cr, cc)


def apply_stage(store, target):
    sess_states, sub_states = STAGE[target]
    for idx, (sid, name, eff, tool, *_rest) in enumerate(SESSIONS):
        st = sess_states[idx]
        store.update(sid, st, tool=(tool if st == "tool" else None),
                     effort=(eff if st != "idle" else None))
    for j, (sid, aid, atype) in enumerate(SUBAGENTS):
        st = sub_states[j]
        store.update_subagent(sid, aid, st, tool=("Grep" if st == "tool" else None), agent_type=atype)


def grow_usage(projects_dir, step):
    """Append another usage line per session so tokens/cost climb each tick."""
    proj = os.path.join(projects_dir, "proj")
    for sid, name, eff, tool, model, i, o, cr, cc in SESSIONS:
        _append_usage(proj, sid, model, i + 400 * step, o + 200 * step,
                      cr + 8000 * step, cc + 300 * step)


def _driver(store, projects_dir, interval, stop):
    step = 0
    while not stop.is_set():
        apply_stage(store, STATE_CYCLE[step % len(STATE_CYCLE)])
        if step:
            grow_usage(projects_dir, step)
        step += 1
        stop.wait(interval)


def run_demo(port=None, interval=None):
    if interval is None:
        try:
            interval = float(os.environ.get("WISP_DEMO_INTERVAL", "2.5"))
        except ValueError:
            interval = 2.5
    roster_dir = tempfile.mkdtemp(prefix="wisp-demo-roster-")
    projects_dir = tempfile.mkdtemp(prefix="wisp-demo-proj-")
    store = SessionStore()
    tracker = UsageTracker(projects_dir, min_interval=0.0)
    seed(roster_dir, projects_dir)
    apply_stage(store, "idle")
    httpd, _ = serve(port=port or 0, store=store, sessions_dir=roster_dir, tracker=tracker)
    bound = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    stop = threading.Event()
    threading.Thread(target=_driver, args=(store, projects_dir, interval, stop), daemon=True).start()
    os.environ["WISP_PORT"] = str(bound)
    try:
        from agenticwisp.tui.app import run_app
        run_app()
    finally:
        stop.set()
        httpd.shutdown()
        httpd.server_close()
        shutil.rmtree(roster_dir, ignore_errors=True)
        shutil.rmtree(projects_dir, ignore_errors=True)
