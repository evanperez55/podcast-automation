"""GPU resource cleanup for pipeline runs.

Why this exists: on Windows, ctranslate2/cuDNN destructors can trigger
STATUS_STACK_BUFFER_OVERRUN (exit code 3221226505) during Python
interpreter shutdown after long pipelines that have loaded a Whisper
model. Explicit teardown BEFORE the interpreter starts shutting down
gives the native libraries a clean window to release GPU state while
Python bookkeeping is still intact.

Every call swallows its own errors — cleanup running after a
successful pipeline run must never be what makes that run look like
a failure.
"""
from __future__ import annotations

import gc

from logger import logger


def release_gpu_resources(components: dict | None = None) -> None:
    """Drop Whisper model + GPU caches at the end of a successful pipeline run.

    Args:
        components: The pipeline components dict returned by
            _initialize_components(). Expected to contain a 'transcriber'
            key. Safe to pass None or an empty dict.
    """
    # Step 1: Drop the Transcriber's internal Whisper model first. Doing
    # this before GC gives ctranslate2 a chance to free CUDA handles while
    # the reference graph is intact.
    if components:
        transcriber = components.get("transcriber")
        if transcriber is not None:
            try:
                if hasattr(transcriber, "model") and transcriber.model is not None:
                    del transcriber.model
                    transcriber.model = None
            except Exception as e:
                logger.debug("Transcriber model cleanup skipped: %s", e)

    # Step 2: Drop remaining component references + force a full GC cycle
    try:
        if components:
            components.clear()
        gc.collect()
    except Exception as e:
        logger.debug("GC cleanup skipped: %s", e)

    # Step 3: Release CUDA cache explicitly. torch.cuda.synchronize() waits
    # for in-flight kernels so the free happens in a well-defined order.
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
    except ImportError:
        pass
    except Exception as e:
        logger.debug("CUDA cleanup skipped: %s", e)
