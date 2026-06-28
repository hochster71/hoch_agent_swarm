from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from backend.swarm_device_mesh import scan_device_swarm, get_cached_or_scan, agent_chat

app = FastAPI(title="HOCH 10-Device Agent Swarm Prototype")

HTML = r'''
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HOCH 10-Device Agent Swarm Prototype</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#020204;--panel:#071018;--card:#0a1624;--text:#eef7ff;--muted:#94a8bd;--blue:#60a5fa;--green:#6ee7b7;--amber:#fbbf24;--red:#fb7185;--purple:#c084fc;--border:rgba(125,180,255,.28)}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,rgba(96,165,250,.18),transparent 30%),linear-gradient(135deg,#020204,#030812);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.shell{padding:22px}.header,.panel{border:1px solid var(--border);border-radius:22px;background:rgba(7,16,24,.9);padding:18px;margin-bottom:16px;box-shadow:0 0 34px rgba(96,165,250,.12)}
.header{display:flex;justify-content:space-between;align-items:center;gap:16px}h1{margin:0;font-size:28px}p{color:var(--muted)}
.grid{display:grid;grid-template-columns:1.35fr .8fr;gap:16px}.summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.metric{border:1px solid var(--border);border-radius:16px;background:rgba(255,255,255,.035);padding:12px}.metric b{font-size:26px;color:var(--green)}
.devices{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.card{border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg,#0a1624,#02060c);padding:13px}.card.live{border-color:var(--green)}.card.missing{border-color:var(--amber)}.card.service{border-color:var(--blue)}
.pill{display:inline-block;border:1px solid rgba(125,180,255,.28);border-radius:999px;padding:3px 7px;margin:3px;font-size:12px}.model{color:var(--green)}.agent{color:var(--purple)}
button{border:1px solid var(--green);background:rgba(110,231,183,.12);color:var(--green);border-radius:999px;padding:10px 14px;cursor:pointer}textarea,input,select{width:100%;margin:.35rem 0;border:1px solid var(--border);border-radius:12px;background:#020812;color:var(--text);padding:10px}
pre{white-space:pre-wrap;overflow:auto;max-height:420px;background:#010305;border:1px solid var(--border);border-radius:12px;padding:12px;color:#c7f9d4}
@media(max-width:1000px){.grid{grid-template-columns:1fr}.summary{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<div class="shell">
  <div class="header">
    <div><h1>HOCH 10-Device Agent Swarm Prototype</h1><p>All network/Wi-Fi devices visible. AI runtimes proof-backed. Agent prompt staging included.</p></div>
    <button onclick="rescan()">Rescan Full Swarm</button>
  </div>
  <div id="summary" class="summary"></div>
  <div class="grid">
    <section class="panel"><h2>10-Device Mesh</h2><p>Green = model runtime. Blue = service/device. Amber = expected/missing.</p><div id="devices" class="devices">Loading...</div></section>
    <section class="panel"><h2>Agent Intelligence Chat</h2>
      <select id="agent"><option>Mission Commander</option><option>Asset Scout</option><option>Model Router</option><option>QA Auditor</option><option>Cyber Commoner</option><option>ConMon Watcher</option><option>Footprint Sentinel</option><option>Self-Heal Engineer</option><option>Gap Analyst</option><option>Release Captain</option></select>
      <input id="target" value="swarm">
      <textarea id="prompt" rows="6" placeholder="Example: audit all model runtimes, name all Wi-Fi devices, gap analyze missing nodes, and stage QA self-heal agents."></textarea>
      <button onclick="sendPrompt()">Stage Agent Prompt</button>
      <pre id="console">Waiting...</pre>
    </section>
  </div>
</div>
<script>
async function api(u,o){const r=await fetch(u,o);if(!r.ok)throw new Error(u+" "+r.status);return r.json()}
function esc(x) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;"
  };
  return String(x ?? "").replace(/[&<>"']/g, c => map[c] || c);
}
function render(data){
 const s=data.summary||{}; summary.innerHTML=`<div class="metric">Devices<br><b>${esc(s.device_count)}</b></div><div class="metric">Model Runtimes<br><b>${esc(s.model_runtime_count)}</b></div><div class="metric">Models<br><b>${esc(s.model_count)}</b></div><div class="metric">Agents<br><b>${esc((s.agents_available||[]).length)}</b></div>`;
 devices.innerHTML=(data.devices||[]).map(d=>{const cls=d.runtime_count>0?"live":d.truth_state==="MISSING_FROM_SCAN"?"missing":"service";const models=(d.models||[]).slice(0,14).map(m=>`<span class="pill model">${esc(m)}</span>`).join("");const agents=(d.agents_available||[]).map(a=>`<span class="pill agent">${esc(a)}</span>`).join("");const rts=(d.runtimes||[]).map(r=>`<span class="pill model">${esc(r.runtime)}:${esc(r.port)} ${esc(r.truth_state)}</span>`).join("");return `<article class="card ${cls}"><h3>${esc(d.name||d.ip)}</h3><p>IP: ${esc(d.ip)}<br>MAC: ${esc(d.mac||"unknown")}<br>Type: ${esc(d.device_type)}<br>Truth: ${esc(d.truth_state)}<br>Ports: ${esc((d.open_ports||[]).join(", ")||"none")}<br>Source: ${esc(d.source)}</p>${rts}${models}${agents}</article>`}).join("");
 console.textContent=JSON.stringify({generated_at:data.generated_at,summary:data.summary,source:data.source},null,2)
}
async function load(){try{render(await api("/api/v1/swarm/devices?limit=10"))}catch(e){console.textContent=e.message}}
async function rescan(){console.textContent="Scanning...";render(await api("/api/v1/swarm/devices/rescan?limit=10",{method:"POST"}))}
async function sendPrompt(){const out=await api("/api/v1/swarm/agent-chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({agent:agent.value,target:target.value,prompt:prompt.value})});console.textContent=JSON.stringify(out,null,2)}
load()
</script>
</body>
</html>
'''

@app.get("/")
async def root():
    return HTMLResponse(HTML, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/prototype/device-swarm")
async def prototype():
    return HTMLResponse(HTML, headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"})

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "device-swarm-prototype"}

@app.get("/api/v1/swarm/devices")
async def devices(limit: int = 10):
    return get_cached_or_scan(limit=limit)

@app.post("/api/v1/swarm/devices/rescan")
async def rescan(limit: int = 10):
    return scan_device_swarm(limit=limit)

@app.post("/api/v1/swarm/agent-chat")
async def chat(payload: dict):
    return agent_chat(payload)
