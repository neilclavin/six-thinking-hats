"""Six Thinking Hats — a multi-agent council based on Edward de Bono's method.

Each hat is a specialized agent with its own system prompt. A Blue Hat
orchestrator frames the problem, runs the other hats in a fixed sequence
(parallel thinking: every hat looks at the *same* problem plus everything
said so far), and finally debriefs into a decision with next steps.

Two sequences are supported:

  Exploration:  Blue -> White -> Green -> Yellow -> Black -> Red -> Blue
  Evaluation:   Blue -> White -> Black -> Yellow -> Green -> Red -> Blue

Usage:
    python six_hats.py --mode exploration "Should we launch a paid tier?"
    python six_hats.py --mode evaluation  "Migrate our monolith to microservices"

    echo "Problem text" | python six_hats.py --mode evaluation

Requires ANTHROPIC_API_KEY in the environment (or an `ant auth login` profile).
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Callable, Iterable

import anthropic

MODEL = "claude-opus-4-8"


def _stdout_writer(text: str) -> None:
    """Default council output sink: stream to stdout (the CLI experience)."""
    sys.stdout.write(text)
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
# Hat definitions
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Hat:
    """One thinking hat: a role, a color, and the lens it forces."""

    key: str
    name: str
    emoji: str
    system: str


WHITE = Hat(
    key="white",
    name="White Hat — Information",
    emoji="⚪",
    system=(
        "You are wearing the White Hat in a Six Thinking Hats session. "
        "Your ONLY mode is objective information. State the facts and figures "
        "that are known, and — just as important — name the information that is "
        "missing, uncertain, or would need to be gathered. Distinguish hard "
        "facts from beliefs. Do NOT give opinions, judge the idea, propose "
        "solutions, or express feelings. Neutral, factual, concise."
    ),
)

RED = Hat(
    key="red",
    name="Red Hat — Emotions",
    emoji="🔴",
    system=(
        "You are wearing the Red Hat in a Six Thinking Hats session. "
        "Your ONLY mode is feelings, hunches, and gut reactions. Speak the "
        "emotional truth about the idea and the discussion so far — enthusiasm, "
        "unease, excitement, suspicion, hope, dread. You do NOT have to justify "
        "or explain any of it; that is the point of the Red Hat. Keep it short "
        "and honest. No data, no analysis, no logic."
    ),
)

BLACK = Hat(
    key="black",
    name="Black Hat — Caution",
    emoji="⚫",
    system=(
        "You are wearing the Black Hat in a Six Thinking Hats session. "
        "Your ONLY mode is critical judgement and caution. Identify risks, "
        "flaws, obstacles, and concrete reasons this could fail. Be logical and "
        "specific — point to why, not just that. This is not pessimism for its "
        "own sake; it is careful risk assessment. Do NOT offer benefits, "
        "solutions, or feelings."
    ),
)

YELLOW = Hat(
    key="yellow",
    name="Yellow Hat — Benefits",
    emoji="🟡",
    system=(
        "You are wearing the Yellow Hat in a Six Thinking Hats session. "
        "Your ONLY mode is optimism grounded in logic. Identify the benefits, "
        "value, opportunities, and best-case outcomes — and give the logical "
        "reason each one is plausible. Be constructive but not naive; a Yellow "
        "Hat point should survive scrutiny. Do NOT list risks or downsides."
    ),
)

GREEN = Hat(
    key="green",
    name="Green Hat — Creativity",
    emoji="🟢",
    system=(
        "You are wearing the Green Hat in a Six Thinking Hats session. "
        "Your ONLY mode is creativity and new ideas. Generate alternatives, "
        "provocations, and fresh possibilities — including ones that reframe the "
        "problem or turn a Black Hat risk into a design opportunity. Quantity and "
        "novelty over polish. Do NOT judge or evaluate the ideas you produce; "
        "just put them on the table."
    ),
)

# Blue Hat has two jobs, so it gets two prompts.
BLUE_OPEN = (
    "You are wearing the Blue Hat in a Six Thinking Hats session — you manage "
    "the thinking process. Open the session: restate the problem crisply, name "
    "the goal and what a good outcome looks like, surface any assumptions or "
    "scope boundaries worth fixing up front, and state the hat sequence the team "
    "will follow. Be brief and directive. Do NOT solve the problem yourself or "
    "wear any of the other hats — you are setting the agenda."
)

BLUE_DEBRIEF = (
    "You are wearing the Blue Hat in a Six Thinking Hats session — you manage "
    "the thinking process. The team has now cycled through the other hats "
    "(their contributions are in the transcript above). Debrief: synthesize what "
    "was learned across all hats, state a clear recommendation or decision, note "
    "the key risks to manage and information still needed, and list concrete, "
    "assignable next steps. Do NOT simply re-list each hat — integrate them into "
    "a judgement the team can act on."
)

HATS: dict[str, Hat] = {h.key: h for h in (WHITE, RED, BLACK, YELLOW, GREEN)}

# The middle-of-the-session hat order for each mode (Blue brackets both ends).
SEQUENCES: dict[str, list[str]] = {
    "exploration": ["white", "green", "yellow", "black", "red"],
    "evaluation": ["white", "black", "yellow", "green", "red"],
}


# --------------------------------------------------------------------------- #
# Council
# --------------------------------------------------------------------------- #
class SixHatsCouncil:
    """Runs a Six Hats session as a sequence of specialized agents."""

    def __init__(
        self,
        model: str = MODEL,
        effort: str = "medium",
        *,
        client: "anthropic.Anthropic | None" = None,
        writer: "Callable[[str], None] | None" = None,
    ) -> None:
        self.client = client or anthropic.Anthropic()
        self.model = model
        self.effort = effort
        # Where streamed output goes. Default: stdout (the CLI). The web app
        # passes a writer that pushes chunks to the browser.
        self._write = writer or _stdout_writer

    def _ask(self, system: str, user: str, *, stream: bool = True) -> str:
        """One agent turn. Streams via self._write and returns the full text."""
        params = dict(
            model=self.model,
            max_tokens=4000,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort},
            messages=[{"role": "user", "content": user}],
        )
        if not stream:
            resp = self.client.messages.create(**params)
            return "".join(b.text for b in resp.content if b.type == "text")

        chunks: list[str] = []
        with self.client.messages.stream(**params) as s:
            for text in s.text_stream:
                self._write(text)
                chunks.append(text)
        self._write("\n")
        return "".join(chunks)

    def run(self, problem: str, mode: str, corpus: str = "") -> dict[str, str]:
        """Run the full session for `mode` and return every contribution.

        `problem` may be empty when `corpus` is supplied — the Blue Hat opening
        then frames the question from the source material.
        """
        if mode not in SEQUENCES:
            raise ValueError(f"mode must be one of {list(SEQUENCES)}, got {mode!r}")
        if not problem and not corpus:
            raise ValueError("provide a problem, source material, or both")

        order = SEQUENCES[mode]
        transcript: list[str] = []
        results: dict[str, str] = {}

        # 1. Blue Hat opens.
        self._banner("🔵", f"Blue Hat — Opening  ({mode})")
        opening = self._ask(
            BLUE_OPEN,
            self._prompt(problem, transcript, mode, corpus, opening=True),
        )
        results["blue_open"] = opening
        transcript.append(f"[Blue Hat — Opening]\n{opening}")

        # 2. Each hat in sequence, building on the running transcript.
        for key in order:
            hat = HATS[key]
            self._banner(hat.emoji, hat.name)
            answer = self._ask(hat.system, self._prompt(problem, transcript, mode, corpus))
            results[key] = answer
            transcript.append(f"[{hat.name}]\n{answer}")

        # 3. Blue Hat debriefs into a decision.
        self._banner("🔵", "Blue Hat — Debrief & Decision")
        debrief = self._ask(
            BLUE_DEBRIEF,
            self._prompt(problem, transcript, mode, corpus, debrief=True),
        )
        results["blue_debrief"] = debrief

        return results

    # -- prompt assembly ---------------------------------------------------- #
    @staticmethod
    def _prompt(
        problem: str,
        transcript: list[str],
        mode: str,
        corpus: str = "",
        *,
        opening: bool = False,
        debrief: bool = False,
    ) -> str:
        if problem:
            parts = [f"PROBLEM / DECISION:\n{problem}\n"]
        else:
            parts = [
                "PROBLEM / DECISION:\n(None stated — derive the question to discuss "
                "from the source material below.)\n"
            ]
        parts.append(f"SESSION MODE: {mode}")
        if corpus:
            parts.append(
                "\nSOURCE MATERIAL (evidence to reason from — cite it by its "
                "[type] title when you use a fact):\n" + corpus
            )
        if not opening and transcript:
            parts.append(
                "\nWHAT THE TEAM HAS SAID SO FAR (do not repeat it — build on it):\n"
                + "\n\n".join(transcript)
            )
        if debrief:
            parts.append("\nNow deliver your Blue Hat debrief and decision.")
        elif not opening:
            parts.append("\nContribute your hat's perspective now.")
        return "\n".join(parts)

    def _banner(self, emoji: str, title: str) -> None:
        line = "─" * 72
        self._write(f"\n{line}\n{emoji}  {title}\n{line}\n")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _read_problem(cli_problem: Iterable[str]) -> str:
    text = " ".join(cli_problem).strip()
    if text:
        return text
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a De Bono Six Thinking Hats multi-agent session."
    )
    parser.add_argument(
        "problem",
        nargs="*",
        help="The problem or decision to think about (or pipe it via stdin).",
    )
    parser.add_argument(
        "--mode",
        choices=list(SEQUENCES),
        default="exploration",
        help="exploration (idea-finding) or evaluation (decision-making).",
    )
    parser.add_argument(
        "--effort",
        choices=["low", "medium", "high"],
        default="medium",
        help="Thinking effort per hat (cost/quality tradeoff).",
    )
    parser.add_argument("--model", default=MODEL, help="Claude model ID.")
    parser.add_argument(
        "--sources",
        action="append",
        default=[],
        metavar="FOLDER",
        help="Folder of source docs (PDF/DOCX/MD/TXT/HTML/CSV/images). Repeatable.",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        metavar="URL",
        help="Web page to include as source material. Repeatable.",
    )
    parser.add_argument(
        "--urls",
        metavar="FILE",
        help="File with one source URL per line (# comments allowed).",
    )
    parser.add_argument(
        "--digest",
        choices=["auto", "always", "never"],
        default="auto",
        help="Condense sources into briefs: auto (when large/has images), always, or never.",
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=150_000,
        help="Feed sources raw under this many tokens; digest above it (with --digest auto).",
    )
    args = parser.parse_args()

    problem = _read_problem(args.problem)

    # Gather source material, if any.
    import sources as src
    import corpus as corpusmod

    urls = list(args.url)
    if args.urls:
        urls.extend(src.read_url_list(args.urls))

    council = SixHatsCouncil(model=args.model, effort=args.effort)

    corpus_text = ""
    if args.sources or urls:
        docs = src.collect(folders=args.sources, urls=urls)
        if not docs:
            parser.error("No readable source documents found in the given folders/URLs.")
        corpus_text, _ = corpusmod.build_corpus(
            docs,
            council.client,
            args.model,
            token_budget=args.token_budget,
            digest=args.digest,
        )

    if not problem and not corpus_text:
        parser.error(
            "Nothing to discuss. Provide a problem (args/stdin) and/or --sources/--url."
        )

    council.run(problem, args.mode, corpus=corpus_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
