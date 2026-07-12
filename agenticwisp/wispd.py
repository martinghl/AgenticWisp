"""AgenticWisp 状态中枢:按 session_id 存细状态(含子agent),喂给所有显示端。"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agenticwisp import protocol
from agenticwisp.page import render_page
from agenticwisp import roster
from agenticwisp import usage
from agenticwisp import pricing
from agenticwisp import i18n

DEFAULT_PORT = 9099
SUBAGENT_TTL = 90.0  # 秒:子agent 超此未更新即视为结束(防 SubagentStop 漏)
USAGE_MIN_INTERVAL = 2.0  # 秒:每 session transcript 最多这么久重读一次(限流)


class SessionStore:
    """线程安全:按 session_id 存 {state, tool, updated_at, subagents:{agent_id:{...}}}。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions = {}

    def _ensure(self, sid):
        s = self._sessions.get(sid)
        if s is None:
            s = {"state": protocol.IDLE, "tool": None, "effort": None,
                 "updated_at": 0.0, "subagents": {}}
            self._sessions[sid] = s
        return s

    def update(self, session_id, state, tool=None, effort=None, now=None):
        norm = protocol.normalize(state)
        if norm is None:
            return None
        sid = session_id or "legacy"
        with self._lock:
            s = self._ensure(sid)
            s["state"], s["tool"] = norm, (tool if norm == protocol.TOOL else None)
            if effort is not None:
                s["effort"] = effort
            s["updated_at"] = now if now is not None else time.time()
        return norm

    def update_subagent(self, session_id, agent_id, state, tool=None, agent_type=None,
                        effort=None, now=None):
        norm = protocol.normalize(state)
        if norm is None or not agent_id:
            return None
        sid = session_id or "legacy"
        with self._lock:
            s = self._ensure(sid)
            sub = s["subagents"].get(agent_id, {})
            sub["state"], sub["tool"] = norm, (tool if norm == protocol.TOOL else None)
            sub["type"] = agent_type or sub.get("type") or "agent"
            if effort is not None:
                sub["effort"] = effort
            sub["updated_at"] = now if now is not None else time.time()
            s["subagents"][agent_id] = sub
        return norm

    def remove_subagent(self, session_id, agent_id):
        sid = session_id or "legacy"
        with self._lock:
            s = self._sessions.get(sid)
            if s and agent_id in s.get("subagents", {}):
                del s["subagents"][agent_id]

    def snapshot(self):
        with self._lock:
            return {sid: {"state": v["state"], "tool": v.get("tool"),
                          "effort": v.get("effort"),
                          "updated_at": v.get("updated_at", 0.0),
                          "subagents": {aid: dict(sub)
                                        for aid, sub in v.get("subagents", {}).items()}}
                    for sid, v in self._sessions.items()}


def _empty_detail():
    return {"models": {}, "web_search": 0, "web_fetch": 0}


def _merge_detail(dst, delta):
    for model, comp in delta.get("models", {}).items():
        m = dst["models"].setdefault(model, {"in": 0, "out": 0, "cr": 0, "cc": 0, "turns": 0})
        for k in ("in", "out", "cr", "cc", "turns"):
            m[k] += comp.get(k, 0)
    dst["web_search"] += delta.get("web_search", 0)
    dst["web_fetch"] += delta.get("web_fetch", 0)


def _detail_total(detail):
    return sum(m["in"] + m["out"] + m["cr"] + m["cc"] for m in detail["models"].values())


