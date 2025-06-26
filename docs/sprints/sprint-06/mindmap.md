```mermaid
mindmap
  root((Sprint 06: Modular Service Architecture for Image Ingestion))
    Goal
      "Modularize data ingestion into FastAPI services (ML inference, ingestion, Qdrant)"
      "Implement in-memory cache and batch processing"
    Big_Wins
      "Service-oriented architecture"
      "Batch efficiency and caching"
      "End-to-end testing of new pipeline"
    Abandoned
      "Monolithic script-based ingestion (replaced by services)"
    Next
      "Persistent cache, Dockerization, UI integration (future work)"
``` 