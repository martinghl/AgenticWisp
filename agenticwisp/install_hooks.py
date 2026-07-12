"""把 AgenticWisp 的 Claude Code 钩子合并进 ~/.claude/settings.json。

用法:python -m agenticwisp.install_hooks /abs/path/to/bin/wisp
幂等(重复运行不会重复添加),并对已有 settings 自动备份。
"""
import json
import os
import shutil
import sys

# (事件, matcher);matcher 只给工具类事件用
EVENTS = [
    ("UserPromptSubmit", None),
    ("PreToolUse", "*"),
    ("PostToolUse", "*"),
    ("PostToolUseFailure", "*"),
    ("PermissionRequest", None),
    ("Notification", None),
    ("Stop", None),
    ("StopFailure", None),
    ("SubagentStart", None),
    ("SubagentStop", None),
]


def build_hooks(wisp_bin):
    """返回把 10 个事件都接到 `<wisp_bin> signal <Event>` 的 hooks 映射。"""
    hooks = {}
    for event, matcher in EVENTS:
        entry = {"hooks": [{"type": "command",
                            "command": "%s signal %s" % (wisp_bin, event),
                            "timeout": 5}]}
        if matcher is not None:
            entry = {"matcher": matcher, **entry}
        hooks[event] = [entry]
    return hooks


def _commands(group):
    return {h.get("command") for h in group.get("hooks", [])}


def merge_into_settings(wisp_bin, settings_path=None):
    """幂等地把钩子合并进 settings 文件。返回 (新增事件列表, 备份路径|None, 实际路径)。"""
    settings_path = settings_path or os.path.expanduser("~/.claude/settings.json")
    parent = os.path.dirname(settings_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    data = {}
    backup = None
    if os.path.exists(settings_path):
        backup = settings_path + ".bak-agenticwisp"
        shutil.copy(settings_path, backup)
        try:
            with open(settings_path) as f:
                data = json.load(f)
        except ValueError:
            data = {}
    if not isinstance(data, dict):
        data = {}
    ours = build_hooks(wisp_bin)
    hooks = data.setdefault("hooks", {})
    added = []
    for event, groups in ours.items():
        dest = hooks.setdefault(event, [])
        existing = set()
        for g in dest:
            existing |= _commands(g)
        for g in groups:
            if not (_commands(g) & existing):
                dest.append(g)
                added.append(event)
    tmp = settings_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, settings_path)
    return added, backup, settings_path


def _is_ours(command, event):
    """True iff `command` is one of ours: a wisp launcher invoked as `... <wisp> signal <event>`
    (tolerates an env-var prefix, e.g. `WISP_PYTHON=... /path/bin/wisp signal <event>`)."""
    if not command:
        return False
    parts = command.split()
    if parts[-2:] != ["signal", event]:
        return False
    return any(os.path.basename(p) == "wisp" for p in parts[:-2])


def remove_from_settings(settings_path=None):
    """Idempotently strip our hook groups. Returns (removed_events, backup|None, path)."""
    settings_path = settings_path or os.path.expanduser("~/.claude/settings.json")
    if not os.path.exists(settings_path):
        return [], None, settings_path
    backup = settings_path + ".bak-agenticwisp"
    shutil.copy(settings_path, backup)
    try:
        with open(settings_path) as f:
            data = json.load(f)
    except ValueError:
        return [], backup, settings_path
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        return [], backup, settings_path
    hooks = data["hooks"]
    removed = []
    for event, _matcher in EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for g in groups:
            if not isinstance(g, dict) or not isinstance(g.get("hooks"), list):
                kept_groups.append(g)
                continue
            entries = g["hooks"]
            kept_entries = [h for h in entries if not _is_ours(h.get("command"), event)]
            if len(kept_entries) != len(entries):
                removed.append(event)
            if not kept_entries:
                continue  # the whole group was ours -> drop it
            g["hooks"] = kept_entries
            kept_groups.append(g)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            hooks.pop(event, None)
    tmp = settings_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, settings_path)
    return removed, backup, settings_path


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    wisp_bin = argv[0] if argv else "wisp"
    added, backup, path = merge_into_settings(wisp_bin)
    print("Merged AgenticWisp hooks into %s" % path)
    if backup:
        print("  backup saved to %s" % backup)
    print("  events wired: %s" % (", ".join(added) if added else "(already installed)"))
    print("Restart your Claude Code session to activate the hooks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
