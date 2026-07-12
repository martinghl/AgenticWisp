<p align="center">
  <img src="docs/media/logo.png" width="640" alt="AgenticWisp">
</p>

<p align="center">
  <b>給 Claude Code 的一盞狀態燈 + 一行狀態列——裝進一個賽博龐克終端面板裡。</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/agenticwisp/"><img alt="PyPI" src="https://img.shields.io/pypi/v/agenticwisp?color=blueviolet"></a>
  <img alt="python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="platform" src="https://img.shields.io/badge/platform-Linux%20%C2%B7%20macOS%20%C2%B7%20WSL-informational">
  <img alt="core deps" src="https://img.shields.io/badge/core-stdlib%20only-brightgreen">
  <img alt="license" src="https://img.shields.io/badge/license-MIT-black">
</p>

<p align="center"><a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <b>繁體中文</b></p>

<p align="center">
  <img src="docs/media/demo.gif" width="860" alt="wisp watch 終端面板">
</p>

Claude Code 自己也會告訴你它在幹嘛——可你沒法一眼看全，更沒法同時盯住好幾個工作階段。AgenticWisp 從它的鉤子裡讀即時狀態，做成一盞**燈**：顏色就是狀態（思考 · 調工具 · 等你 · 幹完 · 出錯），燈底下還鋪著一整行**狀態列**——模型、上下文視窗、token、即時花費，一個工作階段一行。

而且這燈是真好看。整塊面板是個霓虹 TUI——一個會用大字拼出當前狀態的電漿 “reactor”、一場片假名資料雨、每個工作階段各自跳的心跳——畢竟一個你整天開著的東西，順手做得像是從一個更酷的未來穿越來的，也不虧。

它很小——純標準函式庫核心 + 一個很小的中樞——一條指令就起。

## 輪到你的時候，你不會錯過

真正需要你出手的那種狀態——它問你話、要你批權限、等你過一版計畫——會把整個面板染紅，大大寫上 **PENDING**。

<p align="center">
  <img src="docs/media/demo_pending.png" width="860" alt="Claude 在等你時的面板">
</p>

## 你能得到什麼

- **一盞狀態燈**——一種狀態一個顏色，所有工作階段掃一眼，就知道有沒有哪個在等你。
- **一行狀態列**——每個工作階段（以及每個子 agent）的模型、reasoning effort、上下文用量條、token，還有即時花費估算。
- **一套賽博龐克 TUI**——reactor 主體、電漿、資料雨、逐工作階段心跳、紅色 PENDING 警報。網路再卡也調得順滑不掉幀。
- **三種看法**——完整的 `textual` 面板、一個自帶的瀏覽器頁，還有一個零相依的簡版燈。
- **幾乎沒有存在感**——中樞、鉤子、瀏覽器燈全是純 Python 標準函式庫，只有花俏面板才要 `textual`；不往外送一個位元組，中樞只綁 `127.0.0.1`。
- **絕不礙事**——鉤子客戶端 0.3 秒逾時、吞掉一切例外、永遠回傳 0。燈可以壞，你的 Claude 工作階段絕不會。

## 這是給誰做的

任何在跑 Claude Code、又想知道它在忙啥、還不願一直盯著的人——一個工作階段也好，十個也好。尤其是，如果你還希望自己的終端配得上這份酷。

## 上手

> **平台：** Linux 和 macOS 直接支援。Windows 需要透過 **WSL** —— 中樞的生命週期指令(`up` / `down` / `status`)依賴 POSIX 行程語意(`os.kill`、`SIGTERM`、`start_new_session`),所以**原生 Windows（cmd / PowerShell）暫不支援**——請在 WSL 裡跑。

```bash
# 安裝(擇一)——[tui] 這個 extra 會拉入 textual 供花俏面板用:
pipx install "agenticwisp[tui]"          # 用 pipx
uv tool install "agenticwisp[tui]"       # ...或用 uv
# 從原始碼裝,不需要 PyPI 帳號:
#   pipx install "git+https://github.com/martinghl/AgenticWisp.git"

wisp demo            # 立刻看效果——自帶的動畫演示,不用接 Claude
```

再接到 Claude Code:

```bash
wisp up              # 起中樞(自己轉背景;只綁 127.0.0.1)
wisp install-hooks   # 把鉤子合併進 ~/.claude/settings.json(會留備份),然後重啟 Claude Code
wisp watch           # 打開面板(加 --simple 用純標準函式庫的簡版)
```

想用原始碼目錄跑?`git clone https://github.com/martinghl/AgenticWisp.git && cd AgenticWisp && bin/wisp demo` 也行。

## 接到 Claude Code 上

