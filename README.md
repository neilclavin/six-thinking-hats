# Six Thinking Hats

Edward de Bono's **Six Thinking Hats** method, run as a one-page evaluation in your browser.

Four hats — White (facts), Black (caution), Yellow (benefits), Green (creativity) — plus
Red (feelings) each give their perspective on your decision in three short sentences,
generated in parallel. The Blue Hat then acts as judge: it weighs where the perspectives
converge or where one clearly outweighs the others, and delivers a single recommendation
and next step. Because each hat is a *separate* call with its own instructions, you get
distinct perspectives instead of one answer trying to be everything at once.

It's a **single HTML file** — no install, no server. It runs entirely in your browser and
talks straight to Claude using **your own** Anthropic API key. Warm paper background,
serif type, minimal linework — a worksheet, not a dashboard.

## Try it

**Hosted:** open the GitHub Pages link for this repo, paste your key, and go.

1. **Paste your Anthropic API key** (see below to get one).
2. State **the decision** (and/or upload `.txt`/`.md` files or images as source material).
3. Hit **Weigh it up**. The five hats appear together and fill in as they respond, then
   Blue delivers the verdict underneath.

Sample material to try is in [`demo/`](demo/) — upload those `.md` files from the form.

## Get your API key (everyone needs their own)

This calls Claude, which is a paid API, so each person brings their own key:

1. Go to **[console.anthropic.com](https://console.anthropic.com/settings/keys)** and sign
   in (this is separate from a Claude.ai subscription).
2. **Billing → add a little credit** ($5 lasts a long time).
3. **API keys → Create Key**, copy it (`sk-ant-...`), and paste it into the page.

Your key is used only for your runs and is **only ever sent to Anthropic** — it's never
saved, so you'll paste it in each visit.

**Cost:** one session is ~6 short calls on Sonnet — typically a few cents.

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

- ✅ A typed problem, and uploaded `.txt`/`.md` files or images (images are described by
  the vision model, then discussed).
- ❌ PDFs/Word docs and fetching web URLs — browsers can't do those cleanly without extra
  machinery.

## Make it your own

Everything is in [`index.html`](index.html): the five hat prompts and order (`HATS`,
`HAT_ORDER`), the judge's prompt (`BLUE_VERDICT`), and the `startSession()` orchestrator.
Tweak a hat's instructions or restyle the page — it's plain HTML/CSS/JS with no build step
and no dependencies.
