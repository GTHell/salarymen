"""serve_web.py — the Devin surface: chat + live preview, stdlib only.

  GET  /                chat UI (inline HTML)
  POST /api/chat        {message} -> INBOX receipt + triggers intake+builder
  GET  /api/events?since=ts   event tail for polling
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .board import Board
from .events import EventLog
from .features import backfill

PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>salaryman — build chat</title>
<style>
:root{--bg:#0b0d12;--panel:#151926;--line:#262d40;--txt:#e8ecf4;--dim:#8b93a8;--cy:#4dd6ff;--gr:#3ddc97}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--txt);font:14px/1.5 ui-monospace,Menlo,monospace;height:100vh;display:flex;flex-direction:column}
header{padding:12px 20px;border-bottom:1px solid var(--line);display:flex;gap:10px;align-items:center}
header b{letter-spacing:1px}.live{width:8px;height:8px;border-radius:50%;background:var(--gr);animation:p 2s infinite}
@keyframes p{50%{opacity:.3}}
#wrap{flex:1;display:flex;min-height:0}
#chat{flex:1.2;display:flex;flex-direction:column;border-right:1px solid var(--line);min-width:0}
#log{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px}
.msg{max-width:85%;padding:10px 14px;border-radius:12px;white-space:pre-wrap;word-break:break-word}
.msg.user{align-self:flex-end;background:#1c3a5e}
.msg.sys{align-self:flex-start;background:var(--panel);border:1px solid var(--line)}
.msg .t{color:var(--dim);font-size:11px;margin-top:4px}
.msg img{max-width:100%;border-radius:8px;margin-top:6px;border:1px solid var(--line)}
#bar{display:flex;gap:8px;padding:12px;border-top:1px solid var(--line)}
#inp{flex:1;background:var(--panel);border:1px solid var(--line);color:var(--txt);border-radius:8px;padding:10px;font:inherit;outline:none}
button{background:var(--cy);color:#00121a;border:0;border-radius:8px;padding:10px 18px;font-weight:700;cursor:pointer}
#right{flex:1;display:flex;flex-direction:column;min-width:0}
#rtabs{display:flex;gap:6px;padding:10px;border-bottom:1px solid var(--line)}
.rt{background:var(--panel);border:1px solid var(--line);color:var(--dim);border-radius:7px;padding:6px 14px;cursor:pointer;font:inherit}
.rt.on{color:var(--cy);border-color:var(--cy)}
#iframe{flex:1;border:0;background:#fff;width:100%}
@media(max-width:900px){#wrap{flex-direction:column}#chat{border-right:0;border-bottom:1px solid var(--line)}}
</style></head>
<body>
<header><span class="live"></span><b>SALARYMAN</b><span style="color:var(--dim)">chat → build → verify</span>
<span id="boardstrip" style="margin-left:auto;color:var(--dim)"></span></header>
<div id="wrap">
 <div id="chat"><div id="log"></div>
  <div id="bar"><input id="inp" placeholder="tell salaryman what to build…" autofocus>
  <button onclick="send()">BUILD</button></div></div>
 <div id="right"><div id="rtabs">
   <button class="rt on" onclick="tab(this,'preview')">PREVIEW</button>
   <button class="rt" onclick="tab(this,'shots')">EVIDENCE</button></div>
  <iframe id="iframe" src="__PREVIEW_URL__"></iframe>
  <div id="shots" style="display:none;overflow-y:auto;padding:10px"></div>
 </div>
</div>
<script>
let lastTs = __LAST_TS__, seen = new Set();
const log = document.getElementById('log');
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
function add(cls, text, img){const d=document.createElement('div');d.className='msg '+cls;
 d.innerHTML=esc(text)+(img?'<img src="'+img+'">':'');log.appendChild(d);log.scrollTop=log.scrollHeight;}
function tab(b,id){document.querySelectorAll('.rt').forEach(x=>x.classList.remove('on'));b.classList.add('on');
 document.getElementById('iframe').style.display=id==='preview'?'':'none';
 document.getElementById('shots').style.display=id==='shots'?'':'none';}
async function send(){const i=document.getElementById('inp');const v=i.value.trim();if(!v)return;
 add('user',v);i.value='';
 await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:v})});}
const ICON={'build.passed':'✅','build.failed':'❌','card.created':'📝','intake.done':'📥','evidence.attached':'📸','deploy.done':'🚀'};
async function poll(){
 try{
  const evs=await fetch('/api/events?since='+lastTs).then(r=>r.json());
  for(const e of evs.events){
   const k=e.ts+'|'+e.type+'|'+(e.card_id||'');
   if(seen.has(k))continue;seen.add(k);
   let t=ICON[e.type]||'•';
   if(e.type==='intake.done'){t+=' intake: '+e.cards.length+' cards';for(const c of e.cards.slice(0,5))t+='\\n • '+c.id+' ('+c.size+') '+c.title;}
   else if(e.type==='card.moved')t+=' '+e.card_id+' → '+e.to;
   else if(e.type==='build.passed')t+=' '+e.card_id+' DONE ('+Math.round(e.duration_s||0)+'s)';
   else if(e.type==='build.failed')t+=' '+e.card_id+' failed';
   else if(e.type==='evidence.attached')t+=' '+e.card_id;
   if(e.screenshot)add('sys',t,e.screenshot);else add('sys',t);
   lastTs=Math.max(lastTs,e.ts);
  }
 }catch(e){}
 try{
  const s=await fetch('/api/board').then(r=>r.json());
  document.getElementById('boardstrip').textContent='BOARD  ✅'+s.done+'  🔨'+s.doing+'  📋'+s.todo;
 }catch(e){}
}
poll();setInterval(poll,2500);
document.getElementById('inp').addEventListener('keydown',e=>{if(e.key==='Enter')send()});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    project_dir: Path = Path(".")
    preview_url: str = "http://localhost:3457"

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path, _, qs = self.path.partition("?")
        params = dict(p.split("=", 1) for p in qs.split("&") if "=" in p)
        events = EventLog(self.project_dir / ".state" / "events.jsonl")
        if path == "/":
            html = PAGE.replace("__LAST_TS__", str(time.time() - 3600)) \
                       .replace("__PREVIEW_URL__", self.preview_url)
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/events":
            since = float(params.get("since", 0))
            self._json({"events": [e for e in events.tail(200) if e["ts"] > since]})
            return
        if path == "/api/board":
            b = Board(self.project_dir / "BOARD.md").load()
            self._json({"todo": len(b.cards["TODO"]),
                        "doing": len(b.cards["DOING"]),
                        "done": len(b.cards["DONE"])})
            return
        if path.startswith("/evidence/"):
            f = self.project_dir / path.lstrip("/")
            if f.is_file():
                body = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n) or b"{}")
        text = (payload.get("message") or "").strip()
        if not text:
            self._json({"error": "empty"}, 400)
            return
        board_path = self.project_dir / "BOARD.md"
        b = Board(board_path).load()
        cid = f"p{len(b.cards['INBOX']) + 1:03d}"
        b.add_inbox(cid, text)
        b.save()
        EventLog(self.project_dir / ".state" / "events.jsonl").emit(
            "card.created", card_id=cid, source="web", raw=text[:200])
        # trigger lanes detached so HTTP returns instantly
        runner = Path(__file__).parent.parent / "scripts" / "run_lanes.sh"
        subprocess.Popen(["bash", str(runner), str(self.project_dir)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        self._json({"ok": True, "inbox_id": cid})


def serve_web(project_dir: str | Path, port: int = 3460,
              preview_url: str = "http://localhost:3457") -> None:
    Handler.project_dir = Path(project_dir)
    Handler.preview_url = preview_url
    print(f"salaryman web chat on :{port} (preview: {preview_url})")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
