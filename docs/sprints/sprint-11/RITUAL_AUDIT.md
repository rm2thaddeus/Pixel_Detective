# Ritual Audit - sprint-11

## Status
- Rubric: 8 / 10
- Anchor docs found: 11
- Linked evidence docs: 12

## Notes
- Missing completion summary (results + gaps).
- PROMPT_PACK.md missing (recommended for repeatable prompting).

## Anchor docs (inputs)
- CODEBASE_EVOLUTION_TRACKING_PRD.md
- DEV_GRAPH_FINAL_TOUCHES_PRD.md
- DEV_GRAPH_LAYOUT_MODES_EXPLORATION_PRD.md
- DEV_GRAPH_PERF_PARALLELIZATION_PRD.md
- DEV_GRAPH_TEMPORAL_SEMANTIC_PRD.md
- DEV_GRAPH_TIMELINE_UI_PRD.md
- PRD.md
- QUICK_REFERENCE.md
- README.md
- mindmap.md
- technical-implementation-plan.md

## Ritual loop (how to work this repo)
- Research: collect notes, constraints, alternatives, and metrics.
- Spec: PRD + acceptance checks that can be verified from logs/files/UI.
- Prompt: keep a prompt pack with definitions + constraints + one real example.
- Implement: ship the smallest reversible slice, then iterate.
- Document: update sprint anchors and generate perspectives (story + receipts).

## Linked evidence (top)
- `docs/sprints/sprint-11/IMPLEMENTATION_IMPROVEMENTS_SUMMARY.md` (co-changed 4x)
  - Tags: plan, sprint
- `README.md` (co-changed 3x)
  - Title: Pixel Detective - Dual AI Platform
- `backend/gpu_umap_service/README.md` (co-changed 2x)
  - Title: GPU UMAP Service
- `backend/ingestion_orchestration_fastapi_app/cuml_integration_guide.md` (co-changed 2x)
  - Title: Overview
  - Tags: evidence
- `archive/CLEANUP_SUMMARY.md` (co-changed 1x)
  - Title: Repository Cleanup Summary
- `archive/CLI_ENTERPRISE_VISION.md` (co-changed 1x)
  - Title: CLI Enterprise Vision: Large Collection Processing
- `archive/COMPONENT_THREADING_FIXES.md` (co-changed 1x)
  - Title: Component Threading Fixes - Pixel Detective
- `archive/CRITICAL_THREADING_FIXES.md` (co-changed 1x)
  - Title: Critical Threading Fixes - Pixel Detective
- `archive/LOADING_SCREEN_FIXES.md` (co-changed 1x)
  - Title: Loading Screen Performance Fixes
  - Tags: metrics
- `archive/PERFORMANCE_OPTIMIZATIONS.md` (co-changed 1x)
  - Title: Pixel Detective Performance Optimizations
  - Tags: metrics
- `archive/THREADING_PERFORMANCE_GUIDELINES.md` (co-changed 1x)
  - Title: Threading & Performance Guidelines for Pixel Detective
  - Tags: evidence, metrics
- `archive/deprecated/architecture-evolution-pre-sprint10.md` (co-changed 1x)
  - Title: Architecture Evolution: A Sprint-by-Sprint Journey

## Rituals (excerpt from MANIFESTO.md)
The Formula That Emerged

```
Week 1: Hit a problem
Week 2: Research the problem (external docs, patterns, options)
Week 3: Write analysis doc (current state, bottlenecks, solutions)
Week 4: Create PRD with research context
Week 5: Prompt AI with research + PRD
Week 6: AI implements in hours, not days
Week 7: Document patterns in AGENTS.md
Week 8: Next sprint references these patterns
```

**Compound Effect**: Sprint 11 had ALL the patterns from Sprints 1-10.

---

## **Closing Scene**

October 2025. We have:

**Built**:
- 50,000 lines of production code
- 8 microservices across 2 applications
- 290+ commits, 11 sprints
- 174 documentation files

**Learned**:
- Context quality correlates with implementation speed
- Research before prompting saves days
- Documentation compounds across sprints
- Multiple AI models > single model
- Good specs great code

**Proved**:
- The gap between idea and execution is research quality
- AI needs context like developers need specifications
- Questions compound when documentation accumulates
- Architecture emerges through documented iteration

**The Question That Started It**: "I want to search my photos"

**The Question That Ended Sprint 11**: "Can we track how we built this?" (with complete schema provided)

