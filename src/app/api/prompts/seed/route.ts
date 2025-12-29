import { NextRequest, NextResponse } from "next/server";
import { Pool } from "pg";

/**
 * POST /api/prompts/seed
 *
 * Seeds the database with all 17 system prompts using Python variable syntax.
 * This endpoint is called during deployment to ensure prompts are up-to-date.
 *
 * IMPORTANT: Prompts use Python f-string variable syntax:
 *   {variable}  - Will be substituted by Python workers
 *   {{          - Literal opening brace (for JSON output)
 *   }}          - Literal closing brace (for JSON output)
 */

// All prompt definitions with correct Python variable syntax
const PROMPTS = {
  // Step 1: Pre-Filter (Gemini)
  slot_1_prefilter: {
    stepId: 1,
    slotNumber: 1,
    name: "Slot 1 Pre-Filter",
    description: "Jobs/Economy slot eligibility check",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    content: `Analyze this news article and determine which newsletter slots it's eligible for.

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
}}`,
  },

  slot_2_prefilter: {
    stepId: 1,
    slotNumber: 2,
    name: "Slot 2 Pre-Filter",
    description: "Tier 1 AI slot eligibility check",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    content: `Analyze this news article and determine which newsletter slots it's eligible for.

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
}}`,
  },

  slot_3_prefilter: {
    stepId: 1,
    slotNumber: 3,
    name: "Slot 3 Pre-Filter",
    description: "Industry Verticals slot eligibility check",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    content: `Analyze this news article and determine which newsletter slots it's eligible for.

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
}}`,
  },

  slot_4_prefilter: {
    stepId: 1,
    slotNumber: 4,
    name: "Slot 4 Pre-Filter",
    description: "Emerging Tech slot eligibility check",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    content: `Analyze this news article and determine which newsletter slots it's eligible for.

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
}}`,
  },

  slot_5_prefilter: {
    stepId: 1,
    slotNumber: 5,
    name: "Slot 5 Pre-Filter",
    description: "Consumer AI slot eligibility check",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    content: `Analyze this news article and determine which newsletter slots it's eligible for.

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
}}`,
  },

  // Step 2: Slot Selection (Claude)
  slot_1_agent: {
    stepId: 2,
    slotNumber: 1,
    name: "Slot 1 Selection Agent",
    description: "Select lead story for Jobs/Economy",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `You are selecting the lead story for Slot 1 of the Pivot 5 AI newsletter.

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

YESTERDAY'S SLOT 1: {yesterday_slot}
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
}}`,
  },

  slot_2_agent: {
    stepId: 2,
    slotNumber: 2,
    name: "Slot 2 Selection Agent",
    description: "Select story for Tier 1 AI",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `You are selecting the story for Slot 2 of the Pivot 5 AI newsletter.

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

YESTERDAY'S SLOT 2: {yesterday_slot}
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
}}`,
  },

  slot_3_agent: {
    stepId: 2,
    slotNumber: 3,
    name: "Slot 3 Selection Agent",
    description: "Select story for Industry Verticals",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `You are selecting the story for Slot 3 of the Pivot 5 AI newsletter.

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

YESTERDAY'S SLOT 3: {yesterday_slot}
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
}}`,
  },

  slot_4_agent: {
    stepId: 2,
    slotNumber: 4,
    name: "Slot 4 Selection Agent",
    description: "Select story for Emerging Tech",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `You are selecting the story for Slot 4 of the Pivot 5 AI newsletter.

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

YESTERDAY'S SLOT 4: {yesterday_slot}
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
}}`,
  },

  slot_5_agent: {
    stepId: 2,
    slotNumber: 5,
    name: "Slot 5 Selection Agent",
    description: "Select story for Consumer AI",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `You are selecting the story for Slot 5 of the Pivot 5 AI newsletter.

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

YESTERDAY'S SLOT 5: {yesterday_slot}
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
}}`,
  },

  subject_line: {
    stepId: 2,
    slotNumber: null,
    name: "Subject Line Generator",
    description: "Generate email subject line",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.8,
    content: `Generate a compelling email subject line for today's Pivot 5 AI newsletter.

TODAY'S STORIES:
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
}}`,
  },

  // Step 3: Decoration (Claude + Gemini)
  content_cleaner: {
    stepId: 3,
    slotNumber: null,
    name: "Content Cleaner",
    description: "Clean article content",
    model: "gemini-3-flash-preview",
    temperature: 0.2,
    content: `Clean this article content by removing:
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
- Key statistics`,
  },

  headline_generator: {
    stepId: 3,
    slotNumber: null,
    name: "Headline Generator",
    description: "Generate newsletter headline",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `Generate a punchy, engaging headline for this newsletter story.

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
}}`,
  },

  bullet_generator: {
    stepId: 3,
    slotNumber: null,
    name: "Bullet Point Generator",
    description: "Generate 3 bullet points",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `Generate 3 informative bullet points summarizing this article for the newsletter.

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
}}`,
  },

  bold_formatter: {
    stepId: 3,
    slotNumber: null,
    name: "Bold Formatter",
    description: "Apply bold formatting",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.3,
    content: `Apply markdown bold formatting to key phrases in these bullet points.

BULLETS:
{bullets}

GUIDELINES:
- Bold 1-2 key phrases per bullet (not full sentences)
- Bold: company names, numbers/statistics, key terms
- Don't bold: common words, entire sentences
- Use **text** markdown syntax

Return JSON only:
{{
  "formatted_bullets": [
    "Bullet with **key phrase** bolded...",
    "Another bullet with **important stat** highlighted...",
    "Third bullet with **company name** emphasized..."
  ]
}}`,
  },

  image_prompt: {
    stepId: 3,
    slotNumber: null,
    name: "Image Prompt Generator",
    description: "Generate image prompt",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.8,
    content: `Generate an image prompt for this newsletter story.

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
}}`,
  },

  image_generator: {
    stepId: 3,
    slotNumber: null,
    name: "Image Generator",
    description: "Generate newsletter image",
    model: "gemini-imagen",
    temperature: 0.7,
    content: `{image_prompt}

Style: Professional newsletter illustration, clean modern design, suitable for business audience.`,
  },

  // Step 4: HTML Compile
  summary_generator: {
    stepId: 4,
    slotNumber: null,
    name: "Summary Generator",
    description: "Generate 15-word newsletter summary",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    content: `Generate a 15-word summary of today's newsletter for the email preview text.

TODAY'S STORIES:
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
}}`,
  },
};

