# Pitfalls Research

**Domain:** Cross-genre podcast pipeline testing — adapting a comedy-tuned pipeline to real-world client content
**Researched:** 2026-03-28
**Confidence:** HIGH (based on direct codebase analysis; most pitfalls are confirmed code-level issues, not hypothetical)

---

## Critical Pitfalls

### Pitfall 1: Config.NAMES_TO_REMOVE Is Loaded at Import Time with Hardcoded Host Names

**What goes wrong:**
`config.py` defines `NAMES_TO_REMOVE` as a class-level list with Joey, Evan, Dom, Dominique, and their last names baked in. `content_editor.py` reads `Config.NAMES_TO_REMOVE` in `_build_analysis_prompt()` and `_find_words_to_censor_directly()`. If you process a client episode without explicitly setting `names_to_remove` in the client YAML, the Fake Problems host names are injected into the censorship prompt and the direct-search censor loop runs against the new client's transcript. A client episode that happens to feature a guest named "Evan" or mentions "Gross" as an adjective will trigger incorrect censorship.

**Why it happens:**
`Config` is a class with static attributes — it's evaluated at import time. `client_config.py` patches these via `apply_client_config()`, but that only fires if `--client` is passed AND the YAML has a non-null `names_to_remove` list. An empty list `[]` in the YAML correctly overrides to empty. But if the YAML field is omitted entirely (e.g., a client config copied before v1.3 YAML fields were added), the fallback stays as the Fake Problems list.

**How to avoid:**
Require `names_to_remove` to be an explicit field in every client YAML — treat absence as a validation error, not a fallback to defaults. Add a `validate-client` check that flags missing content section fields. When `names_to_remove: []` is set, verify the override actually clears `Config.NAMES_TO_REMOVE` to `[]` (it does, per `client_config.py:117`, but test this explicitly with a real episode).

**Warning signs:**
- Demo output for a non-comedy client has audio gaps where no slurs exist
- GPT-4o prompt contains names like "Joey", "Evan" in the names-to-censor section when processing a true crime or business podcast
- `logger.info("Items to censor: %d", ...)` shows unexpectedly high count

**Phase to address:**
Phase 1 (Client Configuration) — before any real episode is processed. Add a `--dry-run` path that prints the active `Config.NAMES_TO_REMOVE` and `Config.WORDS_TO_CENSOR` so it's auditable before processing.

---

### Pitfall 2: Voice Persona Is Comedy-Specific and Will Corrupt All AI-Generated Output for Non-Comedy Clients

**What goes wrong:**
The fallback `VOICE_PERSONA` in `content_editor.py` is hardcoded as Fake Problems voice: "irreverent comedy show," "dark, weird, and absurd topics," "deadpan confidence." This affects the episode title, social captions, show notes, chapter titles, and blog post. For a true crime podcast or a business interview show, this produces unusable output — chapter titles come out deadpan-comic, show notes read as if the hosts are joking about murder cases, and social captions use comedy framing that will alienate the target audience.

The prompt itself also contains voice examples with Fake Problems-branded BAD/GOOD pairs (lines 263–285 of `content_editor.py`) that are embedded directly in the prompt string, not driven by config. Even if `voice_persona` is set in the YAML, these example blocks remain in the prompt.

**Why it happens:**
The voice examples block is a string literal inside `_build_analysis_prompt()` and is not conditional on whether the client has set a custom voice. The `VOICE_PERSONA` constant is the fallback but the inline voice-examples block always fires regardless.

**How to avoid:**
Make the voice-examples block conditional — only include Fake Problems-specific examples if the active client is `fake-problems` or no custom persona is set. For new clients, replace the example block with genre-appropriate examples drawn from the client config, or omit it entirely and rely on the `voice_persona` field to provide tone guidance.

**Warning signs:**
- Blog post for a true crime client opens with deadpan humor about the subject matter
- YouTube description for a business podcast reads as ironic/comedic
- Chapter titles sound like Fake Problems episode beats ("POV: You Don't Know What POV Means" style)

**Phase to address:**
Phase 1 (Client Configuration) — configure `voice_persona` for each test client before processing. Phase 2 (Integration Fix) — make the voice-examples block conditional on client type or omit when custom persona is provided.

---

### Pitfall 3: Audio Energy Scoring Favors High-Volume Comedy Delivery, Not Substantive Moments

**What goes wrong:**
`AudioClipScorer` ranks segments by RMS energy. Comedy podcasts generate high-energy peaks from shouting, laughter, and fast crosstalk — these map well to "best moments." True crime, business, and interview podcasts often have their most compelling moments during quiet, measured delivery: a revealing confession, a key data point, a moment of tension. RMS scoring will favor segments with the most volume, not the most substance — potentially selecting the wrong clips entirely.