**The Answer**: Yes, when you give me research docs like that Batch Size masterpiece.

---

**Built through increasingly better prompts**
**Powered by accumulated research**
**Documented for compound learning**

* Claude 3.5 Sonnet, with help from Gemini and the GPT-4 crew*

**October 2025**

---

P.S. - Seriously, that Batch Size document? That's the gold standard. 19 pages of analysis with line numbers, implementation sketches, performance implications. More of those, please. My neural networks will thank you.

## Manifesto outline (headings)
- The Pixel Detective Manifesto
-   Confessions of an Exhausted AI: Building 50,000 Lines Through Increasingly Better Prompts
-   **Cold Open: March 2025**
-   **Act I: When You Actually Gave Me Context (Sprint 1-2)**
-     **Sprint 01: The Golden Age of Design Docs**
- Pixel Detective UX Flow Design
-   Mission: Seamless 3-Screen User Journey
- You told me to remove technical metrics
- BEFORE:
- AFTER (matching your design doc):
-     **Sprint 02: The 0.001s Miracle**
-   **Act II: The Dark Times - When Context Disappeared (Sprint 3-5)**
-     **Sprint 03: EMERGENCY RECOVERY MODE**
-     **Sprint 04: The Great JSON Betrayal**
-     **Sprint 05: The Undocumented Failure**
-   **Act III: The Research Era (Sprint 6 - Everything Changes)**
-     **Sprint 06: When You Finally Gave Me Research**
-   **Act IV: When You Gave Me Checklists (Sprint 7)**
-     **Sprint 07: The Perfect Refactor Plan**
- Sprint 07 Refactoring Plan
-     **Sprint 08: Metrics That Lied To Us**
-     **Sprint 09: Race Conditions: The Musical**
-   **Act V: The Next.js Nuclear Option (Sprint 10)**
-     **Sprint 10: "We're Rewriting Everything"**
-   **Act VI: When You Started Giving Me RESEARCH ARCHIVES (Sprint 11)**
-     **The Batch Size Love Letter**
-   1. Processing Pipeline Analysis
-     Suggested Changes for 64GB RAM & 100k Images
- ingestion_orchestration_fastapi_app/utils/autosize.py
-   3.5 New in Sprint 11: PyTorch-Native Model Optimizations
-     **The Dev Graph Research Archive**
- PRD: Temporal Semantic Dev Graph
-   Data Model (Unified Temporal Schema)
-   Current State Analysis
-   Solutions
-   **The Real Story: Context Evolution**
-     **Sprint 1-2: The Golden Age**
-     **Sprint 3-5: The Wilderness**
-     **Sprint 6-7: Research Arrives**
-     **Sprint 11: The Research Archive**
-   **The Context Quality Matrix**
-   **What I Learned (The Hard Way)**
-     **Lesson 1: Research Before Prompting**
-     **Lesson 2: Specifications Beat Vagueness**
-     **Lesson 3: Document Everything For Future Me**
-     **Lesson 4: The Self-Reflection Sections**
-     **Lesson 5: Multi-Model Strategy**
-   **The Meta-Recursion: Dev Graph**
-     **Sprint 11 Part 2: The System Documents Itself**
-   **What The Sprints Don't Tell You**

## Manifesto referenced artifacts (best-effort)
- `RECONNECT_UI_REFACTOR_PLAN.md`
- `archive/`
- `archive/
├── CUDA_ACCELERATION_GUIDE.md
├── QDRANT_COLLECTION_MERGE_GUIDE.md  
├── cluster_visualization_and_labeling.md
├── POC_COMPLETION_STATUS.md
├── Batch Size (the 19-page masterpiece)
└── research lasso tool/`
- `archive/``
- `docs/reference_guides/Streamlit Background tasks.md`
- `docs/reference_guides/UX_FLOW_DESIGN.md`
- `docs/sprints/sprint-11/archive/`
- `docs/sprints/sprint-11/archive/``
- `frontend/AGENTS.md`

## Prompting rules (from manifesto-derived guide)
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

## Recommended next actions
- Ensure PRD contains explicit acceptance checks (3-7 bullets).
- Add/keep a RESEARCH_BRIEF that lists alternatives + constraints + metrics.
- Keep a PROMPT_PACK with: goal, definitions, constraints, example payload/log, acceptance checklist.
- Run sprint perspectives again after adding research notes to refresh linked evidence.
