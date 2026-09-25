Please clean up the floating site captions in `/root/Storm-Damage-Survey.pptx`.
Use `/root/survey_caption_alignment.csv` to standardize the site wording first.
Only use rows that provide both a `reported_name` and a `normalized_site`, and ignore rows whose `record_status` is `ignore` or `retired`.

On the survey slides, clean only the floating site captions.
Keep the smaller zone badges, severity labels, inspector notes, and the rest of the slide copy unchanged.

For every site caption:
- change the font to Arial, font size 14, font color #5B6776, and turn bold off
- widen the caption box enough so the caption stays on a single line
- place the caption banner at the bottom center of the slide

The deck already ends with a slide titled `Inspection Index`.
Replace the bullet list on that existing final slide with each unique standardized caption exactly once, in the order it first appears in the deck, using auto-numbered bullet points.
Do not add another slide.

Save the finished deck to `/root/Storm-Damage-Survey_cleaned.pptx`.
