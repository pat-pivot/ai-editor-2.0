-- AI Editor 2.0: Seed System Prompts with Python Variable Syntax
-- Date: December 24, 2025
--
-- IMPORTANT: These prompts use Python f-string variable syntax:
--   {variable}  - Will be substituted by Python
--   {{          - Literal opening brace (for JSON output)
--   }}          - Literal closing brace (for JSON output)
--
-- Run this after init.sql to populate prompts

-- ============================================================================
-- STEP 1: PRE-FILTER PROMPTS (Gemini 3 Flash Preview)
-- ============================================================================

-- Insert prompt metadata first
INSERT INTO system_prompts (prompt_key, step_id, name, description, model, temperature, slot_number, is_active)
VALUES
    ('slot_1_prefilter', 1, 'Slot 1 Pre-Filter', 'Jobs/Economy slot eligibility check', 'gemini-3-flash-preview', 0.3, 1, true),
    ('slot_2_prefilter', 1, 'Slot 2 Pre-Filter', 'Tier 1 AI slot eligibility check', 'gemini-3-flash-preview', 0.3, 2, true),
    ('slot_3_prefilter', 1, 'Slot 3 Pre-Filter', 'Industry Verticals slot eligibility check', 'gemini-3-flash-preview', 0.3, 3, true),
    ('slot_4_prefilter', 1, 'Slot 4 Pre-Filter', 'Emerging Tech slot eligibility check', 'gemini-3-flash-preview', 0.3, 4, true),
    ('slot_5_prefilter', 1, 'Slot 5 Pre-Filter', 'Consumer AI slot eligibility check', 'gemini-3-flash-preview', 0.3, 5, true)
ON CONFLICT (prompt_key) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    model = EXCLUDED.model,
    temperature = EXCLUDED.temperature,
    updated_at = NOW();