class UsageTracker:
    """按 session 增量累计 transcript token(按模型明细);限流每 min_interval 秒读一次。线程安全。"""

    def __init__(self, projects_dir="~/.claude/projects", min_interval=USAGE_MIN_INTERVAL):
        self._projects_dir = projects_dir
        self._min = min_interval
        self._lock = threading.Lock()
        self._st = {}    # sid -> {path, offset, last_read, detail, last}
        self._sub = {}   # f"{parent}\x00{aid}" -> {path, offset, last_read, last}

    def _ensure(self, sid):
        e = self._st.get(sid)
        if e is None:
            e = {"path": None, "offset": 0, "last_read": -1e9,
                 "detail": _empty_detail(), "last": None}
            self._st[sid] = e
        return e

    def _refresh(self, sid, now):
        """(须持锁) 限流增量读,更新 detail。返回 entry。"""
        e = self._ensure(sid)
        if now - e["last_read"] < self._min:
            return e
        e["last_read"] = now
        if e["path"] is None:
            e["path"] = usage.find_transcript(sid, self._projects_dir)
            if e["path"] is None:
                return e
        old = e["offset"]
        delta, new_off = usage.scan_usage_detailed(e["path"], e["offset"])
        if new_off < old:                    # 截断/轮转:detail 清零重算
            e["detail"] = _empty_detail()
        _merge_detail(e["detail"], delta)
        if new_off < old:
            e["last"] = None
        if delta.get("last"):
            e["last"] = delta["last"]
        e["offset"] = new_off
        return e

    def tokens_for(self, session_id, now=None):
        if not session_id:
            return None
        now = now if now is not None else time.time()
        with self._lock:
            e = self._refresh(session_id, now)
            if e["path"] is None:
                return None
            return _detail_total(e["detail"])

    def model_ctx_for(self, session_id, now=None):
        if not session_id:
            return (None, None)
        now = now if now is not None else time.time()
        with self._lock:
            e = self._refresh(session_id, now)
            last = e["last"]
        return (last["model"], last["ctx"]) if last else (None, None)

    def subagent_model_ctx(self, parent_sid, agent_id, now=None):
        if not parent_sid or not agent_id:
            return (None, None)
        now = now if now is not None else time.time()
        key = parent_sid + "\x00" + agent_id
        with self._lock:
            e = self._sub.get(key)
            if e is None:
                e = {"path": None, "offset": 0, "last_read": -1e9, "last": None}
                self._sub[key] = e
            if now - e["last_read"] >= self._min:
                e["last_read"] = now
                if e["path"] is None:
                    e["path"] = usage.find_subagent_transcript(parent_sid, agent_id, self._projects_dir)
                if e["path"]:
                    old = e["offset"]
                    delta, new_off = usage.scan_usage_detailed(e["path"], e["offset"])
                    if new_off < old:
                        e["last"] = None
                    if delta.get("last"):
                        e["last"] = delta["last"]
                    e["offset"] = new_off
            last = e["last"]
        return (last["model"], last["ctx"]) if last else (None, None)

    def aggregate(self, session_ids, now=None):
        """全局聚合给定活 session 的用量 + 成本。"""
        now = now if now is not None else time.time()
        merged = _empty_detail()
        with self._lock:
            for sid in session_ids:
                self._refresh(sid, now)
            for sid in session_ids:
                e = self._st.get(sid)
                if e:
                    _merge_detail(merged, e["detail"])
        by_model = []
        tin = tout = tcr = tcc = tturns = 0
        total_cost = 0.0
        for model, m in merged["models"].items():
            c = pricing.cost(model, m["in"], m["out"], m["cr"], m["cc"])
            by_model.append({"model": model, "turns": m["turns"],
                             "tokens": m["in"] + m["out"] + m["cr"] + m["cc"], "cost_usd": c})
            tin += m["in"]; tout += m["out"]; tcr += m["cr"]; tcc += m["cc"]
            tturns += m["turns"]; total_cost += c
        by_model.sort(key=lambda r: -r["cost_usd"])
        return {"cost_usd": total_cost, "in": tin, "out": tout, "cache": tcr + tcc,
                "turns": tturns, "sessions": len(list(session_ids)),
                "web_search": merged["web_search"], "web_fetch": merged["web_fetch"],
                "by_model": by_model}

    def forget(self, session_id):
        with self._lock:
            self._st.pop(session_id, None)

    def prune(self, live_ids):
        """Drops _st / _sub entries whose (parent) session_id is not in the given live set."""
        keep = set(live_ids)
        with self._lock:
            for sid in list(self._st):
                if sid not in keep:
                    del self._st[sid]
            for key in list(self._sub):
                if key.split("\x00", 1)[0] not in keep:
                    del self._sub[key]


def _active_subagents(detail, now, ttl):
    out = []
    for aid, sub in (detail.get("subagents") or {}).items():
        if now - sub.get("updated_at", 0.0) <= ttl:
            out.append({"id": aid, "type": sub.get("type", "agent"),
                        "state": sub["state"], "tool": sub.get("tool"),
                        "effort": sub.get("effort")})
    return out


