```mermaid
mindmap
  root((Sprint 07: Service Hardening, UI Integration, and Legacy Cleanup))
    Goal
      "Dockerize FastAPI services (ML Inference, Ingestion Orchestration)"
      "Integrate persistent cache for ingestion service"
      "Begin integrating Streamlit UI with backend services via HTTP API"
      "Continue deprecation of legacy code"
      "Ensure system stability and robust testing"
    Big_Wins
      "Fully decoupled UI/backend (all communication via HTTP API)"
      "Robust testing and documentation"
    Abandoned
      "Legacy direct model/database access in UI (now via service_api.py)"
    Next
      "Performance profiling, further E2E testing, persistent cache rollout"
``` 