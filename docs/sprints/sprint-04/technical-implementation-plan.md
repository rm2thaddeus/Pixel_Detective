# Sprint 04 Technical Implementation Plan: Threading & Task Orchestration

**Objective:** Establish a centralized background-task system and refactor existing components to use it, ensuring thread safety, performance, and maintainability.

## Goals

- Centralize all background threads in a single `components/task_orchestrator.py` module.
- Refactor UI components (search, visualization, sidebar) to delegate all work to the orchestrator.
- Enforce thread-safety: no direct `threading.Thread` calls in components; use guard flags.
- Integrate component-level progress reporting into existing `LoadingProgress` or new `ComponentProgress` structures.
- Validate with benchmarks: achieve at least 30% reduction in UI load and task latency.
- Update documentation and share guidelines with the team.

## Key Deliverables (Story Points)

| Deliverable                                                   | Points |
|---------------------------------------------------------------|:------:|
| `task_orchestrator.py` implementation + unit tests             |   3    |
| Refactor `components/search` to use orchestrator              |   2    |
| Refactor `components/visualization` to use orchestrator       |   2    |
| Refactor `components/sidebar` to use orchestrator             |   2    |
| Integrate component progress into UI screens                  |   2    |
| End-to-end integration tests and performance benchmarks       |   3    |
| Documentation updates (`Streamlit Background tasks.md`, `THREADING_PERFORMANCE_GUIDELINES.md`, this sprint doc) | 1 |

_Total: 15 SP_

## Sprint Backlog

1. **Create Task Orchestrator** (`components/task_orchestrator.py`)
   - API: `submit(name, fn, *args) -> bool`, `is_running(name) -> bool`
   - Internal: thread registry + lock
   - Tests: ensure single-thread enforcement, thread completion tracking

2. **Refactor Components**
   - In `components/search/search_tabs.py`, call orchestrator instead of raw threads
   - In `components/visualization/latent_space.py`, delegate projections to orchestrator
   - In `components/sidebar/context_sidebar.py`, wrap any async tasks via orchestrator

3. **Progress Integration**
   - Extend `LoadingProgress` or create `ComponentProgress` dataclass for per-job reporting
   - Surface progress in `screens/loading_screen.py` and advanced UI tabs

4. **Testing & Benchmarking**
   - Write integration tests: simulate multiple rapid reruns, ensure only one thread per job
   - Run benchmarks on sample dataset; capture pre/post load times and log files

5. **Documentation & Knowledge Sharing**
   - Finalize this sprint doc in `/docs/sprints/sprint-04`
   - Update `THREADING_PERFORMANCE_GUIDELINES.md` with orchestrator reference
   - Host a short walkthrough with the team: demos of orchestrator usage

## Timeline & Ownership

- **Day 1–2:** Orchestrator core implementation and tests (Owner: Backend) 5 SP
- **Day 3–4:** Component refactors & progress integration (Owner: Frontend) 6 SP
- **Day 5:** Testing, benchmarking, docs, and review (Owner: Full team) 4 SP

---

This plan ensures we lock down a robust, maintainable threading model before we scale with more features. Let's crush Sprint 04! 