For a solo-host or interview podcast where one person speaks at a consistent volume, energy scores will be nearly flat across all segments, making the energy signal useless as a differentiator. GPT-4o still picks clips, but loses its primary pre-selection signal and will instead pick from whatever the energy_candidates list happens to contain.

**Why it happens:**
RMS energy is a reasonable heuristic for high-energy comedy but conflates volume with interest. The `energy_candidates` are passed to GPT-4o as a strong hint with the instruction "prioritize these for clips" — the model will follow this even when energy scores don't correlate with content quality.

**How to avoid:**
In the client's `voice_persona` field, explicitly instruct GPT-4o to weight content quality over audio energy for this show type. Alternatively, add a `clip_selection_mode` field to the client YAML (`energy` vs. `content`) that controls whether the energy candidates block is included in the prompt at all.

**Warning signs:**
- Selected clips are all loud/overlapping-talk moments, not substantive ones
- For solo-host podcasts, all energy scores cluster in a narrow range (0.3–0.7 for all segments)
- GPT-4o picks clips from the energy candidates list even when the transcript content is mundane

**Phase to address:**
Phase 2 (Integration Fix) — after first-pass processing reveals clip quality issues for non-comedy genres.

---

### Pitfall 4: Compliance Checker Is Tuned to Not Flag Comedy Content, Which May Miss Real Violations in Other Genres

**What goes wrong:**
The compliance checker prompt was explicitly calibrated to avoid over-flagging: "Dark humor and profanity are NOT violations; only genuine hate speech and dangerous misinformation." For a true crime podcast discussing sensitive topics (child abuse, racial violence, extremism), the permissive threshold may under-flag content that YouTube's actual moderation would catch. The inverse is also true: if the client runs a family-friendly or educational channel, profanity that the checker ignores is a genuine violation for that client's context.

**Why it happens:**
`ContentComplianceChecker` uses a single hardcoded prompt. There is no per-client compliance profile. The checker was validated against comedy content only and its calibration reflects that.

**How to avoid:**
Add a `compliance_style` field to the client YAML (`permissive` / `standard` / `strict`). For demo purposes, manually review compliance checker output for the first episode per genre before treating it as reliable. Do not include compliance results in the sales demo without manual verification.

**Warning signs:**
- True crime episode discussing racial violence gets 0 compliance flags
- Family-friendly podcast episode with incidental profanity gets 0 compliance flags
- All clients across all genres produce identical compliance result patterns

**Phase to address:**
Phase 2 (Integration Fix) — after first processing run surfaces compliance gaps per genre.

---

### Pitfall 5: Whisper Base Model Degrades Significantly on Real-World Client Audio Quality

**What goes wrong:**
Whisper (`base` model by default) was validated on Fake Problems WAV files: ~700MB, 70-minute studio recordings with two close-mic'd hosts. Real podcast clients may supply heavily compressed MP3s, phone recordings, laptop mic audio, multi-room echo, or non-native English speakers. Transcription accuracy on these inputs can drop from ~95% word accuracy to 70–80%, which cascades into broken censor timestamps (direct word search misses misspelled words), poor clip selection (GPT-4o works from a garbled transcript), and unusable subtitle clips.

**Why it happens:**
`Config.WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")` — model is configurable but defaults to `base`, the weakest Whisper variant. No per-client model override exists in the client YAML.

**How to avoid:**
Add `whisper_model` to the client YAML content section. For new clients with unknown audio quality, use `small` or `medium` for the initial test run. Validate transcript quality by skimming the output JSON before continuing past Step 2. Set a pre-flight minimum quality bar (e.g., no severe clipping, file at least -30 LUFS average).

**Warning signs:**
- Transcript contains obvious wrong words or garbled proper nouns
- Episode title generated by GPT-4o doesn't match episode content at all
- `censor_timestamps` is empty even when host names are known to appear in the episode

**Phase to address:**
Phase 1 (Client Setup) — confirm audio quality and set appropriate Whisper model before processing. Add a manual transcript spot-check step before proceeding.

---

### Pitfall 6: Episode Numbering Assumption Breaks for Non-Sequential or Non-Numeric Episode IDs

**What goes wrong:**
The pipeline parses episode numbers from filenames using the `ep25` convention. Many podcasts use date-based filenames (`2024-03-15-episode-title.wav`), descriptive slugs (`cold-case-greenville.mp3`), or season/episode notation (`S01E03`). The `episode_number` field in `PipelineContext` drives checkpoint keys, output directory names, analytics storage, RSS entry creation, and search index entries. If parsing fails and resolves to `None`, all episodes map to the same state key — which silently breaks checkpoint resume (subsequent runs overwrite the first) and analytics (records overwrite each other).

