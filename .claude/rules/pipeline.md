---
paths:
  - "pipeline/**"
---

- runner.py is the orchestration engine — changes here affect the entire pipeline
- Steps execute in order: ingest → analysis → audio → video → distribute
- PipelineContext carries state between steps (episode_number, transcript, analysis, etc.)
- Each step function receives context and returns updated context
- Checkpoint keys in pipeline_state.py enable resume from failure point
- distribute.py is the largest step (33K) — handles scheduling, uploading, notifications, blog, search index
