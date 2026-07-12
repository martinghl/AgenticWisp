<p align="center">
  <img src="docs/media/logo.png" width="640" alt="AgenticWisp">
</p>

<p align="center">
  <b>给 Claude Code 的一盏状态灯 + 一行状态栏——装进一个赛博朋克终端面板里。</b>
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="platform" src="https://img.shields.io/badge/platform-Linux%20%C2%B7%20macOS%20%C2%B7%20WSL-informational">
  <img alt="core deps" src="https://img.shields.io/badge/core-stdlib%20only-brightgreen">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
</p>

<p align="center"><a href="README.md">English</a> · <b>简体中文</b> · <a href="README.zh-TW.md">繁體中文</a></p>

<p align="center">
  <img src="docs/media/demo.gif" width="860" alt="wisp watch 终端面板">
</p>

Claude Code 自己也会告诉你它在干嘛——可你没法一眼看全，更没法同时盯住好几个会话。AgenticWisp 从它的钩子里读实时状态，做成一盏**灯**：颜色就是状态（思考 · 调工具 · 等你 · 干完 · 出错），灯底下还铺着一整行**状态栏**——模型、上下文窗口、token、实时花费，一个会话一行。

而且这灯是真好看。整块面板是个霓虹 TUI——一个会用大字拼出当前状态的等离子 “reactor”、一场片假名数据雨、每个会话各自跳的心跳——毕竟一个你整天开着的东西，顺手做得像是从一个更酷的未来穿越来的，也不亏。

它很小——纯标准库内核 + 一个很小的中枢——一条命令就起。

## 轮到你的时候，你不会错过

真正需要你出手的那种状态——它问你话、要你批权限、等你过一版计划——会把整个面板染红，大大写上 **PENDING**。

<p align="center">
  <img src="docs/media/demo_pending.png" width="860" alt="Claude 在等你时的面板">
</p>

## 你能得到什么

- **一盏状态灯**——一种状态一个颜色，所有会话扫一眼，就知道有没有哪个在等你。
- **一行状态栏**——每个会话（以及每个子 agent）的模型、reasoning effort、上下文用量条、token，还有实时花费估算。
- **一套赛博朋克 TUI**——reactor 主体、等离子、数据雨、逐会话心跳、红色 PENDING 警报。网络再卡也调得顺滑不掉帧。
- **三种看法**——完整的 `textual` 面板、一个自带的浏览器页、还有一个零依赖的简版灯。
- **几乎没有存在感**——中枢、钩子、浏览器灯全是纯 Python 标准库，只有花哨面板才要 `textual`；不往外发一个字节，中枢只绑 `127.0.0.1`。
- **绝不碍事**——钩子客户端 0.3 秒超时、吞掉一切异常、永远返回 0。灯可以坏，你的 Claude 会话绝不会。

## 这是给谁做的

任何在跑 Claude Code、又想知道它在忙啥、还不愿一直盯着的人——一个会话也好，十个也好。尤其是，如果你还希望自己的终端配得上这份酷。

## 上手

> **平台：** Linux、macOS，或 Windows 走 **WSL**。启动脚本是 bash、默认按 Unix shell 来，所以**原生 Windows（cmd / PowerShell）用不了**——请在 WSL 里跑。

```bash
pipx install "agenticwisp[tui]"          # 从 PyPI 装(花面板需要 [tui] 这个 extra)
# 或者从源码装,不需要 PyPI 账号:
#   pipx install "git+https://github.com/martinghl/AgenticWisp.git"

wisp demo            # 立刻看效果——自带的动画演示,不用连 Claude
```

再接到 Claude Code:

```bash
wisp up              # 起中枢(自己转后台;只绑 127.0.0.1)
wisp install-hooks   # 把钩子合并进 ~/.claude/settings.json(会留备份),然后重启 Claude Code
wisp watch           # 打开面板(加 --simple 用纯 stdlib 的简版)
```

想用源码目录跑?`git clone https://github.com/martinghl/AgenticWisp.git && cd AgenticWisp && bin/wisp demo` 也行。

## 接到 Claude Code 上

```bash
bin/wisp install-hooks    # 自动填好路径，合并进 ~/.claude/settings.json（会留备份）
# 然后重启你的 Claude Code 会话
```

