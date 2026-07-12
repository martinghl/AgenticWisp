<h1 align="center">AgenticWisp 🔦</h1>

<p align="center">
  <b>远程 Claude Code 会话的信号灯 —— 不管你人在哪儿,都能看清你的 AI 在干什么。</b>
</p>

<p align="center">
  <img alt="python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="core deps" src="https://img.shields.io/badge/core-stdlib%20only-brightgreen">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
</p>

<p align="center">
  <a href="README.md">English</a> | <b>简体中文</b>
</p>

---

> 试着想象把 **Claude Traffic Light**——那个人人都爱的、一眼扫过去就知道红黄绿状态的经典点子——和 Claude Code 自带的 **status line**(模型 · 上下文 · token · 花费)揉到一起。红绿灯让你一眼看到状态;status line 给你每个会话的丰富细节。AgenticWisp 两个都要——服务对象是跑在**远程**机器上的 Claude,走的是你本来就开着的 SSH 隧道。

---

## 问题所在,以及解法

你的 Claude Code 会话八成不是跑在你眼前这台笔记本上的。它可能在走廊尽头的 GPU 服务器上、云端的开发实例里,或者 VPN 后面某台大家共用的研究服务器上——你通过 SSH 连过去,开着一个时不时切回去瞄一眼的终端标签页。它还在思考吗?在跑工具吗?还是安安静静地卡在五分钟前问你的那个权限确认上,等着你回应?盯着一个看起来毫无动静的终端窗口,你是真的看不出来。

AgenticWisp 把 Claude 的实时状态变成一盏灯。**红绿灯**这一侧是聚合的光——扫一眼就知道这台机器上所有会话里,眼下最忙的是什么状态。**status line** 这一侧是你凑近细看时得到的东西——每个会话的模型、推理强度、上下文窗口占用、token 数和累计花费,实时更新。Claude 的 hooks 把状态报给服务器上一个小小的 hub;信号再通过**你本来就开着的 SSH 隧道**传回给你——不用云服务,不开放端口,没有任何新增的信任风险。

## 这是给谁用的?

只要你的 Claude 跑在一台需要通过 SSH 或 VPN 才能连上的机器上,这就是给你用的:在共享 GPU 服务器上跑实验的研究生和研究员、用计算集群的 ML 从业者、在云端或远程开发机上写代码的工程师,或者单纯是那种启动了一个长时间自主运行的 agent 会话然后就得离开去干别的事的人。如果你曾经 alt-tab 切到一个看起来毫无动静的 SSH 窗口,心里犯嘀咕"它到底还在想,还是在等*我*?"——这个项目挠的就是这个痒处。

## 长什么样

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

这盏"灯"可以是那个电影感十足的终端面板(*Reactor Core*,反应堆核心),也可以是给副屏用的浏览器页面,或者——等公司 IT 部门批准了 USB 设备之后——变成桌上一个真实的 Arduino 交通灯。

## 特性