**Why it happens:**
Episode number extraction in `run_ingest` is built around the Fake Problems naming convention. There is no per-client episode number extraction strategy in the current YAML schema.

**How to avoid:**
Before processing a real client's first episode, run `--dry-run` and confirm the resolved `episode_number` is meaningful. For date-based filenames, pre-rename files to the `ep01_original-name` convention before processing, or derive a sequential number from the Dropbox folder listing order.

**Warning signs:**
- Output directory named `ep_None` or `ep_0`
- Checkpoint file named with `None` as the episode key
- Second episode processing overwrites the first episode's checkpoint state

**Phase to address:**
Phase 1 (Client Setup) — verify with `--dry-run` before live processing.

---

### Pitfall 7: Hardcoded Podcast Name in GPT-4o Prompt Leaks into Client AI Output

**What goes wrong:**
`content_editor.py` line 287 embeds `Config.PODCAST_NAME` directly into the analysis prompt: `You are analyzing a podcast transcript for "{Config.PODCAST_NAME}"`. The blog generator also reads `Config.NAMES_TO_REMOVE` for its own prompt. If `activate_client()` is called before components are instantiated, the overrides are applied correctly. But if any component is instantiated before `activate_client()` — or in test/dry-run mode where client config isn't loaded — Fake Problems values bleed through.

**Why it happens:**
`Config` class attributes are read at the moment `_build_analysis_prompt()` is called, not at component init time. This is correct behavior. But the risk is that any path through the code that bypasses `activate_client()` (a test, an isolated dry-run, a direct runner invocation) will use Fake Problems defaults.

**Warning signs:**
- Blog post for a client mentions "Fake Problems Podcast"
- Social captions reference the wrong show name
- `validate-client` passes but processed output contains wrong podcast name

**Phase to address:**
Phase 1 (Client Setup) — add an assertion in `validate-client` that checks `Config.PODCAST_NAME` matches the YAML `podcast_name` after activation.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded voice examples in `_build_analysis_prompt` | Works perfectly for Fake Problems | Every new genre requires code changes, not config changes | Never for multi-client use |
| `Config.NAMES_TO_REMOVE` falls back to Fake Problems list | Safe default for original use case | Incorrect censorship for all new clients unless explicitly cleared in YAML | Never — should default to empty list for new clients |
| Single compliance prompt for all clients | Simple, no per-client complexity | Under/over-flags content for different genres | Only for single-client deployment |
| `WHISPER_MODEL = "base"` global default | Fast processing on known good audio | Poor accuracy on real-world client audio | Acceptable for Fake Problems only |
| Episode number from filename convention | Simple, works for ep25 naming | Breaks for any client using date or slug naming | Acceptable only after explicit pre-flight check |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Dropbox for new client | Assuming episode files are WAV; many clients deliver MP3 | Confirm file format before processing; pydub handles MP3 but some path logic assumes WAV extension |
| YouTube token per client | Using the global token pickle path without setting `youtube.token_pickle` in the client YAML | Each client needs its own token pickle path — they cannot share a single OAuth token |
| RSS feed output | All clients write to the same `podcast_feed.xml` unless output dirs are isolated | Confirm `OUTPUT_DIR` is client-specific before the RSS step runs |
| Compliance checker | Running compliance before reviewing transcription accuracy | Compliance results are only meaningful if the transcript is accurate — spot-check transcript first |
| Audio energy candidates | Passing energy candidates to GPT-4o for a flat-energy interview podcast | Consider suppressing the energy block for shows where RMS variance is low |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Whisper `base` on CPU | 30–45 min transcription per episode | Confirm CUDA is available; set `WHISPER_MODEL=small` minimum for unknown audio | Immediately on CPU-only or shared machines |
| pydub loading full 700MB WAV | ~4GB RAM peak during energy scoring | Not a new issue but confirm client files aren't multi-track or unusually large | Files >90 min or files larger than ~800MB |
| GPT-4o cost for demo run | ~$0.50–0.80 per episode × 3 clients | Budget ~$3 for initial test runs; not a problem at this scale | Non-issue at 2–3 client demo scale |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing real client credentials in YAML | Credential exposure in git history | Confirm `clients/*.yaml` is in `.gitignore` except `example-client.yaml`; use `null` values + env vars |
| Demo using private client episode content | Client content shared without consent | Use publicly available episodes for demos; get explicit permission before processing private audio |
| Shared Dropbox credentials across clients | One client's revoked token breaks all | Each client config specifies its own Dropbox credentials |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `--auto-approve` on first client test run | Bad clips reach the demo package without review | Always run interactively on first episode per client to calibrate expectations |
| Demo output not reviewed before presenting | Prospective client sees wrong tone, wrong podcast name, or garbled AI output | Establish a manual review gate before packaging any demo artifact |
| Clip approval UI showing no genre context | Reviewer can't tell if a quiet moment is good for true crime vs. comedy | Add genre note from `voice_persona` to clip approval display, or add reviewer notes in the demo package |

