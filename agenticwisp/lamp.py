"""AgenticWisp 终端灯:订阅中枢,把整屏刷成状态色。"""
import http.client
import os
import shutil
import sys
import time

from agenticwisp import protocol, i18n

DEFAULT_PORT = 9099
ESC = "\033"


def render(state, cols, rows, connected=True):
    """把状态渲染成填满终端的 ANSI 字符串(纯函数,便于测试)。"""
    if not connected:
        bg, label = (40, 40, 40), i18n.t("lamp.waiting")
    else:
        disp = protocol.DISPLAY.get(state)
        if disp is None:
            bg, label = (40, 40, 40), i18n.t("lamp.unknown", state=state)
        else:
            bg, label = disp["rgb"], i18n.state_label(state)
    r, g, b = bg
    fill = f"{ESC}[48;2;{r};{g};{b}m"        # 真彩背景
    clear = f"{ESC}[2J{ESC}[H"               # 清屏 + 光标归位
    top_pad = "\n" * max(rows // 2, 0)
    line = label.center(cols)
    return fill + clear + top_pad + f"{ESC}[1;97m{line}{ESC}[0m" + fill


def fetch_state(host, port, timeout=1.0):
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    conn.request("GET", "/state")
    data = conn.getresponse().read().decode("utf-8").strip()
    conn.close()
    return data


def main(argv=None):
    host = "127.0.0.1"
    port = int(os.environ.get("WISP_PORT", DEFAULT_PORT))
    poll = float(os.environ.get("WISP_POLL", "0.25"))
    sys.stdout.write(f"{ESC}[?25l")  # 隐藏光标
    sys.stdout.flush()
    try:
        while True:
            try:
                state, connected = fetch_state(host, port), True
            except Exception:
                state, connected = None, False
            cols, rows = shutil.get_terminal_size((80, 24))
            sys.stdout.write(render(state, cols, rows, connected))
            sys.stdout.flush()
            time.sleep(poll)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(f"{ESC}[0m{ESC}[2J{ESC}[H{ESC}[?25h")  # 复位 + 显示光标
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
