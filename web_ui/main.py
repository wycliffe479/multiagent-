"""web_ui/main.py
FastAPI web UI for the Anvil 2026 demo.
Run with:  python web_ui/main.py
Then open: http://localhost:8000
"""

import sys
import os
import json
import asyncio
import time
from typing import Any

# Make root importable
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
import uvicorn

app = FastAPI(title="Anvil 2026 — Ops Alert Triage")

# ---------------------------------------------------------------------------
# HTML frontend (single-file, no build step needed)
# ---------------------------------------------------------------------------
HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Anvil 2026 — Ops Alert Triage</title>
<style>
  :root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--accent:#58a6ff;--green:#3fb950;--red:#f85149;--yellow:#d29922;--text:#c9d1d9;--muted:#8b949e}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;padding:2rem}
  h1{font-size:1.8rem;font-weight:700;color:#fff;margin-bottom:.25rem}
  .subtitle{color:var(--muted);margin-bottom:2rem;font-size:.95rem}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:1.5rem;margin-bottom:1.5rem}
  textarea{width:100%;background:#0d1117;border:1px solid var(--border);border-radius:8px;color:var(--text);padding:.75rem 1rem;font-family:monospace;font-size:.9rem;resize:vertical;outline:none;transition:border-color .2s}
  textarea:focus{border-color:var(--accent)}
  .btn{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:.65rem 1.6rem;font-size:1rem;font-weight:600;cursor:pointer;transition:opacity .2s}
  .btn:hover{opacity:.85}
  .btn:disabled{opacity:.45;cursor:not-allowed}
  .presets{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.75rem}
  .preset{background:transparent;border:1px solid var(--border);border-radius:6px;color:var(--muted);padding:.3rem .75rem;font-size:.8rem;cursor:pointer;transition:border-color .2s}
  .preset:hover{border-color:var(--accent);color:var(--accent)}
  .pipeline{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:1.5rem 0}
  @media(max-width:700px){.pipeline{grid-template-columns:repeat(2,1fr)}}
  .agent{background:var(--bg);border:2px solid var(--border);border-radius:10px;padding:1rem;text-align:center;transition:border-color .4s,box-shadow .4s}
  .agent .num{font-size:1.5rem;font-weight:700;color:var(--muted)}
  .agent .name{font-size:.85rem;color:var(--muted);margin-top:.2rem}
  .agent.active{border-color:var(--accent);box-shadow:0 0 16px rgba(88,166,255,.25)}
  .agent.done{border-color:var(--green);box-shadow:0 0 16px rgba(63,185,80,.15)}
  .agent.done .num,.agent.done .name{color:var(--green)}
  .logs{background:#0d1117;border:1px solid var(--border);border-radius:8px;padding:1rem;font-family:monospace;font-size:.82rem;max-height:340px;overflow-y:auto;line-height:1.6;white-space:pre-wrap}
  .logs .info{color:var(--text)}
  .logs .ok{color:var(--green)}
  .logs .warn{color:var(--yellow)}
  .logs .err{color:var(--red)}
  .result-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-top:1rem}
  .result-item label{display:block;font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:.3rem}
  .result-item .value{font-size:1rem;font-weight:600;color:#fff}
  .badge{display:inline-block;padding:.2rem .6rem;border-radius:20px;font-size:.78rem;font-weight:600}
  .badge.critical{background:rgba(248,81,73,.2);color:var(--red)}
  .badge.warning{background:rgba(210,153,34,.2);color:var(--yellow)}
  .badge.info{background:rgba(88,166,255,.2);color:var(--accent)}
  .badge.green{background:rgba(63,185,80,.2);color:var(--green)}
  #slackPreview{background:#1a1d21;border:1px solid var(--border);border-radius:8px;padding:1rem;font-family:monospace;font-size:.83rem;white-space:pre-wrap;color:var(--text);margin-top:1rem;display:none}
  .hidden{display:none}
</style>
</head>
<body>
<h1>⚡ Anvil 2026</h1>
<p class="subtitle">Multi-Agent Autonomous Ops Alert Triage Pipeline</p>

<div class="card">
  <div style="margin-bottom:.6rem;font-weight:600">Alert Input</div>
  <p style="color:var(--muted);font-size:.85rem;margin-bottom:.6rem">Paste a raw alert string or pick a preset:</p>
  <div class="presets">
    <button class="preset" onclick="setPreset('server-down')">🔴 Server Down</button>
    <button class="preset" onclick="setPreset('high-cpu')">🟡 High CPU</button>
    <button class="preset" onclick="setPreset('memory-leak')">🟡 Memory Leak</button>
    <button class="preset" onclick="setPreset('disk-full')">🟠 Disk Full</button>
    <button class="preset" onclick="setPreset('deploy-fail')">🔴 Deploy Failed</button>
  </div>
  <textarea id="alertInput" rows="3" placeholder="ALERT: server-7 is down at us-east-1 ..."></textarea>
  <div style="margin-top:.75rem;display:flex;gap:.75rem;align-items:center">
    <button class="btn" id="runBtn" onclick="runPipeline()">▶ Trigger Agents</button>
    <span id="elapsed" style="color:var(--muted);font-size:.85rem"></span>
  </div>
</div>

<div class="card">
  <div style="margin-bottom:1rem;font-weight:600">Agent Pipeline</div>
  <div class="pipeline">
    <div class="agent" id="a1"><div class="num">A1</div><div class="name">Alert Reader</div></div>
    <div class="agent" id="a2"><div class="num">A2</div><div class="name">Past Searcher</div></div>
    <div class="agent" id="a3"><div class="num">A3</div><div class="name">Decision Maker</div></div>
    <div class="agent" id="a4"><div class="num">A4</div><div class="name">Slack Notifier</div></div>
  </div>

  <div style="margin-bottom:.5rem;font-weight:600;font-size:.9rem">Live Logs</div>
  <div class="logs" id="logBox">Waiting for alert…</div>
</div>

<div class="card hidden" id="resultCard">
  <div style="font-weight:600;margin-bottom:.5rem">Pipeline Result</div>
  <div class="result-grid" id="resultGrid"></div>
  <div style="font-weight:600;margin:.75rem 0 .4rem;font-size:.9rem">Slack Message Preview</div>
  <div id="slackPreview"></div>
</div>

<script>
const PRESETS = {
  'server-down':  'ALERT: server-7 is down at us-east-1. Error: connection_refused. Severity: critical. Time: 2026-05-15T03:00:00Z',
  'high-cpu':     'ALERT: server-12 CPU at 98% in eu-west-1. Error: high_cpu. Severity: warning. Time: 2026-05-15T08:30:00Z',
  'memory-leak':  'ALERT: server-3 OOM killer triggered in us-west-2. Error: memory_leak. Severity: critical. Time: 2026-05-15T11:00:00Z',
  'disk-full':    'ALERT: server-9 disk at 99% in ap-south-1. Error: disk_full. Severity: warning. Time: 2026-05-15T14:15:00Z',
  'deploy-fail':  'ALERT: Deployment to server-15 failed in eu-central. Error: deployment_failed. Severity: critical. Time: 2026-05-15T16:45:00Z',
};

function setPreset(key){ document.getElementById('alertInput').value = PRESETS[key]; }

function log(msg, cls='info'){
  const box = document.getElementById('logBox');
  const line = document.createElement('div');
  line.className = cls;
  line.textContent = msg;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

function setAgent(id, state){
  const el = document.getElementById(id);
  el.className = 'agent ' + state;
}

function resetUI(){
  ['a1','a2','a3','a4'].forEach(id => document.getElementById(id).className='agent');
  document.getElementById('logBox').innerHTML = '';
  document.getElementById('resultCard').classList.add('hidden');
  document.getElementById('slackPreview').style.display='none';
  document.getElementById('elapsed').textContent='';
}

async function runPipeline(){
  const alert = document.getElementById('alertInput').value.trim();
  if(!alert){ alert('Please enter an alert string.'); return; }

  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  resetUI();

  const t0 = Date.now();
  const timer = setInterval(()=>{
    document.getElementById('elapsed').textContent = ((Date.now()-t0)/1000).toFixed(1)+'s';
  }, 100);

  log('Starting Anvil 2026 pipeline …');

  try {
    const resp = await fetch('/run', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({alert})
    });

    if(!resp.ok){ throw new Error('Server error: '+resp.status); }

    const data = await resp.json();

    // Animate agents
    for(const [id, delay] of [['a1',0],['a2',300],['a3',600],['a4',900]]){
      await new Promise(r=>setTimeout(r,delay));
      setAgent(id,'done');
    }

    // Logs
    if(data.logs && data.logs.length){
      data.logs.forEach(l => log(l, l.includes('✓') ? 'ok' : l.includes('WARNING') ? 'warn' : 'info'));
    }
    log('✓ Pipeline complete.', 'ok');

    // Result card
    const parsed   = data.parsed_alert  || {};
    const decision = data.decision      || {};
    const sevClass = parsed.severity === 'critical' ? 'critical' : parsed.severity === 'warning' ? 'warning' : 'info';

    document.getElementById('resultGrid').innerHTML = `
      <div class="result-item"><label>Server</label><div class="value">${parsed.server_name||'—'}</div></div>
      <div class="result-item"><label>Error Type</label><div class="value">${parsed.error_type||'—'}</div></div>
      <div class="result-item"><label>Severity</label><div class="value"><span class="badge ${sevClass}">${(parsed.severity||'—').toUpperCase()}</span></div></div>
      <div class="result-item"><label>Location</label><div class="value">${parsed.location||'—'}</div></div>
      <div class="result-item"><label>Recommended Fix</label><div class="value">${data.recommended_fix||'—'}</div></div>
      <div class="result-item"><label>Decision</label><div class="value"><span class="badge green">${decision.action||'—'}</span></div></div>
      <div class="result-item"><label>Auto-Execute</label><div class="value">${decision.auto_execute ? '✅ Yes' : '⚠️ Manual'}</div></div>
      <div class="result-item"><label>Confidence</label><div class="value">${((decision.confidence||0)*100).toFixed(0)}%</div></div>
      <div class="result-item"><label>Est. Recovery</label><div class="value">${decision.estimated_recovery_minutes||0} min</div></div>
      <div class="result-item"><label>Slack Status</label><div class="value">${data.slack_status||'—'}</div></div>
    `;

    if(data.slack_message){
      const sp = document.getElementById('slackPreview');
      sp.textContent = data.slack_message;
      sp.style.display='block';
    }

    document.getElementById('resultCard').classList.remove('hidden');

  } catch(err){
    log('ERROR: '+err.message, 'err');
    ['a1','a2','a3','a4'].forEach(id=>setAgent(id,''));
  } finally {
    clearInterval(timer);
    btn.disabled = false;
  }
}

// Pre-fill with default alert
document.getElementById('alertInput').value = PRESETS['server-down'];
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(HTML)


@app.post("/run")
async def run_pipeline(request: Request):
    body = await request.json()
    raw_alert: str = body.get("alert", "")

    if not raw_alert.strip():
        return JSONResponse({"error": "No alert provided"}, status_code=400)

    # Run in a thread-pool so we don't block the event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _invoke_pipeline, raw_alert)
    return JSONResponse(result)


def _invoke_pipeline(raw_alert: str) -> dict[str, Any]:
    """Synchronous pipeline invocation (runs in thread pool)."""
    import importlib.util

    def load_wf(rel):
        abs_path   = os.path.join(_ROOT, rel)
        # rel example: "group-a-agents/src/workflow/graph.py"
        if "group-a-agents" in abs_path:
            group_root = os.path.join(_ROOT, "group-a-agents")
        elif "group-b-agents" in abs_path:
            group_root = os.path.join(_ROOT, "group-b-agents")
        else:
            raise RuntimeError(f"Cannot determine group for: {abs_path}")

        src_dir = os.path.join(group_root, "src")

        # Ensure the correct group's `src/` is importable as top-level package `src`.
        old_sys_path = sys.path[:]
        try:
            # Remove other group's src dirs to prevent `src` collisions.
            other_a = os.path.join(_ROOT, "group-a-agents", "src")
            other_b = os.path.join(_ROOT, "group-b-agents", "src")
            sys.path[:] = [p for p in sys.path if p not in (other_a, other_b)]

            if _ROOT not in sys.path:
                sys.path.insert(0, _ROOT)
            if group_root not in sys.path:
                sys.path.insert(0, group_root)
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)

            module = __import__("src.workflow.graph", fromlist=["workflow"])
            return getattr(module, "workflow")
        finally:
            sys.path[:] = old_sys_path


    wf_a = load_wf("group-a-agents/src/workflow/graph.py")
    state_a = wf_a.invoke({
        "raw_alert":       raw_alert,
        "parsed_alert":    {},
        "past_incidents":  [],
        "recommended_fix": "",
        "reasoning":       "",
        "status":          "",
    })

    wf_b = load_wf("group-b-agents/src/workflow/graph.py")
    state_b = wf_b.invoke({
        "parsed_alert":    state_a.get("parsed_alert",    {}),
        "past_incidents":  state_a.get("past_incidents",  []),
        "recommended_fix": state_a.get("recommended_fix", "monitor"),
        "reasoning":       state_a.get("reasoning",       ""),
        "decision":        {},
        "slack_message":   "",
        "slack_status":    "",
        "status":          "",
    })

    return {**state_a, **state_b}


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Starting Anvil 2026 Web UI at http://localhost:8000")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, app_dir=os.path.dirname(__file__))