```bash
bin/wisp install-hooks    # 自動填好路徑，合併進 ~/.claude/settings.json（會留備份）
# 然後重啟你的 Claude Code 工作階段
```

想手動接也行：把 [`hooks/settings-snippet.json`](hooks/settings-snippet.json) 裡的 `hooks` 區塊拷進 `~/.claude/settings.json`，把裡面的路徑換成你自己 clone 的路徑就成。不管哪種，接上之後燈就自己跟著走了：你敲字 → 🟡，它調工具 → 🟣，它需要你 → 🔴 **PENDING**，它幹完了 → 🟢。

## 它是怎麼轉的

```
  Claude Code 鉤子
    └─ wisp signal <事件> ─▶  wispd（中樞）─┐
       從鉤子的 stdin 裡讀       127.0.0.1:9099  │  各顯示端來訂閱：
       階段 / 工具               + Claude 自己的  ├─ 終端面板   (bin/wisp watch)
                                階段名冊          └─ 瀏覽器頁   (中樞的 GET /)
```

- **`wisp signal`**——鉤子客戶端。把事件 POST 給中樞就退出。0.3 秒逾時、吞掉例外、永遠回傳 0。
- **`wispd`**——中樞。按工作階段（連子 agent 一起）記狀態，跟 Claude 自己的工作階段名冊對上名字和工作目錄，再從每份 transcript 裡讀模型、上下文、token 和花費。只綁 `127.0.0.1`。
- **各顯示端**都輪詢中樞。面板刷你執行它的那個終端；瀏覽器頁由中樞在 `GET /` 直接吐出來。

## 面板

| 鍵 | 作用 |
|-----|--------|
| `1`–`9` | 盯住第 N 個工作階段（reactor 只跟它） |
| `0` / `Esc` | 回到總覽 |
| `q` | 退出 |

從上到下三塊：大大的 **reactor**（所有工作階段的彙總狀態）；**工作階段表**（一個工作階段一行，子 agent 縮排在底下，每行是 模型 · 狀態 · effort · 上下文條 · 心跳 · 已持續多久 · token）；還有 **用量行**（總花費、token 拆分、每個模型一條）。

## 瀏覽器燈

```bash
open http://localhost:9099
# 中樞在另一台機器上，就先轉發連接埠：
#   ssh -L 9099:localhost:9099 <主機>
```

多工作階段卡片加一盞呼吸燈，扔第二塊螢幕上挺順手。

## 設定

| 變數 | 預設 | 含義 |
|----------|---------|---------|
| `WISP_PORT` | `9099` | 中樞連接埠（永遠綁在 `127.0.0.1`） |
| `WISP_PYTHON` | `python3` | 中樞/鉤子用的直譯器，也是 `watch` 的首選 |
| `WISP_PLAIN` | 不設 | 設 `1` 就用純色塊，不跑電漿特效 |
| `WISP_POLL` | `0.25` | `--simple` 簡版燈的輪詢間隔（秒） |
| `WISP_LANG` | `en` | `en` 或 `zh`——所有介面的語言（面板、瀏覽器、命令列） |

## 狀態 → 顏色

| 狀態 | 顏色 | 什麼時候 |
|-------|-------|------|
| 空閒 idle | 🟢 `#22a04a` | 幹完了 / 在等你下一句 |
| 思考 thinking | 🟡 `#d2aa1e` | 兩次工具呼叫之間在推理 |
| 調工具 tool | 🟣 `#8b5cf6` | 正在跑一個工具 |
| 等你 waiting | 🔵 `#22b8cf` | 需要你出手——在 reactor 裡畫成紅色 **PENDING** |
| 出錯 error | 🔴 `#e5484d` | 某個工具或某輪失敗了 |

好幾個工作階段同時開著時，燈顯示優先順序最高的那個：`等你 > 出錯 > 調工具 > 思考 > 空閒`。

## 測試

```bash
python3 -m unittest discover -s tests           # 核心套件（純標準函式庫）
.venv/bin/python -m unittest discover -s tests   # 裝了 textual 就連面板測試一起跑
```

## 往後

- 桌上擺一個真的 Arduino 紅綠燈，走 USB 驅動（`GET /aggregate` 要的東西早就備好了）。
- 按工具分色、更豐富的瀏覽器動畫。

## 解除安裝

```bash
wisp uninstall-hooks     # 從 ~/.claude/settings.json 移除 AgenticWisp 的鉤子(留備份)
pipx uninstall agenticwisp
```

## 授權

[MIT](LICENSE)。

<sub>兩個博士生做的——起因是老是搞不清自己的 Claude 到底在忙啥，索性讓那個「告訴你答案」的東西也順便好看點。</sub>
