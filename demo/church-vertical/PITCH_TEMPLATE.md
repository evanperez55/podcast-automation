# Church Outreach Pitch Template

**Instructions:** Copy this file for each prospect. Replace all `{{PLACEHOLDERS}}`.
Process one of their sermons first (`uv run main.py --client {{SLUG}} latest --auto-approve`),
then fill in the specific episode details and upload clips to Google Drive.

---

**Prospect:** {{CHURCH_NAME}}
**Slug:** {{SLUG}}
**Contact:** {{PASTOR_NAME}} / {{CONTACT_EMAIL}}
**Episode referenced:** "{{SERMON_TITLE}}" ({{EPISODE_DATE}})
**Drive folder:** Upload from `output/{{SLUG}}/{{EP_DIR}}/`
**Status:** {{Draft / Ready to send / Sent}}

---

## Email

**Subject:** Made these from your "{{SERMON_TITLE}}" sermon — took 5 minutes

Hey {{FIRST_NAME}},

I watched your sermon "{{SERMON_TITLE}}" — {{SPECIFIC_MOMENT_REFERENCE}}. That's the kind of teaching that deserves to reach people beyond Sunday morning. I ran it through my automation pipeline and here's what came out in about 5 minutes — no manual editing:

[GOOGLE DRIVE LINK]

Inside you'll find:
- {{NUM_CLIPS}} vertical clips with burned-in subtitles (ready for YouTube Shorts / Instagram Reels)
- A devotional-style blog post with full scripture references
- Social captions written per platform (YouTube, Instagram, Facebook, Twitter)
- Chapter markers for the full sermon
- A complete searchable transcript

The clip I'd lead with is "{{BEST_CLIP_TITLE}}" ({{CLIP_TIMESTAMP}}). {{WHY_THIS_CLIP_WORKS}}.

Here's why this matters for {{CHURCH_NAME}}: right now your sermons live on YouTube as a single full-length video. That's a great start — but here's what you're leaving on the table:

**Sermon transcripts get 7x more organic traffic from Google.** When someone in {{CITY}} searches "what does the Bible say about {{SERMON_TOPIC}}" at 2am on a Wednesday, your sermon already has the answer — but Google can't find it because it's locked inside a video file. A transcript makes every sermon a searchable page on your website, forever.

**YouTube Shorts have the longest shelf life of any content format.** A 30-second clip of {{PASTOR_NAME}} teaching on {{SERMON_TOPIC}} keeps getting discovered via YouTube search for months. One sermon can generate 5+ Shorts, each reaching people who'd never click a 45-minute video.

**The math:** 52 sermons/year = 52 blog posts, 260+ clips, 52 transcript pages, and hundreds of social posts. Doing this manually takes 4-6 hours per sermon. My pipeline does it in 5 minutes.

I'd like to process your next 4 sermons completely free. No strings — you keep everything. If you like the output, we talk about automating the whole thing. If not, you've got a month of free content.

Would it be easier to jump on a 10-minute call this week, or should I just send the next batch when it's ready?

{{SENDER_NAME}}
{{SENDER_URL}} | {{SENDER_LINKEDIN}}

---

## Follow-Up Email (send 4-5 days later if no response)

**Subject:** Re: Made these from your "{{SERMON_TITLE}}" sermon

Hey {{FIRST_NAME}},

Quick follow-up — I know church weeks are busy. Here are the clips in case the link got buried:

{{CLIP_1_TITLE}} ({{CLIP_1_DURATION}}): [direct link]
{{CLIP_2_TITLE}} ({{CLIP_2_DURATION}}): [direct link]
{{CLIP_3_TITLE}} ({{CLIP_3_DURATION}}): [direct link]

These are ready to post — just download and upload to YouTube Shorts or Instagram Reels. No editing needed.

Also: I checked, and {{CHURCH_NAME}} doesn't have searchable sermon transcripts on your website. That means Google can't index any of your {{PASTOR_NAME}}'s teachings. With 52 sermons a year, you're sitting on a massive SEO opportunity that most churches miss.

Happy to walk through it on a quick call, or I can just process the next few sermons and send them over.

{{SENDER_NAME}}

---

## What to Upload to Drive Before Sending

Source files at `output/{{SLUG}}/{{EP_DIR}}/`:

- `/clips/*_subtitle.mp4` — all video clips with subtitles
- `*_blog_post.md` — devotional blog post
- `*_show_notes.txt` — sermon summary and key points
- `*_thumbnail.png` — episode thumbnail
- First ~500 words of `*_transcript.json` saved as `transcript_preview.txt`
- `*_episode.mp4` — full episode video (optional, large file)

---

## Pitch Customization Notes

**Lead with the angle most relevant to this church:**

- **SEO angle** (best for churches with a website but no blog):
  "Only 1.8% of US churches have searchable sermon transcripts. Your sermons answer questions people Google every day — but right now Google can't find them."

- **Growth angle** (best for churches actively trying to grow):
  "YouTube Shorts from sermons reach people who'd never click a 45-minute video. One sermon = 5+ Shorts, each a front door to your church."

- **Time-saving angle** (best for overworked comms directors):
  "Your comms person is probably spending 4-6 hours per sermon on content. This gets it down to zero — it's fully automated."

- **Stewardship angle** (best for budget-conscious churches):
  "You're already recording every sermon. Right now that investment produces one YouTube video. This turns it into 15+ content pieces — same investment, 15x the output."
