# Architectural Decisions — Do Not Revisit Without Discussion

These decisions were made deliberately. Do not "fix" or undo them.

## Content Processing
- NEVER remove filler words from transcripts — kills comedy timing (learned Apr 7)
- Clip time distribution must span full episode — beginning, middle, end (not just best moments)
- Audio normalization targets -16 LUFS for podcasts

## Platform & Pricing
- Twitter API is pay-per-use (~$0.01/tweet), NOT a $100/mo subscription
- Instagram token expires every 60 days — must manually refresh and update GitHub Secret
- YouTube compliance checker required after ep29 strike

## Infrastructure
- No CI/CD pipeline — manual GitHub Actions only (decided v1.4)
- cuDNN v8 DLLs manually copied to ctranslate2 dir — may need re-copy after venv rebuild
- NEVER run multiple episode pipelines simultaneously — kills GPU/RAM
- Episode source for prospect clients is RSS (not Dropbox)

## Business / Outreach
- Pitch angle is FULL AUTOMATION — "we automate your entire post-production and social media workflow"
- NOT "you don't have clips" — almost every podcast already has social presence
- Scoring rewards active shows with reachable hosts, penalizes network-backed shows
- Prospect handle checks use show/host names, NOT slugs (slugs give false positives)

## Website
- GitHub Pages via fakeproblemspodcast org (not personal account) — keeps Evan's name off public site
- Single index.html, no framework, no build step
- Episode pages generated with full transcripts for SEO
