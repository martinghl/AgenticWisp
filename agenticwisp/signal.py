"""AgenticWisp hook 客户端:把(session/子agent, 状态)发给中枢就退出;绝不拖慢 Claude。"""
import http.client
import json
import os
import sys

from agenticwisp import protocol

DEFAULT_PORT = 9099
DEFAULT_TIMEOUT = 0.3  # 秒。极短:连不上立刻放弃


def read_stdin_context(stream):
    """从钩子 stdin 的 JSON 读 {session_id, tool, agent_id, agent_type, effort};任何问题返回 {}。"""
    try:
        raw = stream.read()
        if not raw or not raw.strip():
            return {}
        d = json.loads(raw)
        if not isinstance(d, dict):
            return {}
        eff = d.get("effort")
        effort = eff.get("level") if isinstance(eff, dict) else None
        return {"session_id": d.get("session_id"), "tool": d.get("tool_name"),
                "agent_id": d.get("agent_id"), "agent_type": d.get("agent_type"),
                "effort": effort}
    except Exception:
        return {}


def _post(body, host="127.0.0.1", port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """POST 一个 JSON body 到 /state;任何失败返回 None(绝不抛)。"""
    try:
        data = json.dumps(body).encode("utf-8")
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("POST", "/state", body=data, headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp.status == 200
    except Exception:
        return None


def send(state, session_id=None, tool=None, host="127.0.0.1", port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """更新某 session 自己的状态。成功返回规约状态;失败返回 None。"""
    norm = protocol.normalize(state)
    if norm is None:
        return None
    ok = _post({"session_id": session_id or os.environ.get("WISP_SESSION") or "manual",
                "state": norm, "tool": tool}, host, port, timeout)
    return norm if ok else None


def _port():
    try:
        return int(os.environ.get("WISP_PORT", DEFAULT_PORT))
    except (TypeError, ValueError):
        return DEFAULT_PORT


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        return 0
    event = argv[0]
    ctx = {}
    try:
        if sys.stdin is not None and not sys.stdin.isatty():
            ctx = read_stdin_context(sys.stdin)
    except Exception:
        ctx = {}
    sid = ctx.get("session_id") or os.environ.get("WISP_SESSION") or "manual"
    aid = ctx.get("agent_id")
    port = _port()
    try:
        if event == "SubagentStop":
            if aid:
                _post({"session_id": sid, "agent_id": aid, "kind": "stop"}, port=port)
            return 0
        if event == "SubagentStart":
            state = protocol.THINKING
        else:
            state = protocol.state_for_event(event, ctx.get("tool"))
        if state is None:
            return 0
        body = {"session_id": sid, "state": state, "tool": ctx.get("tool")}
        if ctx.get("effort"):
            body["effort"] = ctx.get("effort")
        if aid:
            body["agent_id"] = aid
            if ctx.get("agent_type"):
                body["agent_type"] = ctx.get("agent_type")
        _post(body, port=port)
    except Exception:
        pass
    return 0  # 永远返回 0:灯坏了不能让钩子失败


if __name__ == "__main__":
    sys.exit(main())
