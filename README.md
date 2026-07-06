# Six Thinking Hats — Multi-Agent Council

A multi-agent example based on Edward de Bono's **Six Thinking Hats** parallel-thinking
framework. Each hat is a specialized Claude agent with its own system prompt that forces
a single mode of thinking. A **Blue Hat** orchestrator frames the problem, runs the other
hats in sequence, and debriefs the discussion into a decision with next steps.

Because everyone "wears the same hat at the same time," the agents stay focused and
collaborative instead of arguing across perspectives — that's the point of parallel thinking.

---

## 🚀 Quick start (easiest — no terminal needed)

You'll run this on your own computer in a web browser. It takes about two minutes.

1. **Download this project.** On the GitHub page, click the green **Code** button →
   **Download ZIP**. Unzip it (double-click the ZIP).
2. **Start it:**
   - **Mac:** double-click **`run.command`** in the unzipped folder.
   - **Windows:** double-click **`run.bat`**.

   The first time, it installs what it needs (about a minute), then your browser opens
   automatically to the app. (If it says Python isn't installed, install it from
   [python.org/downloads](https://www.python.org/downloads/) — on Windows tick
   *"Add Python to PATH"* — then double-click the launcher again.)
3. **Paste your API key** into the field on the page (see below), type a question, and
   press **Run the council**. The six hats stream in live.

> On a Mac, the first time you may get *"cannot be opened because it is from an
> unidentified developer."* Right-click `run.command` → **Open** → **Open**, just once.

### Get your API key (each person needs their own)

This tool talks to Claude, which is a paid API. Every person who uses it needs their own key:

1. Go to **[console.anthropic.com](https://console.anthropic.com/settings/keys)** and sign in
   (this is separate from a Claude.ai subscription).
2. **Billing → add a little credit** ($5 is plenty for lots of runs).
3. **API keys → Create Key**, copy it (starts with `sk-ant-...`), and paste it into the app.

Your key is used only for your run and is **never stored or sent anywhere except Anthropic** —
it stays on your machine.

### Sharing it with others

There's **no server to host and no cost to you** — you just share this project (send the ZIP,
or the GitHub link). Each person downloads it, double-clicks the launcher, and uses their own
key. *(Note: this can't run on GitHub Pages — that only serves static web pages and can't run
the program or safely hold a key.)*

---

## The hats

| Hat | Mode | What the agent does |
|-----|------|---------------------|
| ⚪ White | Information | Objective facts, data, and the gaps that still need filling |
| 🔴 Red | Emotions | Gut reactions and feelings — no justification required |
| ⚫ Black | Caution | Risks, flaws, and concrete reasons it could fail |
| 🟡 Yellow | Benefits | Value, opportunities, and best-case outcomes (grounded in logic) |
| 🟢 Green | Creativity | New ideas, alternatives, and reframes |
| 🔵 Blue | Process | Sets the agenda, runs the sequence, and debriefs into a decision |

## Two approaches

The Blue Hat brackets both sequences (it opens and closes every session):

- **Exploration** — for finding ideas and possibilities:
  `Blue → White → Green → Yellow → Black → Red → Blue`
- **Evaluation** — for testing a proposal and deciding:
  `Blue → White → Black → Yellow → Green → Red → Blue`

Each hat receives the original problem **plus everything said so far**, so later hats
build on earlier ones rather than starting cold.

## Advanced: run it from the terminal (optional)

The launcher above is all most people need. If you'd rather use the command line — or want
the browser UI without double-clicking — here's the manual path.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # or paste your key in the web page instead

# Browser UI (same app the launcher opens):
python app.py                          # then open http://127.0.0.1:5000

# Or the command-line council:
python six_hats.py --mode exploration "Should we launch a free tier for our SaaS?"
python six_hats.py --mode evaluation  "Migrate our monolith to microservices this quarter"
echo "Adopt a four-day work week" | python six_hats.py --mode evaluation
python six_hats.py --effort low  "..."     # cheaper/faster while testing
```

Output streams hat by hat, ending with the Blue Hat's decision.

## Feeding it sources

Instead of (or in addition to) a typed-in problem, point the council at real
material — a folder of mixed documents and/or web pages. The hats then reason from
that evidence, and the White Hat reports the facts in it.

```bash
# A folder of mixed docs (PDF/DOCX/MD/TXT/HTML/CSV/images) as evidence for a question
python six_hats.py --mode evaluation --sources ./research "Should we change our pricing?"

# Add web pages
python six_hats.py --mode exploration --sources ./research \
  --url https://example.com/market-report --url https://example.com/competitor

# URLs from a file (one per line, # comments allowed)
python six_hats.py --mode evaluation --urls links.txt "Enter the EU market?"

# No explicit problem — the Blue Hat frames the question from the material
python six_hats.py --mode exploration --sources ./research
```

**Supported material:** `.txt .md .csv .json .html` and images (`.png .jpg .gif .webp`)
work out of the box; `.pdf` needs `pypdf` and `.docx` needs `python-docx` (both in
`requirements.txt`). Web pages are fetched over plain HTTP and stripped to text.

**How large material is handled (adaptive, no tuning):**
- If the corpus is small and text-only, it's fed **raw** with a provenance header on
  each document.
- If it's over `--token-budget` (default 150k tokens) or contains images, each source
  is **digested** into key facts + notable quotes (with provenance); images/designs are
  read by the vision model and turned into text.
- Force it either way with `--digest always` / `--digest never`.

**Not included (by design):** live Gmail/Drive/Slack connectors and Figma. These need
API credentials, which this "files & folders only" tool deliberately avoids. For Figma,
export the relevant frames as PNG/PDF into your `--sources` folder — the vision digest
reads them. `sources.py` has a documented `FigmaSource` stub and notes the API path if
you want to wire it up later.

## How it works

- `SixHatsCouncil.run()` drives the session: Blue opening → each hat in the mode's
  sequence → Blue debrief.
- Every turn is a separate Claude call with a hat-specific system prompt (`thinking:
  adaptive`, streamed). Isolating each hat in its own system prompt is what keeps the
  perspectives clean — no single call is asked to be six minds at once.
- A running transcript is threaded into each subsequent prompt so the council reasons
  cumulatively.

## Extending it

- **Add a hat variation** — copy a `Hat(...)` definition and drop it into a sequence.
- **New sequence** — add an entry to `SEQUENCES` (e.g. a short `Blue → Black → Green → Blue`
  problem-solving loop).
- **Return structured output** — `run()` already returns a `dict` of every contribution,
  keyed by hat; feed it to a report generator, a UI, or a follow-up agent.