-- Insert pre-filter prompt content
SELECT update_prompt_content(
    'slot_1_prefilter',
    E'Analyze this news article and determine which newsletter slots it''s eligible for.

ARTICLE:
Headline: {headline}
Summary: {content}
Published: {date_published}
Hours Old: {hours_ago}
Source: {source}
Source Credibility: {credibility}/5

SLOT CRITERIA:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_2_prefilter',
    E'Analyze this news article and determine which newsletter slots it''s eligible for.

ARTICLE:
Headline: {headline}
Summary: {content}
Published: {date_published}
Hours Old: {hours_ago}
Source: {source}
Source Credibility: {credibility}/5

SLOT CRITERIA:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 2,
  "reasoning": "Brief explanation"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_3_prefilter',
    E'Analyze this news article and determine which newsletter slots it''s eligible for.

ARTICLE:
Headline: {headline}
Summary: {content}
Published: {date_published}
Hours Old: {hours_ago}
Source: {source}
Source Credibility: {credibility}/5

SLOT CRITERIA:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 3,
  "reasoning": "Brief explanation"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_4_prefilter',
    E'Analyze this news article and determine which newsletter slots it''s eligible for.

ARTICLE:
Headline: {headline}
Summary: {content}
Published: {date_published}
Hours Old: {hours_ago}
Source: {source}
Source Credibility: {credibility}/5

SLOT CRITERIA:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 4,
  "reasoning": "Brief explanation"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_5_prefilter',
    E'Analyze this news article and determine which newsletter slots it''s eligible for.

ARTICLE:
Headline: {headline}
Summary: {content}
Published: {date_published}
Hours Old: {hours_ago}
Source: {source}
Source Credibility: {credibility}/5

SLOT CRITERIA:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

Return JSON only:
{{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 5,
  "reasoning": "Brief explanation"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

-- ============================================================================
-- STEP 2: SLOT SELECTION PROMPTS (Claude Sonnet)
-- ============================================================================

INSERT INTO system_prompts (prompt_key, step_id, name, description, model, temperature, slot_number, is_active)
VALUES
    ('slot_1_agent', 2, 'Slot 1 Selection Agent', 'Select lead story for Jobs/Economy', 'claude-sonnet-4-5-20250929', 0.7, 1, true),
    ('slot_2_agent', 2, 'Slot 2 Selection Agent', 'Select story for Tier 1 AI', 'claude-sonnet-4-5-20250929', 0.7, 2, true),
    ('slot_3_agent', 2, 'Slot 3 Selection Agent', 'Select story for Industry Verticals', 'claude-sonnet-4-5-20250929', 0.7, 3, true),
    ('slot_4_agent', 2, 'Slot 4 Selection Agent', 'Select story for Emerging Tech', 'claude-sonnet-4-5-20250929', 0.7, 4, true),
    ('slot_5_agent', 2, 'Slot 5 Selection Agent', 'Select story for Consumer AI', 'claude-sonnet-4-5-20250929', 0.7, 5, true),
    ('subject_line', 2, 'Subject Line Generator', 'Generate email subject line', 'claude-sonnet-4-5-20250929', 0.8, NULL, true)
ON CONFLICT (prompt_key) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    model = EXCLUDED.model,
    temperature = EXCLUDED.temperature,
    updated_at = NOW();

SELECT update_prompt_content(
    'slot_1_agent',
    E'You are selecting the lead story for Slot 1 of the Pivot 5 AI newsletter.

SLOT 1 FOCUS: AI impact on JOBS, ECONOMY, and MARKETS
- Employment disruption or creation
- Stock market movements related to AI
- Economic policy and AI
- Workforce transformation
- Broad societal/economic impact

CANDIDATE STORIES:
{candidates}

ALREADY SELECTED FOR OTHER SLOTS:
- Story IDs: {selected_stories}
- Companies: {selected_companies}
- Sources: {selected_sources}

YESTERDAY''S SLOT 1: {yesterday_slot}
(Avoid similar topics or sources)

SELECTION RULES:
1. Cannot select a story already chosen for another slot
2. Avoid repeating the same company twice in one issue
3. Maximum 2 stories from the same source per issue
4. Must be <24 hours old for Slot 1

Select the BEST story for Slot 1.

Return JSON only:
{{
  "selected_story_id": "the storyID of your selection",
  "company": "Company name if applicable",
  "reasoning": "Brief explanation of why this story was selected"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_2_agent',
    E'You are selecting the story for Slot 2 of the Pivot 5 AI newsletter.

SLOT 2 FOCUS: TIER 1 AI COMPANIES + RESEARCH
- OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI
- Major research breakthroughs
- Product announcements from major players

CANDIDATE STORIES:
{candidates}

ALREADY SELECTED FOR OTHER SLOTS:
- Story IDs: {selected_stories}
- Companies: {selected_companies}
- Sources: {selected_sources}

YESTERDAY''S SLOT 2: {yesterday_slot}
(Avoid similar topics or sources)

SELECTION RULES:
1. Cannot select a story already chosen for another slot
2. Avoid repeating the same company twice in one issue
3. Maximum 2 stories from the same source per issue
4. Can be 24-48 hours old for Slot 2

Select the BEST story for Slot 2.

Return JSON only:
{{
  "selected_story_id": "the storyID of your selection",
  "company": "Company name if applicable",
  "reasoning": "Brief explanation of why this story was selected"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_3_agent',
    E'You are selecting the story for Slot 3 of the Pivot 5 AI newsletter.

SLOT 3 FOCUS: INDUSTRY-SPECIFIC AI APPLICATIONS
- Healthcare, Government, Education, Legal
- Accounting, Retail, Cybersecurity
- Transportation, Manufacturing, Real Estate
- Agriculture, Energy

CANDIDATE STORIES:
{candidates}

ALREADY SELECTED FOR OTHER SLOTS:
- Story IDs: {selected_stories}
- Companies: {selected_companies}
- Sources: {selected_sources}

YESTERDAY''S SLOT 3: {yesterday_slot}
(Avoid similar industries or sources)

SELECTION RULES:
1. Cannot select a story already chosen for another slot
2. Avoid repeating the same company twice in one issue
3. Maximum 2 stories from the same source per issue
4. Try to pick a different industry than yesterday
5. Can be up to 7 days old for Slot 3

Select the BEST story for Slot 3.

Return JSON only:
{{
  "selected_story_id": "the storyID of your selection",
  "company": "Company name if applicable",
  "industry": "Industry sector",
  "reasoning": "Brief explanation of why this story was selected"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_4_agent',
    E'You are selecting the story for Slot 4 of the Pivot 5 AI newsletter.

SLOT 4 FOCUS: EMERGING COMPANIES
- Startups and new entrants
- Product launches
- Funding rounds and acquisitions
- New AI tools and applications

CANDIDATE STORIES:
{candidates}

ALREADY SELECTED FOR OTHER SLOTS:
- Story IDs: {selected_stories}
- Companies: {selected_companies}
- Sources: {selected_sources}

YESTERDAY''S SLOT 4: {yesterday_slot}
(Avoid similar companies or themes)

SELECTION RULES:
1. Cannot select a story already chosen for another slot
2. Avoid repeating the same company twice in one issue
3. Maximum 2 stories from the same source per issue
4. Must be <48 hours old for Slot 4

Select the BEST story for Slot 4.

Return JSON only:
{{
  "selected_story_id": "the storyID of your selection",
  "company": "Company name if applicable",
  "reasoning": "Brief explanation of why this story was selected"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'slot_5_agent',
    E'You are selecting the story for Slot 5 of the Pivot 5 AI newsletter.

SLOT 5 FOCUS: CONSUMER AI / HUMAN INTEREST
- AI ethics and societal debates
- Entertainment and lifestyle applications
- Fun, quirky, or surprising AI uses
- Human interest stories about AI

CANDIDATE STORIES:
{candidates}

ALREADY SELECTED FOR OTHER SLOTS:
- Story IDs: {selected_stories}
- Companies: {selected_companies}
- Sources: {selected_sources}

YESTERDAY''S SLOT 5: {yesterday_slot}
(Avoid similar themes)

SELECTION RULES:
1. Cannot select a story already chosen for another slot
2. Avoid repeating the same company twice in one issue
3. Maximum 2 stories from the same source per issue
4. Can be up to 7 days old for Slot 5
5. Should end newsletter on an engaging note

Select the BEST story for Slot 5.

Return JSON only:
{{
  "selected_story_id": "the storyID of your selection",
  "company": "Company name if applicable",
  "reasoning": "Brief explanation of why this story was selected"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'subject_line',
    E'Generate a compelling email subject line for today''s Pivot 5 AI newsletter.

TODAY''S STORIES:
Slot 1 (Lead): {slot1_headline}
Slot 2 (Tier 1): {slot2_headline}
Slot 3 (Industry): {slot3_headline}
Slot 4 (Emerging): {slot4_headline}
Slot 5 (Consumer): {slot5_headline}

GUIDELINES:
- Maximum 50 characters
- Create urgency or curiosity
- Reference the most impactful story
- Avoid clickbait but be compelling
- Use title case

RECENT SUBJECT LINES (avoid similar patterns):
{recent_subject_lines}

Return JSON only:
{{
  "subject_line": "Your Subject Line Here",
  "reasoning": "Why this subject line works"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

-- ============================================================================
-- STEP 3: DECORATION PROMPTS (Claude + Gemini)
-- ============================================================================

INSERT INTO system_prompts (prompt_key, step_id, name, description, model, temperature, slot_number, is_active)
VALUES
    ('content_cleaner', 3, 'Content Cleaner', 'Clean article content', 'gemini-2.0-flash-exp', 0.2, NULL, true),
    ('headline_generator', 3, 'Headline Generator', 'Generate newsletter headline', 'claude-sonnet-4-5-20250929', 0.7, NULL, true),
    ('bullet_generator', 3, 'Bullet Point Generator', 'Generate 3 bullet points', 'claude-sonnet-4-5-20250929', 0.7, NULL, true),
    ('bold_formatter', 3, 'Bold Formatter', 'Apply bold formatting', 'claude-sonnet-4-5-20250929', 0.3, NULL, true),
    ('image_prompt', 3, 'Image Prompt Generator', 'Generate image prompt', 'claude-sonnet-4-5-20250929', 0.8, NULL, true),
    ('image_generator', 3, 'Image Generator', 'Generate newsletter image', 'gemini-imagen', 0.7, NULL, true)
ON CONFLICT (prompt_key) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    model = EXCLUDED.model,
    temperature = EXCLUDED.temperature,
    updated_at = NOW();

SELECT update_prompt_content(
    'content_cleaner',
    E'Clean this article content by removing:
- Advertisements and promotional content
- Navigation elements and menu items
- Social media buttons and sharing links
- Cookie notices and popups
- Subscription prompts
- Author bios (keep byline only)
- Related article links
- Comments sections

ORIGINAL CONTENT:
{raw_content}

Return the cleaned article text only, preserving:
- Headline
- Byline
- Publication date
- Main article body
- Relevant quotes
- Key statistics',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'headline_generator',
    E'Generate a punchy, engaging headline for this newsletter story.

ORIGINAL HEADLINE: {original_headline}
ARTICLE SUMMARY: {summary}
SLOT: {slot_number} ({slot_focus})

GUIDELINES:
- Use Title Case
- Maximum 10 words
- Be specific and concrete
- Create interest without clickbait
- Match the tone of Pivot 5 (professional but accessible)

Return JSON only:
{{
  "headline": "Your Headline Here",
  "reasoning": "Why this headline works"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'bullet_generator',
    E'Generate 3 informative bullet points summarizing this article for the newsletter.

HEADLINE: {headline}
ARTICLE CONTENT: {content}

GUIDELINES:
- Each bullet should be 1-2 sentences
- Start with action verbs or key facts
- Cover the most important information
- Be specific with numbers and names
- Third bullet can include context or implications

Return JSON only:
{{
  "bullets": [
    "First bullet point...",
    "Second bullet point...",
    "Third bullet point..."
  ]
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'bold_formatter',
    E'Apply markdown bold formatting to key phrases in these bullet points.

BULLETS:
{bullets}

GUIDELINES:
- Bold 1-2 key phrases per bullet (not full sentences)
- Bold: company names, numbers/statistics, key terms
- Don''t bold: common words, entire sentences
- Use **text** markdown syntax

Return JSON only:
{{
  "formatted_bullets": [
    "Bullet with **key phrase** bolded...",
    "Another bullet with **important stat** highlighted...",
    "Third bullet with **company name** emphasized..."
  ]
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'image_prompt',
    E'Generate an image prompt for this newsletter story.

HEADLINE: {headline}
SUMMARY: {summary}
SLOT: {slot_number}

STYLE GUIDELINES:
- Professional, modern aesthetic
- Clean composition with single focal point
- Avoid text in the image
- Abstract or conceptual representations work well
- Blue, purple, and teal color palette preferred
- Suitable for business newsletter

Return JSON only:
{{
  "image_prompt": "Detailed description for image generation...",
  "style_notes": "Additional style guidance"
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

SELECT update_prompt_content(
    'image_generator',
    E'{image_prompt}

Style: Professional newsletter illustration, clean modern design, suitable for business audience.',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

-- ============================================================================
-- STEP 4: HTML COMPILE PROMPTS
-- ============================================================================

INSERT INTO system_prompts (prompt_key, step_id, name, description, model, temperature, slot_number, is_active)
VALUES
    ('summary_generator', 4, 'Summary Generator', 'Generate 15-word newsletter summary', 'claude-sonnet-4-5-20250929', 0.7, NULL, true)
ON CONFLICT (prompt_key) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    model = EXCLUDED.model,
    temperature = EXCLUDED.temperature,
    updated_at = NOW();

SELECT update_prompt_content(
    'summary_generator',
    E'Generate a 15-word summary of today''s newsletter for the email preview text.

TODAY''S STORIES:
1. {slot1_headline}
2. {slot2_headline}
3. {slot3_headline}
4. {slot4_headline}
5. {slot5_headline}

GUIDELINES:
- Exactly 15 words
- Mention 1-2 key stories
- Create interest to open the email
- Professional tone

Return JSON only:
{{
  "summary": "Your 15-word summary here..."
}}',
    NULL,
    'system@aieeditor.com',
    'Initial seed with Python variable syntax'
);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify all prompts are present
SELECT
    prompt_key,
    step_id,
    name,
    model,
    (SELECT version FROM system_prompt_versions WHERE prompt_id = sp.id AND is_current = true) as version
FROM system_prompts sp
WHERE is_active = true
ORDER BY step_id, slot_number NULLS LAST;