- **感知多会话** —— 看得到这台机器上所有存活的 Claude Code 会话,用它们的真实名字(来自 `/rename`)和工作目录标识,你再也不用去猜到底哪个窗口是哪个。
- **聚合灯,也能放大细看** —— 扫一眼就能看到所有会话里"最忙"的状态;需要细节时按个数字键就能聚焦到单个会话。
- **5 种状态,带动画,永远看得清** —— 色相始终对应状态,哪怕动画正播到一半你也能一眼认出来;变化的只是亮度和纹理。
- **为长途连接打造的赛博朋克霓虹风** —— 面板是黑底霓虹 HUD,专门针对跨洲际的 SSH 连接做了调校(低帧率、确定性帧渲染、强制 truecolor),所以它看起来是流畅的动画,而不是卡成 PPT。
- **子代理(subagent)追踪** —— 被派发出去的子代理会以自己的实时子行显示,各自带着状态和心跳,让你能实时看到任务委派的过程。
- **实时霓虹心跳** —— 每一行都按状态跳动,当那个会话的 token 用量猛增时跳动会更剧烈——忙碌的 agent 看上去就是*忙*的。
- **每行都有丰富的遥测数据** —— 模型、推理强度、上下文窗口占用表(填充过程中呈**青 → 琥珀 → 粉红**渐变)、当前状态持续时间,以及累计 token 数,精确到每个会话和每个子代理。这就是 status line 那一半的思路。
- **Usage HUD(用量仪表盘)** —— 所有会话累计花费的实时估算,按模型拆分,并对便宜的缓存读取做了降权处理,让这个数字更贴近你实际花掉的钱。
- **中英文随你选** —— 设一次 `WISP_LANG`,面板、浏览器页面、简易灯和 CLI 输出全部跟着切换。
- **三种显示端,不管你盯着哪块屏幕** —— 一个完整的 `textual` 终端面板、一个自包含的浏览器页面,以及一个零依赖的兜底灯。
- **绝不会拖累 Claude** —— hook 客户端有 0.3 秒超时,吞掉所有错误,并且始终以 0 退出。这盏灯可以坏,你的会话不会。
- **不用云服务,不开放端口** —— 一切都走你现有的 SSH 隧道;hub 只绑定 `127.0.0.1`。
- **核心只用标准库** —— hub、hooks 和浏览器灯除了 Python 标准库什么都不需要。只有那个花哨的终端面板需要 `textual`。

## 快速开始

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

> `bin/wisp watch` 会自动挑第一个装了 `textual` 的解释器(先看 `$WISP_PYTHON`,再试几个候选),省得你每次都敲一长串解释器路径。

## 接入 Claude Code

用**一条命令**把 Claude 的 hooks 接到这盏灯上——它会自动填好自己的绝对路径,并合并进你的 `~/.claude/settings.json`(会先备份,并且可以重复执行):

```bash
bin/wisp install-hooks
# then restart your Claude Code session to activate the hooks
```

想自己手动配置?把 [`hooks/settings-snippet.json`](hooks/settings-snippet.json) 里的 `hooks` 块复制到 `~/.claude/settings.json` 中,并把每条 hook 命令里的占位路径替换成你自己克隆的路径。

现在这盏灯就会自动跟着 Claude 走:你输入 → 🟡,它跑工具 → 🟣,它需要你批准 → 🔵,它完成了 → 🟢。

## 工作原理

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

- **`wisp signal`**(hook 客户端)把 `{session_id, state, tool, effort}` —— 如果事件来自子代理,还会带上 `agent_id`/`agent_type` —— 发给 hub,然后退出。模型和上下文窗口用量是 hub 另外从会话的 transcript 里读出来的。
- **`wispd`**(hub)维护每个会话的状态(以及每个子代理的状态),把它和 Claude Code 自己的实时会话注册表(`~/.claude/sessions/*.json`)关联起来获取真实名字和工作目录,并解析每个会话的 transcript 来统计 token 用量。它提供 `GET /sessions`、`GET /aggregate`(别名 `GET /state`)、`GET /usage`(按模型统计的 token 数 + 预估花费),以及 `GET /`(浏览器灯页面)。
- **显示端** 轮询 hub。终端灯*跑在服务器上*,直接画在你的 SSH 窗口里;浏览器灯是 hub 提供的一个页面,通过一行 `ssh -L` 端口转发就能访问。

## 使用终端面板

| 按键 | 动作 |
|-----|------|
| `1`–`9` | **聚焦**第 N 个会话(Reactor Core 只显示这一个) |
| `0` / `Esc` | 回到**聚合**总览 |
| `q` | 退出 |

面板是黑底霓虹 HUD,从上到下分三个区域:

