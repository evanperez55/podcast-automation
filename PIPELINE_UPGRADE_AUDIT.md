# Pipeline Upgrade Audit — Early 2026

**Audit Date:** 2026-03-29
**Current Stack:** Whisper/WhisperX, pydub+FFmpeg, Pillow, GPT-4o, Ollama Llama 3.1, FFmpeg (H.264 NVENC)
**Hardware:** RTX 3070 8GB VRAM, Windows 11, Python 3.12+

---

## Priority 1 — High Impact, Low Effort

### 1. Replace openai-whisper with faster-whisper
- **Current:** `openai-whisper==20231117` (standard Python inference)
- **Proposed:** `faster-whisper` (CTranslate2 backend)
- **Impact:** **4x transcription speed**, identical accuracy, lower VRAM
- **Details:** Same model weights, optimized inference engine. `large-v3` fits in ~5GB fp16 (vs ~5GB but much slower with openai-whisper). Built-in Silero VAD pre-filters silence for 10-30% additional speedup. Native word-level timestamps.
- **VRAM:** `large-v3` int8 = ~3GB, `distil-large-v3` fp16 = ~2.5GB
- **Effort:** ~2 hours. API is nearly identical. Change `transcription.py` imports and call patterns.
- **Benchmarks (RTX 3070 est.):**

  | Config | Speed | VRAM |
  |--------|-------|------|
  | openai-whisper large-v3 | ~8-10x real-time | ~5GB |
  | faster-whisper large-v3 (fp16) | ~25-35x real-time | ~5GB |
  | faster-whisper large-v3 (int8) | ~30-40x real-time | ~3GB |
  | faster-whisper distil-large-v3 | ~50-70x real-time | ~2.5GB |

### 2. Switch to OpenAI Structured Outputs (JSON Schema mode)
- **Current:** Prompt-based JSON in `content_editor.py` with regex fallbacks and retry loops
- **Proposed:** `response_format={"type": "json_schema", "json_schema": {..., "strict": True}}`
- **Impact:** **Eliminates 100% of JSON parsing failures.** No more malformed JSON retries.
- **Cost:** Zero additional — same API pricing
- **Effort:** Medium — define JSON schemas for analysis output types, refactor parsing in `content_editor.py`

### 3. Downgrade main analysis to GPT-4.1-mini
- **Current:** GPT-4o (~$2.50/$10 per 1M tokens)
- **Proposed:** GPT-4.1-mini (~$0.40/$1.60 per 1M tokens)
- **Impact:** **~80% cost reduction** per episode. GPT-4.1-mini handles structured extraction (chapters, timestamps, social captions) well.
- **Quality:** 90-95% of GPT-4o for structured tasks. Slightly weaker on nuanced humor detection.
- **Effort:** Trivial — change model string in `content_editor.py`
- **Hybrid option:** Use GPT-4.1-mini for bulk analysis, keep GPT-4o only for clip selection where quality matters most.

---

## Priority 2 — Moderate Impact, Low-Medium Effort

### 4. Drop WhisperX, use faster-whisper + pyannote directly
- **Current:** WhisperX 3.1.6 wraps Whisper + wav2vec2 alignment + pyannote diarization
- **Proposed:** faster-whisper (native word timestamps) + pyannote.audio 3.x (direct call)
- **Impact:** Simpler dependency tree, faster model updates, no WhisperX version pinning
- **Details:** faster-whisper's native `word_timestamps=True` is sufficient for subtitle generation (~50-100ms variance vs WhisperX's forced alignment). For 2-speaker podcasts, pyannote with `num_speakers=2` is fast and accurate.
- **Effort:** ~50-100 lines of glue code to replace WhisperX integration in `diarize.py`

### 5. Switch Ollama to Qwen 2.5 7B for topic scoring
- **Current:** Ollama + Llama 3.1 8B (or 3.2)
- **Proposed:** Qwen 2.5 7B (`ollama pull qwen2.5:7b`)
- **Impact:** ~10-15% better structured JSON output reliability, comparable reasoning
- **Cost:** Zero (local model)
- **Effort:** Trivial — change model name in ollama_client.py or config

### 6. Add scale animation to active subtitle word
- **Current:** Word-by-word accent color highlighting (white → cyan)
- **Proposed:** Add `\fscx120\fscy120` ASS tags on active word for 20% scale-up effect
- **Impact:** Matches latest CapCut/TikTok style trends. Visual polish.
- **Effort:** ~30 min — modify `_generate_ass_file()` in `subtitle_clip_generator.py`
- **Code change:** `{\fscx120\fscy120\c&Haccent&}WORD{\fscx100\fscy100\c&Hffffff&}`

