# Sprint 04 → Sprint 05 Transition

## Pending Items for Sprint 05

- [ ] Define follow-on tasks for UI polish with orchestrator insights
- [ ] Evaluate integration of enterprise API endpoints
- [ ] Determine further performance optimization areas
- [ ] Plan AI feature enhancements beyond threading architecture
- [ ] Formalize and implement the 3-screen state machine (FAST_UI → LOADING → ADVANCED_UI) using `AppState` and `LoadingPhase` enums per UX_FLOW_DESIGN.
- [ ] Build the FAST_UI screen: instant launch with folder selection, live status indicators, and automatic background triggers (Progressive Loading).
- [ ] Develop the LOADING screen: display real-time progress bar, live logs, current phase indicator, ETA estimation, and pause/cancel controls for user engagement.
- [ ] Create the ADVANCED_UI screen: tabbed interface for Text/Image Search, AI Guessing Game, Latent Space Explorer, and Duplicate Detection.
- [ ] Integrate orchestrator task events into UI transitions: update `st.session_state.loading_phase` and `loading_logs` for seamless feedback.
- [ ] Implement skeleton screens and subtle animations during loading phases to improve perceived performance.
- [ ] Enhance sidebar context for each screen state: contextual commands, status summaries, and next-step prompts as documented in UX_FLOW_DESIGN.
- [ ] Diagnose and fix `BLIP_MODEL_NAME` undefined error in caption generation pipeline to prevent database build crashes.
- [ ] Optimize app startup time by deferring heavy ML and CUDA imports, leveraging lazy loading and performance skeletons. 