想手动接也行：把 [`hooks/settings-snippet.json`](hooks/settings-snippet.json) 里的 `hooks` 块拷进 `~/.claude/settings.json`，把里面的路径换成你自己 clone 的路径就成。不管哪种，接上之后灯就自己跟着走了：你敲字 → 🟡，它调工具 → 🟣，它需要你 → 🔴 **PENDING**，它干完了 → 🟢。

## 它是怎么转的

```
  Claude Code 钩子
    └─ wisp signal <事件> ─▶  wispd（中枢）─┐
       从钩子的 stdin 里读       127.0.0.1:9099  │  各显示端来订阅：
       会话 / 工具               + Claude 自己的  ├─ 终端面板   (bin/wisp watch)
                                会话花名册        └─ 浏览器页   (中枢的 GET /)
```

- **`wisp signal`**——钩子客户端。把事件 POST 给中枢就退出。0.3 秒超时、吞掉异常、永远返回 0。
- **`wispd`**——中枢。按会话（连子 agent 一起）记状态，跟 Claude 自己的会话花名册对上名字和工作目录，再从每份 transcript 里读模型、上下文、token 和花费。只绑 `127.0.0.1`。
- **各显示端**都轮询中枢。面板刷你运行它的那个终端；浏览器页由中枢在 `GET /` 直接吐出来。

## 面板

| 键 | 作用 |
|-----|--------|
| `1`–`9` | 盯住第 N 个会话（reactor 只跟它） |
| `0` / `Esc` | 回到总览 |
| `q` | 退出 |

从上到下三块：大大的 **reactor**（所有会话的汇总状态）；**会话表**（一个会话一行，子 agent 缩进在底下，每行是 模型 · 状态 · effort · 上下文条 · 心跳 · 已持续多久 · token）；还有 **用量行**（总花费、token 拆分、每个模型一条）。

## 浏览器灯

```bash
open http://localhost:9099
# 中枢在另一台机器上,就先转发端口:
#   ssh -L 9099:localhost:9099 <主机>
```

多会话卡片加一盏呼吸灯，扔第二块屏上挺顺手。

## 配置

| 变量 | 默认 | 含义 |
|----------|---------|---------|
| `WISP_PORT` | `9099` | 中枢端口（永远绑在 `127.0.0.1`） |
| `WISP_PYTHON` | `python3` | 中枢/钩子用的解释器，也是 `watch` 的首选 |
| `WISP_PLAIN` | 不设 | 设 `1` 就用纯色块，不跑等离子特效 |
| `WISP_POLL` | `0.25` | `--simple` 简版灯的轮询间隔（秒） |
| `WISP_LANG` | `en` | `en` 或 `zh`——所有界面的语言（面板、浏览器、命令行） |

## 状态 → 颜色

| 状态 | 颜色 | 什么时候 |
|-------|-------|------|
| 空闲 idle | 🟢 `#22a04a` | 干完了 / 在等你下一句 |
| 思考 thinking | 🟡 `#d2aa1e` | 两次工具调用之间在推理 |
| 调工具 tool | 🟣 `#8b5cf6` | 正在跑一个工具 |
| 等你 waiting | 🔵 `#22b8cf` | 需要你出手——在 reactor 里画成红色 **PENDING** |
| 出错 error | 🔴 `#e5484d` | 某个工具或某轮失败了 |

好几个会话同时开着时，灯显示优先级最高的那个：`等你 > 出错 > 调工具 > 思考 > 空闲`。

## 测试

```bash
python3 -m unittest discover -s tests           # 核心套件（纯标准库）
.venv/bin/python -m unittest discover -s tests   # 装了 textual 就连面板测试一起跑
```

## 往后

- 桌上摆一个真的 Arduino 红绿灯，走 USB 驱动（`GET /aggregate` 要的东西早就备好了）。
- 按工具分色、更丰富的浏览器动画。

## 卸载

```bash
wisp uninstall-hooks     # 从 ~/.claude/settings.json 删掉 AgenticWisp 的钩子(留备份)
pipx uninstall agenticwisp
```

## 许可证

[MIT](LICENSE)。

<sub>两个博士生做的——起因是老是搞不清自己的 Claude 到底在忙啥，索性让那个「告诉你答案」的东西也顺便好看点。</sub>