- 一个硕大的动画 **Reactor Core**(反应堆核心)—— 洋红/青色/紫色的等离子场,叠着一层若隐若现的片假名**数据雨(data-rain)**、一条移动的**扫描线(scanline)**、偶尔出现的**故障效果(glitch)**、一个 `// STATE //` 风格的 HUD 标题,以及用**3 行半角块 ASCII 大字**拼出来的聚合(或聚焦)状态(如果面板太窄或太矮,会退化成一行小字标签);
- 一张**编号会话表** —— 每一行显示**模型**、**状态**、**推理强度**、**上下文窗口占用表**、霓虹心跳、**当前状态持续时间**和**累计 token 数**;一个会话正在运行的**子代理**会以 `↳` 前缀的子行形式显示在它下面,带着同样的遥测数据;
- 一个 **Usage HUD** —— 一个发光的累计花费总数、输入/输出/缓存 token 的拆分,以及按花费排名前几的模型各自的霓虹能量条。

专为跨洲际 SSH 调校:低帧率、逐格确定性更新、强制 truecolor、暗底亮字,即使在延迟很高的链路上也能看得清。

## 浏览器灯

hub 在 `/` 提供一个自包含的页面。在你本地机器上,通过 SSH 转发端口后打开它:

```bash
ssh -L 9099:localhost:9099 <your-server>
# then open http://localhost:9099 in your browser
```

多会话卡片、一个会呼吸的 canvas 灯,还有点击聚焦——很适合放在副屏上。

## 配置

| 变量 | 默认值 | 含义 |
|----------|---------|---------|
| `WISP_PORT` | `9099` | hub 端口(hub 始终只绑定 `127.0.0.1`) |
| `WISP_PYTHON` | `python3` | hub/hooks 使用的解释器;也是 `watch` 尝试的第一个候选 |
| `WISP_PLAIN` | unset | 设为 `1` 可换成纯色色块,而不是等离子特效 |
| `WISP_POLL` | `0.25` | `--simple` 灯的轮询间隔(秒) |
| `WISP_LANG` | `en` | `en` \| `zh` —— 设置所有界面的语言:终端面板、浏览器页面、简易灯和 CLI 输出 |

**帧率:** Reactor Core 和 Usage HUD 默认跑在 6 fps(专门为长距离 SSH 链路上的渲染做了调校)。编辑 `agenticwisp/tui/app.py` 里的 `set_interval(1 / 6, ...)` 调用——在网速快/本地连接下可以调高(`1 / 10`),想省 CPU 就调低(`1 / 3`)。

> **给慢速/远程链路的小提示:** 全屏动画终端在跨洲际 SSH 上开销不小。如果感觉卡,就调低帧率,或者用 `WISP_PLAIN=1`(或者 `wisp watch --simple`)。

## 状态 → 颜色

| 状态 | 颜色 | 何时出现 |
|-------|-------|------|
| `idle` | 🟢 green `#22a04a` | Claude 完成了 / 在等你下一条指令 |
| `thinking` | 🟡 yellow `#d2aa1e` | 在工具调用之间进行推理 |
| `tool` | 🟣 purple `#8b5cf6` | 正在运行工具 |
| `waiting` | 🔵 cyan `#22b8cf` | 需要你输入 / 做权限决定 |
| `error` | 🔴 red `#e5484d` | 某个工具或回合失败了 |

当多个会话同时存活时,聚合灯显示优先级最高的状态:
`waiting > error > tool > thinking > idle`。

## 测试

```bash
python3 -m unittest discover -s tests          # core suite (stdlib only)
# with textual installed, the terminal-panel tests run too:
.venv/bin/python -m unittest discover -s tests
```

## 路线图

- **实体灯** —— 一个真正通过 USB 驱动的 Arduino 交通灯模块,把红黄绿映射到你最关心的那个会话上(架构里已经专门为此暴露了 `GET /aggregate`)——目前还在等 IT 批准这个 USB 设备。
- 按工具区分颜色、自定义配色方案,以及更丰富的浏览器动画。

## 许可证

[MIT](LICENSE) —— 你想怎么用都行;如果能保留版权声明,我们会很感激。

---

<sub>AgenticWisp 是两个累得够呛的博士生给自己挠痒痒的产物——一个纯粹为了好玩而做的副业项目,源于太多次"等等,我的 Claude 是不是还在跑?"的瞬间,不是什么公司产品。请以这种心态享受它。</sub>
