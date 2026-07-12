"""AgenticWisp command-line entry point — the single dispatcher behind both the
`wisp` console script (pip/pipx) and the `bin/wisp` shim (run-from-checkout).

  wisp {up | down | status | signal <event> | watch [--simple] | demo
        | install-hooks | uninstall-hooks}
"""
import os
import shutil
import signal as _signal
import subprocess
import sys

from agenticwisp import i18n

RUN_DIR = os.path.expanduser("~/.agenticwisp")
PIDFILE = os.path.join(RUN_DIR, "wispd.pid")
LOGFILE = os.path.join(RUN_DIR, "wispd.log")

USAGE_EN = ("usage: wisp {up|down|status|signal <event>|watch [--simple]|demo|"
            "install-hooks|uninstall-hooks}")
USAGE_ZH = ("用法: wisp {up|down|status|signal <event>|watch [--simple]|demo|"
            "install-hooks|uninstall-hooks}")


def _msg(en, zh):
    print(zh if i18n.lang() == "zh" else en)


def _port():
    try:
        return int(os.environ.get("WISP_PORT", 9099))
    except (TypeError, ValueError):
        return 9099


def _read_pid():
    try:
        with open(PIDFILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _running():
    pid = _read_pid()
    if pid is None:
        return None
    try:
        os.kill(pid, 0)
        return pid
    except OSError:
        return None


def _have_textual():
    try:
        import textual  # noqa: F401
        return True
    except Exception:
        return False


def _textual_hint():
    _msg("No Python with 'textual' found.", "找不到装了 textual 的 python。")
    _msg("  Install it:  pipx install 'agenticwisp[tui]'   (or: pip install textual)",
         "  安装:  pipx install 'agenticwisp[tui]'   (或: pip install textual)")
    _msg("  Or run the stdlib-only lamp:  wisp watch --simple",
         "  或用纯 stdlib 的简易灯:  wisp watch --simple")


def _wisp_launcher():
    """Absolute, PATH-independent launcher for the hook command."""
    env = os.environ.get("WISP_LAUNCHER")
    if env:
        return env
    found = shutil.which("wisp")
    if found:
        return found
    argv0 = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    if argv0 and os.path.basename(argv0) == "wisp":
        return argv0
    return "wisp"


def _cmd_signal(argv):
    try:
        from agenticwisp import signal as sig
        return sig.main(argv)
    except Exception:
        return 0  # a broken light must never break a hook


def _cmd_watch(argv):
    if argv and argv[0] == "--simple":
        from agenticwisp import lamp
        return lamp.main(argv[1:]) or 0
    if not _have_textual():
        _textual_hint()
        return 1
    from agenticwisp.tui.app import run_app
    run_app()
    return 0


def _cmd_demo(argv):
    if not _have_textual():
        _textual_hint()
        return 1
    from agenticwisp import demo
    demo.run_demo()
    return 0


def _cmd_install_hooks(argv):
    from agenticwisp import install_hooks
    base = argv[0] if argv else _wisp_launcher()
    added, backup, path = install_hooks.merge_into_settings(base)
    _msg("Merged AgenticWisp hooks into %s" % path,
         "已把 AgenticWisp 钩子合并进 %s" % path)
    if backup:
        _msg("  backup saved to %s" % backup,
             "  备份已保存到 %s" % backup)
    _msg("  events wired: %s" % (", ".join(added) if added else "(already installed)"),
         "  已接线的事件: %s" % (", ".join(added) if added else "(已安装)"))
    _msg("  hook command base: %s" % base,
         "  钩子命令基址: %s" % base)
    _msg("Restart your Claude Code session to activate the hooks.",
         "重启你的 Claude Code 会话以激活钩子。")
    return 0


def _cmd_uninstall_hooks(argv):
    from agenticwisp import install_hooks
    removed, backup, path = install_hooks.remove_from_settings()
    _msg("Removed AgenticWisp hooks from %s" % path,
         "已从 %s 移除 AgenticWisp 钩子" % path)
    if backup:
        _msg("  backup saved to %s" % backup,
             "  备份已保存到 %s" % backup)
    _msg("  events removed: %s"
         % (", ".join(sorted(set(removed))) if removed else "(none present)"),
         "  已移除的事件: %s"
         % (", ".join(sorted(set(removed))) if removed else "(无)"))
    return 0


def _cmd_up(argv):
    pid = _running()
    if pid:
        _msg("hub already running (pid %d)" % pid, "中枢已在运行 (pid %d)" % pid)
        return 0
    os.makedirs(RUN_DIR, exist_ok=True)
    port = _port()
    env = dict(os.environ, WISP_PORT=str(port))
    log = open(LOGFILE, "ab")
    proc = subprocess.Popen([sys.executable, "-m", "agenticwisp.wispd"],
                            stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                            start_new_session=True, env=env)
    log.close()
    with open(PIDFILE, "w") as f:
        f.write(str(proc.pid))
    _msg("hub started (pid %d), port %d, log %s" % (proc.pid, port, LOGFILE),
         "中枢已启动 (pid %d),端口 %d,日志 %s" % (proc.pid, port, LOGFILE))
    return 0


def _cmd_down(argv):
    pid = _read_pid()
    if pid:
        try:
            os.kill(pid, _signal.SIGTERM)
        except OSError:
            pass
    try:
        os.remove(PIDFILE)
    except OSError:
        pass
    _msg("hub stopped", "中枢已停止")
    return 0


def _cmd_status(argv):
    pid = _running()
    if not pid:
        _msg("not running", "未运行")
        return 0
    import urllib.request
    try:
        url = "http://127.0.0.1:%d/state" % _port()
        state = urllib.request.urlopen(url, timeout=2).read().decode().strip()
    except Exception:
        state = "?"
    _msg("running (pid %d), state: %s" % (pid, state),
         "运行中 (pid %d),当前状态: %s" % (pid, state))
    return 0


_COMMANDS = {
    "up": _cmd_up, "down": _cmd_down, "status": _cmd_status,
    "signal": _cmd_signal, "watch": _cmd_watch, "demo": _cmd_demo,
    "install-hooks": _cmd_install_hooks, "uninstall-hooks": _cmd_uninstall_hooks,
}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else None
    fn = _COMMANDS.get(cmd)
    if fn is None:
        _msg(USAGE_EN, USAGE_ZH)
        return 1
    return fn(argv[1:])


if __name__ == "__main__":
    sys.exit(main())