def build_sessions(roster_map, store_snapshot, now=None, ttl=SUBAGENT_TTL):
    """合并花名册与细状态 → [{id,name,cwd,state,tool,subagents:[...]}]。
    花名册非空时丢弃不在册的 store-only session;为空时保留(fallback)。子agent 按 TTL 过滤。"""
    now = now if now is not None else time.time()
    out = []
    for sid, meta in roster_map.items():
        detail = store_snapshot.get(sid)
        if detail:
            state, tool = detail["state"], detail.get("tool")
            subs = _active_subagents(detail, now, ttl)
        else:
            state = protocol.THINKING if meta.get("status") == "busy" else protocol.IDLE
            tool, subs = None, []
        row = {"id": sid, "name": meta.get("name", sid[:8]), "cwd": meta.get("cwd", ""),
               "state": state, "tool": tool,
               "effort": detail.get("effort") if detail else None}
        if subs:                       # 只在有子agent时加键,避免打破已有精确断言测试
            row["subagents"] = subs
        out.append(row)
    if not roster_map:
        for sid, detail in store_snapshot.items():
            subs = _active_subagents(detail, now, ttl)
            row = {"id": sid, "name": sid[:8], "cwd": "",
                   "state": detail["state"], "tool": detail.get("tool"),
                   "effort": detail.get("effort")}
            if subs:
                row["subagents"] = subs
            out.append(row)
    return out


def _aggregate_state(sessions):
    states = []
    for s in sessions:
        states.append(s["state"])
        states.extend(sub["state"] for sub in s.get("subagents", []))
    return protocol.aggregate(states)


def make_handler(store, sessions_dir="~/.claude/sessions", tracker=None):
    tracker = tracker if tracker is not None else UsageTracker()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="text/plain; charset=utf-8"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _sessions(self):
            rows = build_sessions(roster.read_roster(sessions_dir), store.snapshot())
            now = time.time()
            for row in rows:
                row["tokens"] = tracker.tokens_for(row["id"], now)
                model, ctx = tracker.model_ctx_for(row["id"], now)
                row["model"] = model
                row["ctx_used"] = ctx
                row["ctx_max"] = pricing.max_context(model) if model else None
                for sub in row.get("subagents", []):
                    m, c = tracker.subagent_model_ctx(row["id"], sub["id"], now)
                    sub["model"] = m
                    sub["ctx_used"] = c
                    sub["ctx_max"] = pricing.max_context(m) if m else None
            tracker.prune(row["id"] for row in rows)
            return rows

        def _usage(self):
            ids = [s["id"] for s in
                   build_sessions(roster.read_roster(sessions_dir), store.snapshot())]
            return tracker.aggregate(ids, time.time())

        def do_GET(self):
            if self.path in ("/state", "/aggregate"):
                self._send(200, _aggregate_state(self._sessions()))
            elif self.path == "/sessions":
                self._send(200, json.dumps(self._sessions(), ensure_ascii=False),
                           "application/json; charset=utf-8")
            elif self.path == "/usage":
                self._send(200, json.dumps(self._usage(), ensure_ascii=False),
                           "application/json; charset=utf-8")
            elif self.path == "/":
                self._send(200, render_page(), "text/html; charset=utf-8")
            else:
                self._send(404, "not found")

        def do_POST(self):
            if self.path != "/state":
                self._send(404, "not found")
                return
            length = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            try:
                payload = json.loads(raw) if raw.strip().startswith("{") else {"state": raw.strip()}
            except ValueError:
                payload = {"state": raw.strip()}
            sid, aid = payload.get("session_id"), payload.get("agent_id")
            if payload.get("kind") == "stop" and aid:
                store.remove_subagent(sid, aid)
                self._send(200, "ok")
                return
            if aid:
                result = store.update_subagent(sid, aid, payload.get("state"),
                                                payload.get("tool"), payload.get("agent_type"),
                                                payload.get("effort"))
            else:
                result = store.update(sid, payload.get("state"), payload.get("tool"),
                                      payload.get("effort"))
            if result is None:
                self._send(400, "invalid state")
            else:
                self._send(200, result)

    return Handler


def serve(port=DEFAULT_PORT, store=None, sessions_dir="~/.claude/sessions", tracker=None):
    store = store if store is not None else SessionStore()
    httpd = ThreadingHTTPServer(("127.0.0.1", port),
                                make_handler(store, sessions_dir, tracker))
    return httpd, store


def main():
    port = int(os.environ.get("WISP_PORT", DEFAULT_PORT))
    httpd, _ = serve(port)
    print(i18n.t("hub.listening", port=port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()


if __name__ == "__main__":
    main()
