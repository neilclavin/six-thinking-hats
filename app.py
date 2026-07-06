"""Local browser UI for the Six Thinking Hats council.

Run it:  python app.py   (or double-click run.command / run.bat)

It serves a page on http://127.0.0.1:5000 where you paste your OWN Anthropic
API key, type a problem (and/or point at a sources folder + URLs), pick the mode,
and watch the six hats stream in live. The key is used only for that run and is
never stored — it stays on your machine.

There is no backend/hosting: everyone who uses this runs it locally with their
own key. That's the tradeoff for not paying for other people's usage.
"""

from __future__ import annotations

import json
import queue
import threading
import webbrowser

import anthropic
from flask import Flask, Response, render_template_string, request

import corpus as corpusmod
import six_hats
import sources as src

app = Flask(__name__)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Six Thinking Hats</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         margin: 0; background: #0f1115; color: #e8e8ea; }
  header { padding: 20px 24px; border-bottom: 1px solid #262a33; }
  header h1 { margin: 0; font-size: 20px; }
  header p { margin: 4px 0 0; color: #9aa0aa; font-size: 13px; }
  .wrap { display: grid; grid-template-columns: 360px 1fr; gap: 0; min-height: calc(100vh - 74px); }
  form { padding: 20px 24px; border-right: 1px solid #262a33; }
  label { display: block; font-size: 12px; text-transform: uppercase; letter-spacing: .04em;
          color: #9aa0aa; margin: 16px 0 6px; }
  input, textarea, select { width: 100%; padding: 9px 11px; background: #1a1d24;
          border: 1px solid #333844; border-radius: 8px; color: #e8e8ea; font-size: 14px; }
  textarea { resize: vertical; min-height: 64px; font-family: inherit; }
  .row { display: flex; gap: 10px; }
  .row > div { flex: 1; }
  button { margin-top: 20px; width: 100%; padding: 12px; border: 0; border-radius: 8px;
           background: #4f7cff; color: white; font-size: 15px; font-weight: 600; cursor: pointer; }
  button:disabled { opacity: .5; cursor: default; }
  .hint { font-size: 12px; color: #757b86; margin-top: 6px; line-height: 1.4; }
  .hint a { color: #7aa2ff; }
  #out { padding: 20px 28px; overflow-y: auto; white-space: pre-wrap; word-break: break-word;
         font: 14px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace; }
  .banner { font-weight: 700; }
  .white  { color: #e8e8ea; } .red { color: #ff6b6b; } .black { color: #b7bdc9; }
  .yellow { color: #ffd24a; } .green { color: #4ade80; } .blue { color: #6ea8ff; }
  .err { color: #ff6b6b; font-weight: 600; }
  .idle { color: #757b86; }
</style>
</head>
<body>
<header>
  <h1>🎩 Six Thinking Hats — council</h1>
  <p>De Bono's method as six AI agents. Runs locally with your own Anthropic API key.</p>
</header>
<div class="wrap">
  <form id="f" onsubmit="return run(event)">
    <label>Your Anthropic API key</label>
    <input type="password" id="key" placeholder="sk-ant-..." autocomplete="off">
    <div class="hint">Used only for this run, never stored. No key yet?
      <a href="https://console.anthropic.com/settings/keys" target="_blank">Get one here</a>
      (needs a little billing credit).</div>

    <label>Problem / decision</label>
    <textarea id="problem" placeholder="e.g. Should we add a mid-tier plan and change our free tier?"></textarea>
    <div class="hint">Optional if you provide sources below — the Blue Hat will frame the question from them.</div>

    <div class="row">
      <div>
        <label>Mode</label>
        <select id="mode">
          <option value="exploration">Exploration (find ideas)</option>
          <option value="evaluation">Evaluation (decide)</option>
        </select>
      </div>
      <div>
        <label>Effort</label>
        <select id="effort">
          <option value="low">Low (cheap/fast)</option>
          <option value="medium" selected>Medium</option>
          <option value="high">High (deep)</option>
        </select>
      </div>
    </div>

    <label>Sources folder (optional)</label>
    <input type="text" id="sources" placeholder="demo">
    <div class="hint">Path to a folder of docs (PDF/DOCX/MD/TXT/HTML/CSV/images) on this computer.</div>

    <label>Source URLs (optional, one per line)</label>
    <textarea id="urls" placeholder="https://example.com/report"></textarea>

    <button id="go" type="submit">Run the council</button>
  </form>
  <div id="out"><span class="idle">Fill in the form and press Run. The hats will appear here, one at a time.</span></div>
</div>
<script>
let es = null;
function cls(line) {
  const m = line.match(/(White|Red|Black|Yellow|Green|Blue) Hat/);
  return m ? m[1].toLowerCase() : "";
}
function run(e) {
  e.preventDefault();
  const out = document.getElementById("out");
  const go = document.getElementById("go");
  out.textContent = "";
  go.disabled = true; go.textContent = "Running…";
  if (es) es.close();

  const p = new URLSearchParams({
    key: document.getElementById("key").value,
    problem: document.getElementById("problem").value,
    mode: document.getElementById("mode").value,
    effort: document.getElementById("effort").value,
    sources: document.getElementById("sources").value,
    urls: document.getElementById("urls").value,
  });
  es = new EventSource("/stream?" + p.toString());
  let atLineStart = true;
  es.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    if (d.done) { es.close(); go.disabled = false; go.textContent = "Run the council"; return; }
    if (d.error) {
      const s = document.createElement("span");
      s.className = "err"; s.textContent = "\\n⚠ " + d.error + "\\n";
      out.appendChild(s); es.close(); go.disabled = false; go.textContent = "Run the council"; return;
    }
    // Colorize whole banner lines; stream everything else plainly.
    const isBanner = d.t.includes("Hat —") || /[─]{5,}/.test(d.t);
    const s = document.createElement("span");
    if (isBanner) s.className = "banner " + cls(d.t);
    s.textContent = d.t;
    out.appendChild(s);
    out.scrollTop = out.scrollHeight;
  };
  es.onerror = () => { go.disabled = false; go.textContent = "Run the council"; if (es) es.close(); };
  return false;
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/stream")
def stream():
    key = (request.args.get("key") or "").strip()
    problem = (request.args.get("problem") or "").strip()
    mode = request.args.get("mode", "exploration")
    effort = request.args.get("effort", "medium")
    sources = (request.args.get("sources") or "").strip()
    urls = [u.strip() for u in (request.args.get("urls") or "").splitlines()
            if u.strip() and not u.strip().startswith("#")]

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj)}\n\n"

    def generate():
        # Validate inputs before doing any work. Every path ends with a "done"
        # event so the page always re-enables the Run button.
        err = None
        if not key:
            err = "Please paste your Anthropic API key."
        elif mode not in six_hats.SEQUENCES:
            err = f"Unknown mode: {mode}"
        elif not problem and not sources and not urls:
            err = "Enter a problem, or point at a sources folder / URLs."
        if err:
            yield sse({"error": err})
            yield sse({"done": True})
            return

        try:
            client = anthropic.Anthropic(api_key=key)
        except Exception as exc:
            yield sse({"error": f"Could not initialize client: {exc}"})
            yield sse({"done": True})
            return

        # A queue bridges the council's writer (background thread) to this SSE stream.
        q: "queue.Queue[str | None]" = queue.Queue()
        error_box: dict[str, str] = {}

        def worker():
            try:
                corpus_text = ""
                if sources or urls:
                    q.put("[corpus] gathering sources…\n")
                    docs = src.collect(folders=[sources] if sources else [], urls=urls)
                    if not docs:
                        raise RuntimeError("No readable documents found in that folder / URLs.")
                    corpus_text, cmode = corpusmod.build_corpus(docs, client, six_hats.MODEL)
                    q.put(f"[corpus] {len(docs)} document(s) — {cmode}.\n")
                council = six_hats.SixHatsCouncil(
                    effort=effort, client=client, writer=q.put
                )
                council.run(problem, mode, corpus=corpus_text)
            except anthropic.AuthenticationError:
                error_box["msg"] = "That API key was rejected. Check it and your billing credit."
            except Exception as exc:  # surface anything else cleanly to the page
                error_box["msg"] = str(exc)
            finally:
                q.put(None)  # sentinel: worker done

        threading.Thread(target=worker, daemon=True).start()

        while True:
            chunk = q.get()
            if chunk is None:
                break
            yield sse({"t": chunk})
        if error_box:
            yield sse({"error": error_box["msg"]})
        yield sse({"done": True})

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def main() -> None:
    url = "http://127.0.0.1:5000"
    print(f"\n  Six Thinking Hats is running at {url}")
    print("  (Opening your browser… press Ctrl+C here to stop.)\n")
    # Open the browser shortly after the server starts.
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=5000, threaded=True)


if __name__ == "__main__":
    main()
