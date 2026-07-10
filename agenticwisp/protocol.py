"""AgenticWisp 状态协议:唯一的状态定义与显示配置,所有组件共用。"""

IDLE = "idle"
THINKING = "thinking"
TOOL = "tool"
WAITING = "waiting"
ERROR = "error"

STATES = (IDLE, THINKING, TOOL, WAITING, ERROR)

# Claude Code 钩子事件 → 内部状态
HOOK_EVENT_TO_STATE = {
    "Stop": IDLE,
    "UserPromptSubmit": THINKING,
    "PostToolUse": THINKING,
    "PreToolUse": TOOL,
    "PermissionRequest": WAITING,
    "Notification": WAITING,
    "PostToolUseFailure": ERROR,
    "StopFailure": ERROR,
}

# 每个状态的显示配置。label 显示文字 / rgb 终端真彩 / web 网页色 / blink 保留字段
DISPLAY = {
    IDLE:     {"label": "IDLE · 空闲",     "rgb": (34, 160, 74),   "web": "#22a04a", "blink": False},
    THINKING: {"label": "THINKING · 思考", "rgb": (210, 170, 30),  "web": "#d2aa1e", "blink": True},
    TOOL:     {"label": "TOOL · 调工具",   "rgb": (139, 92, 246),  "web": "#8b5cf6", "blink": True},
    WAITING:  {"label": "WAITING · 等你",  "rgb": (34, 184, 207),  "web": "#22b8cf", "blink": True},
    ERROR:    {"label": "ERROR · 出错",    "rgb": (229, 72, 77),   "web": "#e5484d", "blink": True},
}

# 聚合优先级:多个 session 状态取"最该看"的(高→低)
PRIORITY = {IDLE: 0, THINKING: 1, TOOL: 2, ERROR: 3, WAITING: 4}


def normalize(value):
    """把状态名或钩子事件名规约为合法内部状态;非法返回 None。"""
    if not isinstance(value, str):
        return None
    v = value.strip()
    if v in STATES:
        return v
    return HOOK_EVENT_TO_STATE.get(v)


def is_valid(value):
    """value 是否是一个合法的内部状态。"""
    return value in STATES


def aggregate(states):
    """多个状态取优先级最高的;空或全非法 → idle。"""
    valid = [s for s in states if s in PRIORITY]
    if not valid:
        return IDLE
    return max(valid, key=PRIORITY.get)
