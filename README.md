# 🎩 Six Thinking Hats — AI council

Edward de Bono's **Six Thinking Hats** method, run as six AI agents in your browser.

Each hat is one mode of thinking — White (facts), Red (feelings), Black (caution),
Yellow (benefits), Green (creativity), Blue (process). A Blue Hat frames your problem,
the other hats weigh in one at a time, and Blue closes with a decision and next steps.
Because each hat is a *separate* call with its own instructions, you get six clean
perspectives instead of one answer trying to be everything at once.

It's a **single HTML file** — no install, no server. It runs entirely in your browser and
talks straight to Claude using **your own** Anthropic API key.

## Try it

**Hosted:** open the GitHub Pages link for this repo _(add yours here once Pages is on —
see below)_, paste your key, and go.

Then:
1. **Paste your Anthropic API key** (see below to get one). Tick "Remember on this device"
   if you don't want to paste it each time.
2. Type a **problem or decision** (and/or paste reference text / drop in `.txt`/`.md`
   files and images).
3. Pick **Exploration** (open up ideas) or **Evaluation** (pressure-test and decide),
   choose a model, and hit **Run the council**.
4. Watch the six hats stream in, ending with the Blue Hat's decision.

Sample material to try is in [`demo/`](demo/) — drag those `.md` files onto the drop zone.

## Get your API key (everyone needs their own)

This calls Claude, which is a paid API, so each person brings their own key:

1. Go to **[console.anthropic.com](https://console.anthropic.com/settings/keys)** and sign
   in (this is separate from a Claude.ai subscription).
2. **Billing → add a little credit** ($5 lasts a long time).
3. **API keys → Create Key**, copy it (`sk-ant-...`), and paste it into the page.

Your key is used only for your runs and is **only ever sent to Anthropic** — it stays in
your browser. "Remember on this device" saves it in your browser's local storage on your
machine; leave it unticked on shared computers.

**Cost:** one session is ~7 calls. Defaulting to **Sonnet** with **Short** length keeps a
run to a few cents; Opus + Long costs more but goes deeper.

## Host it on GitHub Pages (to share a link)

```bash
# from this folder, once:
gh repo create six-thinking-hats --public --source=. --push
```

Then on GitHub: **Settings → Pages → Build and deployment → Deploy from a branch →
`main` / `/ (root)` → Save.** After a minute your app is live at
`https://<your-username>.github.io/six-thinking-hats/`. Share that link.

> **Don't just double-click `index.html`.** Opened from disk (`file://`) the browser may
> block the API call. Use the GitHub Pages URL (or any web server).

## What it does and doesn't handle

- ✅ Typed problems, pasted reference text, drag-dropped `.txt`/`.md` files, and images
  (images are described by the vision model, then discussed).
- ❌ PDFs/Word docs and fetching web URLs — browsers can't do those cleanly without extra
  machinery. Paste the text in instead.

## Make it your own

Everything is in [`index.html`](index.html): the six hat prompts (`HATS`, `BLUE_OPEN`,
`BLUE_DEBRIEF`), the two sequences (`SEQUENCES`), and the `run()` orchestrator. Tweak a
hat's instructions, add a sequence, or restyle the page — it's plain HTML/CSS/JS with no
build step and no dependencies.
