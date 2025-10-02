# Manifesto‑Derived Rules
## The Cognitive Immune System For AI Projects (Non‑Coder Edition)

This is a field guide for giving AI assistants the right “nutrients” so they don’t hallucinate, overfit, or melt your GPU. Think psychology meets immunology: you provide the antibodies (context), the system builds memory (docs), and future bugs get neutralized faster.

---

## Core Axioms (Psychologist’s View)
- Name the goal in concrete, observable terms. Describe what you expect to see on screen, in logs, or in a file.
- Define the world. Provide vocabulary: what words mean, what “done” means, what is out of scope.
- Show one real example. One payload, one screenshot, one tiny folder path beats paragraphs.
- Bound the sandbox. Time budgets, memory/device limits, ports, directories, OS quirks.
- Share your priors. What you tried, what broke, why you think it did.
- State acceptance checks as bullets. Humans read vibes; agents need checklists.

---

## Innate vs. Adaptive Immunity (Immunologist’s View)
- Innate defenses (always on):
  - Typed contracts for APIs and files (Pydantic models, versioned schemas)
  - Idempotency on writes (tokens, fingerprints)
  - Async by default; isolate CPU work with `asyncio.to_thread()`
  - React Query for all polling; no ad‑hoc `useEffect + fetch`
  - “Do not” boundaries: never import `main` from routers; never block event loop; no browser APIs during render
- Adaptive defenses (learned from incidents):
  - Path normalization before hashing or indexing
  - GPU lease manager with locks/semaphores per device
  - Bounded queues with backpressure instead of vibes
  - Batched, idempotent upserts to vector DB
  - Hydration‑safe UI widgets and timezones normalized to UTC

---

## Ten Golden Rules For Non‑Coders
1) Tell me what “good” looks like. One sentence + one example.
2) Define key terms (e.g., caption vs caption_text). Ambiguity is a bug.
3) Paste a sample payload with correct keys/units and an expected response.
4) Specify constraints: device, GPU/CPU, memory/time budget, ports.
5) List acceptance checks (3–5 bullets). I will treat these as tests.
6) Point to where the work lives (folders/files/services/URLs).
7) Include one log or screenshot that shows the failure.
8) Call out non‑goals and tradeoffs you accept.
9) Link any prior sprint doc or issue that’s relevant.
10) Say how safe we must be: can we change schemas? Can we migrate data?

---

## Copy‑Paste Mini Templates

### Feature Request (Vaccination)
Goal: <what should exist, in plain words>
Why: <user story / outcome>
Scope: <pages/services affected>
Definitions: <domain terms and meanings>
Constraints: <devices, budgets, ports, OS>
Example Payload: <json snippet>
Acceptance:
- [ ] <check 1>
- [ ] <check 2>

### Bug Report (Pathogen)
Observed: <what you saw>
Expected: <what you wanted>
Repro: <short steps + sample file/path>
Env: <OS, GPU/CPU, versions>
Evidence: <one log/screenshot>
Blast radius: <who/what is affected>

### Refactor Plan (Antibodies)
Target: <module/service>
Invariants: <must not change>
Risks: <what might break>
Migration: <order of operations + fallback>
Rollback: <how to revert safely>

### Research Brief (Immunization)
Hypothesis: <what you think will help>
Alternatives: <2–3 options>
Constraints: <hard limits>
Metrics: <how we’ll judge>
Plan: <small experiment, low blast radius>

---

## Incident Antibodies (From The Manifesto)
- Schema drift: version your payloads; validate strictly; reject mixed keys.
- Duplicate vectors: use idempotency tokens and content fingerprints.
- Path chaos: normalize to POSIX before hashing/indexing.
- Hydration errors: client‑only widgets, suspense boundaries, no render‑time browser APIs.
- Lying dashboards: typed metrics endpoints; single source of truth collector; UTC everywhere.
- GPU races: per‑device locks/semaphores; adaptive batch within leases, not vibes.
- Slow I/O: move CPU work to `to_thread`, bound queues, measure end‑to‑end throughput.

---

## One‑Minute Prompt You Can Reuse

“Build/repair X. Good = I can <do/see> Y on <page/service>. Use folders <A/B> and endpoint <C>. Terms: <term: meaning>. Device/time/memory limits: <…>. Here’s a real example payload and expected response: <json>. Acceptance: (1) <…> (2) <…> (3) <…>. Non‑goals: <…>. Prior attempts/log: <1 snippet>. If risky, propose a two‑step plan with a safe fallback.”

---

## Project Memory (Long‑Term Immunity)
- Keep living documents up to date: `AGENTS.md`, architecture, and sprint PRDs.
- Cross‑link incidents to fixes: “symptom → antibody → result.”
- Promote proven patterns to checklists and templates.
- Make the next failure cheaper to fix than the last.

---

## TL;DR
Say what you want, define the world, show one real example, set constraints, give acceptance checks. The agent supplies the rest. That’s how we keep the project healthy.

