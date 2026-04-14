"""GPU resource cleanup — library/test use only.

History (B011, re-diagnosed): this helper originally ran at the end of
every pipeline as a "clean window" for ctranslate2 to release CUDA
state before interpreter shutdown. In practice, calling `del
transcriber.model` here IS what triggered STATUS_STACK_BUFFER_OVERRUN
(exit code 3221226505) on a subset of Windows runs — faulthandler
caught the crash inside the ctranslate2 C++ destructor invoked by that
del. Python `try/except` cannot catch native stack corruption, so the
"swallow errors" comments below give false safety for the real hazard.

Current strategy: main.py flushes stdout then calls os._exit(0),
which terminates the process without running any destructors. The OS
reclaims GPU state, CUDA handles, and open files. No manual teardown
is needed on the success path, and the pipeline no longer calls this
function. It is retained for library callers and tests.
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
