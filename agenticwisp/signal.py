"""AgenticWisp hook 客户端:把(session, 状态)发给中枢就退出;绝不拖慢 Claude。"""
import http.client
import json
import os
import sys

from agenticwisp import protocol

DEFAULT_PORT = 9099
DEFAULT_TIMEOUT = 0.3  # 秒。极短:连不上立刻放弃


def read_stdin_context(stream):
    """从钩子 stdin 的 JSON 读 (session_id, tool_name);任何问题返回 (None, None)。"""
    try:
        raw = stream.read()
        if not raw or not raw.strip():
            return None, None
        d = json.loads(raw)
        if not isinstance(d, dict):
            return None, None
        return d.get("session_id"), d.get("tool_name")
    except Exception:
        return None, None


def send(state, session_id=None, tool=None, host="127.0.0.1", port=DEFAULT_PORT, timeout=DEFAULT_TIMEOUT):
    """更新某 session 的细状态。成功返回规约状态;任何失败返回 None(绝不抛)。"""
    norm = protocol.normalize(state)
    if norm is None:
        return None
    try:
        body = json.dumps({
            "session_id": session_id or os.environ.get("WISP_SESSION") or "manual",
            "state": norm,
            "tool": tool,
        })
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("POST", "/state", body=body.encode("utf-8"),
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return norm if resp.status == 200 else None
    except Exception:
        return None  # 中枢没起 / 超时 / 网络错 / 序列化错 —— 静默,别打扰 Claude


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        return 0
    session_id, tool = (None, None)
    try:
        if sys.stdin is not None and not sys.stdin.isatty():
            session_id, tool = read_stdin_context(sys.stdin)
    except Exception:
        session_id, tool = None, None
    try:
        port = int(os.environ.get("WISP_PORT", DEFAULT_PORT))
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    send(argv[0], session_id=session_id, tool=tool, port=port)
    return 0  # 永远返回 0:灯坏了不能让钩子失败


if __name__ == "__main__":
    sys.exit(main())