---

## "Looks Done But Isn't" Checklist

- [ ] **Config override active:** After `activate_client()`, print `Config.PODCAST_NAME`, `Config.NAMES_TO_REMOVE`, `Config.WORDS_TO_CENSOR` — confirm they match the client YAML, not Fake Problems defaults
- [ ] **Voice persona in prompt:** Check debug log of `_call_openai_with_retry` — confirm system prompt is the client voice, not the Fake Problems fallback
- [ ] **Voice examples block:** Confirm Fake Problems-specific BAD/GOOD examples (lobster immortality, etc.) are absent from the GPT-4o prompt for non-comedy clients
- [ ] **Output directory isolation:** Confirm `Config.OUTPUT_DIR`, `Config.CLIPS_DIR`, and `Config.DOWNLOAD_DIR` are client-specific paths before ingest starts
- [ ] **RSS isolation:** Verify RSS generator writes to client-specific output dir, not global `podcast_feed.xml`
- [ ] **Episode number resolves:** Run `--dry-run` and confirm `episode_number` is a meaningful value for the client's filename convention
- [ ] **Transcript quality:** Skim first 10 segments of the generated transcript JSON before proceeding past Step 2
- [ ] **Compliance calibration:** Manually review compliance output for first episode per genre — confirm it's appropriate for that content type and channel
- [ ] **Demo artifacts reviewed:** All demo output (clips, thumbnail, blog post, social captions) manually reviewed for correct client voice before presenting to prospective client

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong host names censored | LOW | Fix YAML `names_to_remove`, delete `analyze` and `censor` checkpoint keys, re-run from Step 3 (transcription preserved) |
| Wrong voice persona in output | LOW | Fix YAML `voice_persona`, delete `analyze` checkpoint key, re-run Step 3 and downstream |
| Poor transcript quality | MEDIUM | Set `WHISPER_MODEL=small` or `medium` in client YAML, delete `transcribe` checkpoint, re-run all steps |
| Episode number parsed as None | LOW | Rename source file to `ep01_original-name.ext` convention before re-run |
| Demo presented with wrong tone or podcast name | HIGH | Full re-run with corrected config + manual review of all output before re-presenting |
| Fake Problems host names censored in client audio | LOW | Fix YAML `names_to_remove: []`, delete `analyze` and `censor` checkpoints, re-run from Step 3 |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| NAMES_TO_REMOVE leakage | Phase 1: Client Config Setup | `--dry-run` prints active `Config.NAMES_TO_REMOVE`; confirm it is empty or matches client hosts |
| Voice persona not applied | Phase 1: Client Config Setup | Check GPT-4o system prompt in debug log before full run |
| Fake Problems voice examples in prompt | Phase 2: Integration Fixes | Review analysis output for first client; fix prompt logic if genre mismatch detected |
| Energy scoring wrong for genre | Phase 2: Integration Fixes | Review clip selection quality after first client run; suppress energy block if needed |
| Compliance calibration wrong | Phase 2: Integration Fixes | Manual review of compliance output for first episode per genre |
| Whisper model too weak | Phase 1: Client Config Setup | Add `whisper_model` to client YAML; use `small` minimum for unknown audio quality |
| Episode number parse failure | Phase 1: Client Config Setup | `--dry-run` confirms `episode_number` resolves to a non-None value |
| Hardcoded podcast name leaks | Phase 1: Client Config Setup | `validate-client` checks `Config.PODCAST_NAME` matches YAML after activation |
| Demo output not reviewed | Phase 3: Demo Packaging | Manual review gate before packaging; never use `--auto-approve` on first client run |

---

## Sources

- Direct codebase analysis: `content_editor.py` lines 11–17, 85, 209, 263–285, 287, 465–570
- Direct codebase analysis: `config.py` lines 132, 141–186
- Direct codebase analysis: `client_config.py` lines 77–182
- Direct codebase analysis: `audio_clip_scorer.py` full file
- Direct codebase analysis: `pipeline/steps/analysis.py`, `pipeline/steps/audio.py`
- Project history: `PROJECT.md` lines 129–130 (compliance calibration decisions and rationale)
- Client config templates: `clients/example-client.yaml`, `clients/fake-problems.yaml`

---
*Pitfalls research for: Cross-genre podcast pipeline testing (v1.4 real-world client testing)*
*Researched: 2026-03-28*