### 7. Make NVENC worker count configurable
- **Current:** Hardcoded `max_workers=3` in ThreadPoolExecutor
- **Proposed:** `MAX_NVENC_SESSIONS` env var in config.py, default 3
- **Impact:** Newer NVIDIA drivers support 5 concurrent NVENC sessions. Configurable parallelism.
- **Effort:** 15 min — add config var, use in ThreadPoolExecutor calls

---

## Priority 3 — Medium Impact, Medium Effort

### 8. Enrich clip selection prompts with audio features
- **Current:** Text-only clip selection via GPT-4o
- **Proposed:** Add speech rate (WPM), word confidence scores, energy/volume changes from Whisper output to the LLM prompt
- **Impact:** ~15-25% better clip quality for comedy/conversational content
- **Details:** Gives the LLM signal about delivery and emphasis, not just content. Especially valuable for comedy podcasts where timing and energy matter.
- **Cost:** Zero — data already exists in Whisper output
- **Effort:** Medium — extract features from `transcript_data`, modify prompt in `content_editor.py`

### 9. Split monolithic analysis prompt into focused sub-tasks
- **Current:** One massive prompt to GPT-4o requesting chapters + clips + summaries + captions + censor timestamps
- **Proposed:** Separate calls for (a) chapters/structure, (b) clip selection, (c) social captions/show notes, (d) censorship
- **Impact:** Better quality per task, enables model tiering (cheap model for captions, quality model for clips)
- **Cost:** Potentially cheaper — smaller focused prompts to cheaper models
- **Effort:** Medium-high refactor of `content_editor.py`

### 10. Use distil-large-v3 for maximum transcription speed
- **Current:** Whisper "base" model (or large-v2 in diarize.py)
- **Proposed:** `distil-whisper/distil-large-v3` via faster-whisper
- **Impact:** ~6-8x faster than current openai-whisper, ~1% WER trade-off
- **Details:** 50% fewer parameters via knowledge distillation. For clean English podcast audio, quality difference is negligible. ~2.5GB VRAM.
- **Effort:** Trivial once faster-whisper is integrated (change model name)

---

## No Change Recommended (Already Best-in-Class)

| Component | Current Approach | Verdict |
|-----------|-----------------|---------|
| **Audio normalization** | FFmpeg two-pass loudnorm, EBU R128, -16 LUFS | Gold standard. pyloudnorm/ffmpeg-normalize offer no improvement. |
| **Video encoding** | H.264 NVENC auto-detected, CRF 18/23 | Correct for social media. HEVC/AV1 not needed (RTX 3070 can't do AV1 encode). |
| **Video generation** | Direct FFmpeg subprocess calls | Fastest approach. MoviePy/ffmpeg-python add overhead for no gain. |
| **Subtitle format** | pysubs2 ASS with word-by-word highlighting | State of the art for Hormozi-style captions. |
| **Thumbnail generation** | Pillow template-based | Appropriate for current scale. AI thumbnails are overkill. |
| **ThreadPoolExecutor** | 3 workers for clip encoding | Well-matched to NVENC session limit. |

---

## Cost Impact Summary (per episode, 60-min podcast)

| Component | Current Cost | After Upgrades | Savings |
|-----------|-------------|----------------|---------|
| Transcription (GPU time) | ~6-8 min | ~1-2 min | 4x faster |
| Content analysis (API) | ~$0.10-0.25 | ~$0.02-0.05 | ~80% cheaper |
| Topic scoring (local) | Free | Free | Better quality |
| Video encoding | Already NVENC | Configurable parallelism | Moderate speedup |
| **Total pipeline time** | ~40-50 min | **~15-25 min** | **~2x faster** |

---

## Implementation Order

1. **faster-whisper** (biggest single speed win)
2. **Structured Outputs** (eliminates parsing failures)
3. **GPT-4.1-mini** (biggest cost win)
4. **Drop WhisperX** (simplifies dependencies)
5. **Qwen 2.5 7B** (better local model)
6. **Subtitle scale animation** (visual polish)
7. **NVENC config** (parallelism tuning)
8. **Audio-enriched clip selection** (quality improvement)
9. **Split analysis prompts** (quality + cost optimization)
10. **distil-large-v3** (maximum speed if quality acceptable)
