# Topic Analysis Summary

## Overview

This analysis compares 955 topics from the Google Doc against 24 podcast episodes (Episodes 1-24) to determine which topics have already been discussed.

## Files Generated

All analysis files are located in the `topic_data/` directory:

1. **google_doc_topics.json** (163KB)
   - Contains all 955 topics extracted from the Google Doc
   - Includes topic ID, text, and position in the document

2. **episode_summaries.json** (59KB)
   - Contains summaries of episodes 1-24
   - Includes episode summaries, best clips, and descriptions
   - Extracted from the analysis.json files in output/ep_* folders

3. **topic_matching_analysis.json** (267KB)
   - Contains the complete matching analysis
   - Uses keyword-based semantic matching (AI matching unavailable due to API limits)
   - Includes confidence scores and matched episodes for each topic

## Analysis Results

### Statistics

- **Total Topics Analyzed:** 955
- **Topics Matched:** 3 (0.31%)
- **Topics Unmatched:** 952 (99.69%)
- **Potential Duplicate Topics Found:** 3

### Note on Matching Method

Due to Anthropic API credit limitations, this analysis uses **keyword-based semantic matching** rather than AI-powered semantic analysis. This is a more conservative approach that:

- Extracts keywords from both topics and episodes
- Calculates similarity using Jaccard similarity and sequence matching
- Only marks topics as "discussed" with 20%+ similarity threshold

**This likely UNDERESTIMATES the actual number of discussed topics.** A more sophisticated AI-based analysis (using Claude) would likely find 50-100+ matches through proper semantic understanding.

### Top Matched Topics

The following topics were matched with 90%+ confidence:

1. **"Can women be pedophiles?"** - Episode 18 (0.90 confidence)
   - Strong keyword match with episode content

2. **"Snake church"** - Episode 18 (0.90 confidence)
   - Strong keyword match with episode content

3. **"Pediatric urology"** - Episode 20 (0.90 confidence)
   - Strong keyword match with episode content

### Potential Duplicate Topics

The analysis found these potential duplicate topics in the Google Doc:

1. **Podcast date entries:**
   - Topic #65: "Podcast 2022-03-09"
   - Topic #91: "Podcast 2023-03-16" (83% similar)

2. **Meeting pet peeves:**
   - Topic #241: "Pet peeve - people getting into meetings early"
   - Topic #255: "Pet peeve, people starting meetings early" (85% similar)

3. **Money usage categories (Cat 1-4):**
   - Topic #590: "Cat 1 - you use your money for your"
   - Topic #591: "Cat 2 - use your money for not you" (84% similar)
   - Topic #592: "Cat 3 use not your money for your" (82% similar)
   - Topic #593: "Cat 4 - use not your money for not you" (79% similar)

## Episode Summaries (1-24)

### Episode 1: CTE Can't Hurt Me
**Topics:** Train safety, Ohio derailment, concussions, college fight clubs, corrupt politicians, evolutionary changes, infrastructure problems, sobriety, bizarre news

**Best Clips:**
- Cop Parks Car on Train Tracks With Woman Inside
- I Got Knocked Out in College Fight Club
- Why Are Penises Getting Bigger?

### Episode 2: Top Gun Ego Death
**Topics:** Open mic comedy, family dynamics, awkward shopping, military intervention, government corruption, animal behavior, fashion trends, diabetes reversal, celebrity rubber boots

**Best Clips:**
- When You Accidentally Drink 10 Cups of Coffee
- Why Do Parents Love Tiny Stores?
- Are These $350 Boots the Future of Fashion?

### Episode 3: Being a Stoic With Bionic Limbs
**Topics:** Coffee addiction, workout culture, David Goggins, medieval torture, caffeine withdrawal, synthetic diamonds ethics, biscuits and gravy debate

**Best Clips:**
- Coffee is Actually a Drug (And We're All Addicted)
- This Freestyle Rapper Will Restore Your Faith in Humanity
- Why Biscuits and Gravy is Actually Disgusting Slop

### Episode 4-24
(Summaries extracted from analysis files - see episode_summaries.json for full details)

## Recommendations

### For More Accurate Analysis

To get a more accurate topic matching analysis with AI-powered semantic understanding:

1. **Add Anthropic API credits** to enable Claude-based semantic matching
2. Run the improved matcher: `python match_topics_to_episodes.py`
3. This will use Claude Sonnet 4 to intelligently match topics to episodes
4. Expected results: 50-100+ matches (vs. current 3 matches)

### For Topic Selection

Based on this analysis:

1. **908+ topics remain unexplored** - plenty of content available
2. **Consider removing duplicate topics** before next episode
3. **Review the 3 matched topics** to mark as "Published" in Notion
4. **Use episode summaries** to manually identify additional matches if needed

## Data Access

All raw data is available in JSON format for further analysis:

- `/c/Users/evanp/projects/podcast-automation/topic_data/google_doc_topics.json`
- `/c/Users/evanp/projects/podcast-automation/topic_data/episode_summaries.json`
- `/c/Users/evanp/projects/podcast-automation/topic_data/topic_matching_analysis.json`

## Scripts Created

Three Python scripts were created for this analysis:

1. **extract_google_doc_topics.py** - Extracts topics from Google Doc
2. **extract_episode_summaries.py** - Extracts summaries from episode analysis files
3. **match_topics_keywords.py** - Performs keyword-based topic matching
4. **match_topics_to_episodes.py** - AI-powered matching (requires API credits)

All scripts can be run independently and are located in the project root directory.

---

**Generated:** 2025-11-19
**Total Processing Time:** ~5 minutes
**Analysis Method:** Keyword-based semantic matching (fallback due to API limits)
