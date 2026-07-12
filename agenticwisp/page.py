"""AgenticWisp 浏览器灯:多 session 卡片 + 聚合 canvas 呼吸灯 + 点击专注。"""
import json

from agenticwisp import protocol
from agenticwisp import i18n

# 注意:CFG 仅注入 protocol.DISPLAY 的静态配置,不含用户/请求数据。session 名/cwd 在
# JS 端用 textContent 写入(不拼进 HTML),故无 </script> 注入风险。
_TEMPLATE = """<!doctype html>
<html lang="__LANG__"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgenticWisp</title>
<style>
  :root{color-scheme:dark}
  html,body{margin:0;height:100%;background:#111;color:#eee;
    font-family:system-ui,-apple-system,sans-serif;overflow:hidden}
  #wrap{height:100vh;display:flex;flex-direction:column}
  #lampwrap{position:relative;height:40vh;min-height:160px}
  #lamp{width:100%;height:100%;display:block}
  #label{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    font-size:4vw;font-weight:800;letter-spacing:.05em;text-shadow:0 2px 16px rgba(0,0,0,.5)}
  #grid{flex:1;overflow:auto;display:grid;gap:12px;padding:16px;
    grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
  .card{border-radius:12px;padding:14px 16px;background:#1c1c1c;border-left:8px solid #333;
    cursor:pointer;transition:transform .1s,box-shadow .2s}
  .card:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.4)}
  .card.focus{outline:2px solid #fff}
  .name{font-weight:700;font-size:1.05em;margin-bottom:4px}
  .cwd{font-size:.8em;color:#999;word-break:break-all;margin-bottom:6px}
  .st{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.8em;color:#111;font-weight:700}
  #hint{position:absolute;top:8px;right:12px;font-size:.75em;color:#bbb}
</style></head>
<body><div id="wrap">
  <div id="lampwrap"><canvas id="lamp"></canvas><div id="label">…</div>
    <div id="hint">__HINT__</div></div>
  <div id="grid"></div>
</div>
<script>
const CFG = __CFG__;
const cvs = document.getElementById('lamp'), ctx = cvs.getContext('2d');
const label = document.getElementById('label'), grid = document.getElementById('grid');
let focusId = null, aggState = 'idle', connected = false, t0 = performance.now();
function hexToRgb(h){h=h.replace('#','');return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)];}
function resize(){cvs.width=cvs.clientWidth;cvs.height=cvs.clientHeight;}
window.addEventListener('resize',resize);resize();
function draw(){
  if(!connected){
    ctx.fillStyle = '#333';
    ctx.fillRect(0,0,cvs.width,cvs.height);
    label.textContent = '__WAITING__';
    requestAnimationFrame(draw);
    return;
  }
  const period = CFG.period[aggState] || 0.6;
  const t = (performance.now()-t0)/1000;
  const b = 0.55 + 0.45*Math.sin(2*Math.PI*(t%period)/period);
  const [r,g,bl] = hexToRgb(CFG.colors[aggState]||'#333');
  ctx.fillStyle = `rgb(${Math.round(r*b)},${Math.round(g*b)},${Math.round(bl*b)})`;
  ctx.fillRect(0,0,cvs.width,cvs.height);
  label.textContent = CFG.labels[aggState]||aggState;
  requestAnimationFrame(draw);
}
requestAnimationFrame(draw);
function card(s){
  const el=document.createElement('div');
  el.className='card'+(s.id===focusId?' focus':'');
  el.style.borderLeftColor=CFG.colors[s.state]||'#333';
  const nm=document.createElement('div');nm.className='name';nm.textContent=s.name||s.id||'';
  const cw=document.createElement('div');cw.className='cwd';cw.textContent=s.cwd||'';
  const st=document.createElement('span');st.className='st';
  st.style.background=CFG.colors[s.state]||'#333';
  st.textContent=(CFG.labels[s.state]||s.state)+(s.tool?(' · '+s.tool):'');
  el.appendChild(nm);el.appendChild(cw);el.appendChild(st);
  el.onclick=()=>{focusId=(focusId===s.id)?null:s.id;};
  return el;
}
async function tick(){
  try{
    const rs=await fetch('/sessions',{cache:'no-store'});
    let sessions=await rs.json();
    const ra=await fetch('/aggregate',{cache:'no-store'});
    aggState=(await ra.text()).trim()||'idle';
    grid.innerHTML='';
    const view=focusId?sessions.filter(s=>s.id===focusId):sessions;
    (view.length?view:sessions).forEach(s=>grid.appendChild(card(s)));
    if(focusId){const f=sessions.find(s=>s.id===focusId);if(f)aggState=f.state;}
    connected=true;
  }catch(e){connected=false;}
}
setInterval(tick, CFG.poll); tick();
</script></body></html>"""


def render_page(poll_ms=250):
    cfg = {
        "colors": {s: protocol.DISPLAY[s]["web"] for s in protocol.STATES},
        "labels": {s: i18n.state_label(s) for s in protocol.STATES},
        "period": {s: (4.0 if s == protocol.IDLE else 1.5 if s == protocol.THINKING else 0.6)
                   for s in protocol.STATES},
        "poll": poll_ms,
    }
    return (_TEMPLATE
            .replace("__CFG__", json.dumps(cfg, ensure_ascii=False))
            .replace("__LANG__", i18n.lang())
            .replace("__HINT__", i18n.t("page.hint"))
            .replace("__WAITING__", i18n.t("page.waiting")))