async function seedPrompts(pool: Pool) {
  const results: { prompt_key: string; status: string; version?: number }[] = [];

  for (const [promptKey, config] of Object.entries(PROMPTS)) {
    try {
      // Upsert prompt metadata
      await pool.query(
        `INSERT INTO system_prompts (prompt_key, step_id, name, description, model, temperature, slot_number, is_active)
         VALUES ($1, $2, $3, $4, $5, $6, $7, true)
         ON CONFLICT (prompt_key) DO UPDATE SET
           name = EXCLUDED.name,
           description = EXCLUDED.description,
           model = EXCLUDED.model,
           temperature = EXCLUDED.temperature,
           slot_number = EXCLUDED.slot_number,
           updated_at = NOW()`,
        [
          promptKey,
          config.stepId,
          config.name,
          config.description,
          config.model,
          config.temperature,
          config.slotNumber,
        ]
      );

      // Get prompt ID
      const promptResult = await pool.query(
        `SELECT id FROM system_prompts WHERE prompt_key = $1`,
        [promptKey]
      );
      const promptId = promptResult.rows[0]?.id;

      if (!promptId) {
        throw new Error(`Failed to get prompt ID for ${promptKey}`);
      }

      // Get current version
      const versionResult = await pool.query(
        `SELECT COALESCE(MAX(version), 0) as max_version FROM system_prompt_versions WHERE prompt_id = $1`,
        [promptId]
      );
      const currentVersion = versionResult.rows[0]?.max_version || 0;
      const newVersion = currentVersion + 1;

      // Mark old versions as not current
      await pool.query(
        `UPDATE system_prompt_versions SET is_current = false WHERE prompt_id = $1 AND is_current = true`,
        [promptId]
      );

      // Insert new version
      await pool.query(
        `INSERT INTO system_prompt_versions (prompt_id, version, content, change_summary, created_by_email, is_current)
         VALUES ($1, $2, $3, $4, $5, true)`,
        [
          promptId,
          newVersion,
          config.content,
          "Seeded with Python variable syntax",
          "system@aieditor.com",
        ]
      );

      results.push({ prompt_key: promptKey, status: "success", version: newVersion });
    } catch (error) {
      console.error(`Error seeding prompt ${promptKey}:`, error);
      results.push({
        prompt_key: promptKey,
        status: "error",
      });
    }
  }

  return results;
}

export async function POST(request: NextRequest) {
  // Verify authorization (optional: add API key check)
  const authHeader = request.headers.get("authorization");
  const expectedKey = process.env.SEED_API_KEY || "seed-prompts-2024";

  if (authHeader !== `Bearer ${expectedKey}`) {
    return NextResponse.json(
      { error: "Unauthorized" },
      { status: 401 }
    );
  }

  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    return NextResponse.json(
      { error: "DATABASE_URL not configured" },
      { status: 500 }
    );
  }

  const pool = new Pool({
    connectionString: databaseUrl,
    ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : undefined,
  });

  try {
    const results = await seedPrompts(pool);

    const successful = results.filter((r) => r.status === "success").length;
    const failed = results.filter((r) => r.status === "error").length;

    return NextResponse.json({
      success: true,
      message: `Seeded ${successful} prompts (${failed} failed)`,
      results,
    });
  } catch (error) {
    console.error("Error seeding prompts:", error);
    return NextResponse.json(
      { error: "Failed to seed prompts", details: String(error) },
      { status: 500 }
    );
  } finally {
    await pool.end();
  }
}

// GET to check status
export async function GET() {
  return NextResponse.json({
    endpoint: "/api/prompts/seed",
    method: "POST",
    description: "Seeds all 17 system prompts with Python variable syntax",
    promptCount: Object.keys(PROMPTS).length,
    prompts: Object.keys(PROMPTS),
  });
}
