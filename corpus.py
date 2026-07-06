"""Turn a list of source Documents into a single corpus block for the hats.

Adaptive strategy:
  * raw   — if the material is small and text-only, tag each document with its
            provenance and concatenate verbatim.
  * digest — if it's over the token budget, or contains images, or the caller
            forces it, condense each document to key facts + notable quotes
            (with provenance), reading image documents via the vision model.

The digest keeps the hats focused and bounds token cost without any tuning.
"""

from __future__ import annotations

import sys

import anthropic

from sources import Document

_DIGEST_SYSTEM = (
    "You are a neutral research assistant preparing a source brief for a "
    "decision-making session. Extract only what is actually present: the key "
    "facts, figures, decisions, and 2-4 notable verbatim quotes. Preserve "
    "meaning; do not add opinions, analysis, or recommendations. If the source "
    "is an image or design, describe its content, structure, and any text it "
    "contains. Be concise and faithful to the source."
)


def _provenance(doc: Document) -> str:
    return f"=== [{doc.source_type}] {doc.title} ({doc.uri}) ==="


def _raw_block(docs: list[Document]) -> str:
    parts = []
    for doc in docs:
        if doc.text:
            parts.append(f"{_provenance(doc)}\n{doc.text.strip()}")
    return "\n\n".join(parts)


def _count_tokens(client: anthropic.Anthropic, model: str, text: str) -> int:
    resp = client.messages.count_tokens(
        model=model, messages=[{"role": "user", "content": text or " "}]
    )
    return resp.input_tokens


def _digest_document(client: anthropic.Anthropic, model: str, doc: Document) -> str:
    """One model call condensing a single document (text or image) to a brief."""
    if doc.is_image:
        media_type, data = doc.image  # type: ignore[misc]
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
            {"type": "text", "text": f"Summarize this source ({doc.title}) into a faithful brief."},
        ]
    else:
        content = [{"type": "text", "text": f"Summarize this source into a faithful brief:\n\n{doc.text}"}]

    resp = client.messages.create(
        model=model,
        max_tokens=1200,
        system=_DIGEST_SYSTEM,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def build_corpus(
    docs: list[Document],
    client: anthropic.Anthropic,
    model: str,
    *,
    token_budget: int = 150_000,
    digest: str = "auto",  # "auto" | "always" | "never"
) -> tuple[str, str]:
    """Assemble docs into a corpus string.

    Returns ``(corpus_text, mode)`` where mode is "raw", "digested", or "empty".
    """
    if not docs:
        return "", "empty"

    has_images = any(d.is_image for d in docs)
    raw = _raw_block(docs)

    if digest == "never":
        if has_images:
            _note("warning: --digest never drops image sources (they need vision).")
        return raw, "raw"

    if digest == "auto":
        raw_tokens = _count_tokens(client, model, raw) if raw else 0
        if not has_images and raw_tokens <= token_budget:
            _note(f"corpus: {len(docs)} document(s), ~{raw_tokens} tokens — feeding raw.")
            return raw, "raw"
        why = "contains images" if has_images else f"~{raw_tokens} tokens over budget"
        _note(f"corpus: {len(docs)} document(s), {why} — digesting each source.")
    else:  # "always"
        _note(f"corpus: {len(docs)} document(s) — digesting each source (forced).")

    briefs: list[str] = []
    for i, doc in enumerate(docs, 1):
        _note(f"  digesting {i}/{len(docs)}: {doc.title}")
        try:
            brief = _digest_document(client, model, doc)
        except Exception as exc:
            _note(f"  digest failed for {doc.title}: {exc}")
            continue
        briefs.append(f"{_provenance(doc)}\n{brief}")
    return "\n\n".join(briefs), "digested"


def _note(msg: str) -> None:
    print(f"[corpus] {msg}", file=sys.stderr)
