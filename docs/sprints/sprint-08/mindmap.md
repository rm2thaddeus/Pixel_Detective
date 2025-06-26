```mermaid
mindmap
  root((Sprint 08: Qdrant Integration, Core Feature Delivery & Frontend Refactoring))
    Goal
      "Full Qdrant integration for backend search and image listing"
      "Implement duplicate detection, random image, advanced filtering/sorting"
      "Refactor frontend to use service API exclusively"
      "Improve error handling, UI polish, and testing"
    Big_Wins
      "API-driven UI (all backend ops via service_api.py)"
      "Legacy code cleanup and stateless UI"
    Abandoned
      "Direct backend/model access in frontend (now only via API)"
    Next
      "UI/UX polish, async/await modernization, accessibility improvements"
``` 