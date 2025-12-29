import { NextRequest, NextResponse } from "next/server";
import { Pool } from "pg";

// This endpoint initializes the database schema and seeds the prompts
// Run once: GET /api/setup?secret=YOUR_SECRET

const SETUP_SECRET = process.env.SETUP_SECRET || "pivot5-setup-2024";

// Initial prompts from n8n workflows
const INITIAL_PROMPTS = [
  // Step 1: Pre-Filter (all 5 slots use same base prompt)
  {
    prompt_key: "slot_1_prefilter",
    step_id: 1,
    name: "Slot 1 Pre-Filter",
    description: "Jobs/Economy pre-filter using Gemini",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    slot_number: 1,
    content: `You are a newsletter editor for Pivot 5, a daily AI newsletter.

Analyze this article and determine which newsletter slots (1-5) it is eligible for:

HEADLINE: {{ headline }}
DEK: {{ dek }}
SOURCE: {{ source }} (credibility: {{ credibilityScore }}/5)
AGE: {{ hoursAgo }} hours ago
TOPIC: {{ topic }}

SLOT DEFINITIONS:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: News about OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: AI in Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

YESTERDAY'S HEADLINES (avoid similar topics):
{{ yesterdayHeadlines }}

Return JSON only:
{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "slot_2_prefilter",
    step_id: 1,
    name: "Slot 2 Pre-Filter",
    description: "Tier 1 AI pre-filter using Gemini",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    slot_number: 2,
    content: `You are a newsletter editor for Pivot 5, a daily AI newsletter.

Analyze this article and determine which newsletter slots (1-5) it is eligible for:

HEADLINE: {{ headline }}
DEK: {{ dek }}
SOURCE: {{ source }} (credibility: {{ credibilityScore }}/5)
AGE: {{ hoursAgo }} hours ago
TOPIC: {{ topic }}

SLOT DEFINITIONS:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: News about OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: AI in Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

YESTERDAY'S HEADLINES (avoid similar topics):
{{ yesterdayHeadlines }}

Return JSON only:
{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "slot_3_prefilter",
    step_id: 1,
    name: "Slot 3 Pre-Filter",
    description: "Industry Impact pre-filter using Gemini",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    slot_number: 3,
    content: `You are a newsletter editor for Pivot 5, a daily AI newsletter.

Analyze this article and determine which newsletter slots (1-5) it is eligible for:

HEADLINE: {{ headline }}
DEK: {{ dek }}
SOURCE: {{ source }} (credibility: {{ credibilityScore }}/5)
AGE: {{ hoursAgo }} hours ago
TOPIC: {{ topic }}

SLOT DEFINITIONS:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: News about OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: AI in Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

YESTERDAY'S HEADLINES (avoid similar topics):
{{ yesterdayHeadlines }}

Return JSON only:
{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "slot_4_prefilter",
    step_id: 1,
    name: "Slot 4 Pre-Filter",
    description: "Emerging Companies pre-filter using Gemini",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    slot_number: 4,
    content: `You are a newsletter editor for Pivot 5, a daily AI newsletter.

Analyze this article and determine which newsletter slots (1-5) it is eligible for:

HEADLINE: {{ headline }}
DEK: {{ dek }}
SOURCE: {{ source }} (credibility: {{ credibilityScore }}/5)
AGE: {{ hoursAgo }} hours ago
TOPIC: {{ topic }}

SLOT DEFINITIONS:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: News about OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: AI in Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

YESTERDAY'S HEADLINES (avoid similar topics):
{{ yesterdayHeadlines }}

Return JSON only:
{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "slot_5_prefilter",
    step_id: 1,
    name: "Slot 5 Pre-Filter",
    description: "Consumer AI pre-filter using Gemini",
    model: "gemini-3-flash-preview",
    temperature: 0.3,
    slot_number: 5,
    content: `You are a newsletter editor for Pivot 5, a daily AI newsletter.

Analyze this article and determine which newsletter slots (1-5) it is eligible for:

HEADLINE: {{ headline }}
DEK: {{ dek }}
SOURCE: {{ source }} (credibility: {{ credibilityScore }}/5)
AGE: {{ hoursAgo }} hours ago
TOPIC: {{ topic }}

SLOT DEFINITIONS:
1. JOBS/ECONOMY: AI impact on employment, workforce, stock market, broad economic impact. Must be <24 hours old.
2. TIER 1 AI: News about OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI. Research breakthroughs. Can be 24-48 hours old.
3. INDUSTRY IMPACT: AI in Healthcare, Government, Education, Legal, Accounting, Retail, Cybersecurity, Transportation, Manufacturing, Real Estate, Agriculture, Energy. Can be up to 7 days old.
4. EMERGING COMPANIES: Startups, product launches, funding rounds, acquisitions, new AI tools. Must be <48 hours old.
5. CONSUMER AI: Ethics, entertainment, lifestyle, societal impact, fun/quirky uses. Can be up to 7 days old.

YESTERDAY'S HEADLINES (avoid similar topics):
{{ yesterdayHeadlines }}

Return JSON only:
{
  "eligible_slots": [1, 2, ...],
  "primary_slot": 1,
  "reasoning": "Brief explanation"
}`,
  },
  // Step 2: Slot Selection Agents
  {
    prompt_key: "slot_1_agent",
    step_id: 2,
    name: "Slot 1 Selection Agent",
    description: "Selects best Jobs/Economy story using Claude",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: 1,
    content: `You are selecting the lead story for Slot 1 of the Pivot 5 AI newsletter.

SLOT 1 FOCUS: AI impact on JOBS, ECONOMY, and MARKETS
- Employment disruption or creation
- Stock market movements related to AI
- Economic policy and AI
- Workforce transformation
- Broad societal/economic impact

CANDIDATES:
{{ candidates }}

YESTERDAY'S SLOT 1: {{ yesterdaySlot1 }}
(Avoid similar topics or sources)

Select the BEST story for Slot 1. Consider:
1. Freshness (must be <24 hours old)
2. Source credibility score
3. Headline impact and reader interest
4. Differentiation from yesterday

Return JSON:
{
  "selected_story_id": "...",
  "reasoning": "Brief explanation of why this story was selected"
}`,
  },
  {
    prompt_key: "slot_2_agent",
    step_id: 2,
    name: "Slot 2 Selection Agent",
    description: "Selects best Tier 1 AI story using Claude",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: 2,
    content: `You are selecting the story for Slot 2 of the Pivot 5 AI newsletter.

SLOT 2 FOCUS: TIER 1 AI COMPANIES + RESEARCH
- OpenAI, Google/DeepMind, Meta AI, NVIDIA, Microsoft, Anthropic, xAI, Amazon AWS AI
- Major research breakthroughs
- Product announcements from major players

CANDIDATES:
{{ candidates }}

ALREADY SELECTED: {{ selectedStories }}
(Cannot reuse these stories)

YESTERDAY'S SLOT 2: {{ yesterdaySlot2 }}
(Avoid similar topics or sources)

Select the BEST story for Slot 2. Consider:
1. Tier 1 company relevance
2. Freshness (can be 24-48 hours old)
3. Source credibility
4. Differentiation from selected stories and yesterday

Return JSON:
{
  "selected_story_id": "...",
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "slot_3_agent",
    step_id: 2,
    name: "Slot 3 Selection Agent",
    description: "Selects best Industry Impact story using Claude",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: 3,
    content: `You are selecting the story for Slot 3 of the Pivot 5 AI newsletter.

SLOT 3 FOCUS: INDUSTRY-SPECIFIC AI APPLICATIONS
- Healthcare, Government, Education, Legal
- Accounting, Retail, Cybersecurity
- Transportation, Manufacturing, Real Estate
- Agriculture, Energy

CANDIDATES:
{{ candidates }}

ALREADY SELECTED: {{ selectedStories }}
(Cannot reuse these stories)

YESTERDAY'S SLOT 3: {{ yesterdaySlot3 }}
(Avoid similar industries or sources)

Select the BEST story for Slot 3. Consider:
1. Clear industry application
2. Can be up to 7 days old
3. Source credibility
4. Different industry than yesterday if possible

Return JSON:
{
  "selected_story_id": "...",
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "slot_4_agent",
    step_id: 2,
    name: "Slot 4 Selection Agent",
    description: "Selects best Emerging Companies story using Claude",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: 4,
    content: `You are selecting the story for Slot 4 of the Pivot 5 AI newsletter.

SLOT 4 FOCUS: EMERGING COMPANIES
- Startups and new entrants
- Product launches
- Funding rounds and acquisitions
- New AI tools and applications

CANDIDATES:
{{ candidates }}

ALREADY SELECTED: {{ selectedStories }}
(Cannot reuse these stories)

YESTERDAY'S SLOT 4: {{ yesterdaySlot4 }}
(Avoid similar companies or themes)

Select the BEST story for Slot 4. Consider:
1. Fresh, exciting company news
2. Must be <48 hours old
3. Source credibility
4. Interesting angle for readers

Return JSON:
{
  "selected_story_id": "...",
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "slot_5_agent",
    step_id: 2,
    name: "Slot 5 Selection Agent",
    description: "Selects best Consumer AI story using Claude",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: 5,
    content: `You are selecting the story for Slot 5 of the Pivot 5 AI newsletter.

SLOT 5 FOCUS: CONSUMER AI / HUMAN INTEREST
- AI ethics and societal debates
- Entertainment and lifestyle applications
- Fun, quirky, or surprising AI uses
- Human interest stories about AI

CANDIDATES:
{{ candidates }}

ALREADY SELECTED: {{ selectedStories }}
(Cannot reuse these stories)

YESTERDAY'S SLOT 5: {{ yesterdaySlot5 }}
(Avoid similar themes)

Select the BEST story for Slot 5. Consider:
1. Reader engagement potential
2. Can be up to 7 days old
3. Unique or surprising angle
4. Good "end of newsletter" feel

Return JSON:
{
  "selected_story_id": "...",
  "reasoning": "Brief explanation"
}`,
  },
  {
    prompt_key: "subject_line",
    step_id: 2,
    name: "Subject Line Generator",
    description: "Generates email subject line using Claude",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.8,
    slot_number: null,
    content: `Generate a compelling email subject line for today's Pivot 5 AI newsletter.

TODAY'S STORIES:
Slot 1 (Lead): {{ slot1Headline }}
Slot 2 (Tier 1): {{ slot2Headline }}
Slot 3 (Industry): {{ slot3Headline }}
Slot 4 (Emerging): {{ slot4Headline }}
Slot 5 (Consumer): {{ slot5Headline }}

GUIDELINES:
- Maximum 50 characters
- Create urgency or curiosity
- Reference the most impactful story
- Avoid clickbait but be compelling
- Use title case

RECENT SUBJECT LINES (avoid similar patterns):
{{ recentSubjectLines }}

Return JSON:
{
  "subject_line": "Your Subject Line Here",
  "reasoning": "Why this subject line works"
}`,
  },
  // Step 3: Decoration Prompts
  {
    prompt_key: "content_cleaner",
    step_id: 3,
    name: "Content Cleaner",
    description: "Cleans article content for processing",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.3,
    slot_number: null,
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
{{ rawContent }}

Return the cleaned article text only, preserving:
- Headline
- Byline
- Publication date
- Main article body
- Relevant quotes
- Key statistics`,
  },
  {
    prompt_key: "headline_generator",
    step_id: 3,
    name: "Headline Generator",
    description: "Generates newsletter headlines using Claude",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: null,
    content: `Generate a punchy, engaging headline for this newsletter story.

ORIGINAL HEADLINE: {{ originalHeadline }}
ARTICLE SUMMARY: {{ summary }}
SLOT: {{ slotNumber }} ({{ slotFocus }})

GUIDELINES:
- Use Title Case
- Maximum 10 words
- Be specific and concrete
- Create interest without clickbait
- Match the tone of Pivot 5 (professional but accessible)

Return JSON:
{
  "headline": "Your Headline Here",
  "reasoning": "Why this headline works"
}`,
  },
  {
    prompt_key: "bullet_generator",
    step_id: 3,
    name: "Bullet Point Generator",
    description: "Generates 3 bullet points for each story",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: null,
    content: `Generate 3 informative bullet points summarizing this article for the newsletter.

HEADLINE: {{ headline }}
ARTICLE CONTENT: {{ content }}

GUIDELINES:
- Each bullet should be 1-2 sentences
- Start with action verbs or key facts
- Cover the most important information
- Be specific with numbers and names
- Third bullet can include context or implications

Return JSON:
{
  "bullets": [
    "First bullet point...",
    "Second bullet point...",
    "Third bullet point..."
  ]
}`,
  },
  {
    prompt_key: "bold_formatter",
    step_id: 3,
    name: "Bold Formatter",
    description: "Applies bold formatting to key phrases",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.3,
    slot_number: null,
    content: `Apply markdown bold formatting to key phrases in these bullet points.

BULLETS:
{{ bullets }}

GUIDELINES:
- Bold 1-2 key phrases per bullet (not full sentences)
- Bold: company names, numbers/statistics, key terms
- Don't bold: common words, entire sentences
- Use **text** markdown syntax

Return JSON:
{
  "formatted_bullets": [
    "Bullet with **key phrase** bolded...",
    "Another bullet with **important stat** highlighted...",
    "Third bullet with **company name** emphasized..."
  ]
}`,
  },
  {
    prompt_key: "image_prompt",
    step_id: 3,
    name: "Image Prompt Generator",
    description: "Generates image prompts for Gemini",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.8,
    slot_number: null,
    content: `Generate an image prompt for this newsletter story.

HEADLINE: {{ headline }}
SUMMARY: {{ summary }}
SLOT: {{ slotNumber }}

STYLE GUIDELINES:
- Professional, modern aesthetic
- Clean composition with single focal point
- Avoid text in the image
- Abstract or conceptual representations work well
- Blue, purple, and teal color palette preferred
- Suitable for business newsletter

Return JSON:
{
  "image_prompt": "Detailed description for image generation...",
  "style_notes": "Additional style guidance"
}`,
  },
  {
    prompt_key: "image_generator",
    step_id: 3,
    name: "Image Generator",
    description: "Generates images using Gemini",
    model: "gemini-2.0-flash",
    temperature: 0.9,
    slot_number: null,
    content: `{{ imagePrompt }}

Style: Professional newsletter illustration, clean modern design, suitable for business audience.`,
  },
  // Step 4: HTML Compile
  {
    prompt_key: "summary_generator",
    step_id: 4,
    name: "Newsletter Summary Generator",
    description: "Generates 15-word email preview text",
    model: "claude-sonnet-4-5-20250929",
    temperature: 0.7,
    slot_number: null,
    content: `Generate a 15-word summary of today's newsletter for the email preview text.

TODAY'S STORIES:
1. {{ slot1Headline }}
2. {{ slot2Headline }}
3. {{ slot3Headline }}
4. {{ slot4Headline }}
5. {{ slot5Headline }}

GUIDELINES:
- Exactly 15 words
- Mention 1-2 key stories
- Create interest to open the email
- Professional tone

Return JSON:
{
  "summary": "Your 15-word summary here..."
}`,
  },
];

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const secret = searchParams.get("secret");

  if (secret !== SETUP_SECRET) {
    return NextResponse.json({ error: "Invalid secret" }, { status: 401 });
  }

  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  });

  const results: string[] = [];

  try {
    const client = await pool.connect();

    try {
      // Step 1: Create extension
      await client.query('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"');
      results.push("✓ UUID extension enabled");

      // Step 2: Create system_prompts table
      await client.query(`
        CREATE TABLE IF NOT EXISTS system_prompts (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          prompt_key VARCHAR(100) UNIQUE NOT NULL,
          step_id INTEGER NOT NULL CHECK (step_id >= 1 AND step_id <= 5),
          name VARCHAR(255) NOT NULL,
          description TEXT,
          model VARCHAR(100) NOT NULL,
          temperature DECIMAL(3,2) DEFAULT 0.7,
          slot_number INTEGER CHECK (slot_number >= 1 AND slot_number <= 5),
          is_active BOOLEAN DEFAULT true,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `);
      results.push("✓ system_prompts table created");

      // Step 3: Create system_prompt_versions table
      await client.query(`
        CREATE TABLE IF NOT EXISTS system_prompt_versions (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          prompt_id UUID NOT NULL REFERENCES system_prompts(id) ON DELETE CASCADE,
          version INTEGER NOT NULL,
          content TEXT NOT NULL,
          change_summary TEXT,
          created_by UUID,
          created_by_email VARCHAR(255),
          is_current BOOLEAN DEFAULT false,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          UNIQUE(prompt_id, version)
        )
      `);
      results.push("✓ system_prompt_versions table created");

      // Step 4: Create indexes
      await client.query(`CREATE INDEX IF NOT EXISTS idx_prompts_step ON system_prompts(step_id)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_prompts_key ON system_prompts(prompt_key)`);
      await client.query(`CREATE INDEX IF NOT EXISTS idx_versions_prompt ON system_prompt_versions(prompt_id)`);
      results.push("✓ Indexes created");

      // Step 5: Create update_prompt_content function
      await client.query(`
        CREATE OR REPLACE FUNCTION update_prompt_content(
          p_prompt_key VARCHAR,
          p_content TEXT,
          p_user_id UUID DEFAULT NULL,
          p_user_email VARCHAR DEFAULT NULL,
          p_change_summary TEXT DEFAULT NULL
        ) RETURNS UUID AS $$
        DECLARE
          v_prompt_id UUID;
          v_current_version INTEGER;
          v_new_version_id UUID;
        BEGIN
          SELECT id INTO v_prompt_id FROM system_prompts WHERE prompt_key = p_prompt_key;
          IF v_prompt_id IS NULL THEN
            RAISE EXCEPTION 'Prompt not found: %', p_prompt_key;
          END IF;
          SELECT COALESCE(MAX(version), 0) INTO v_current_version
          FROM system_prompt_versions WHERE prompt_id = v_prompt_id;
          UPDATE system_prompt_versions
          SET is_current = false
          WHERE prompt_id = v_prompt_id AND is_current = true;
          INSERT INTO system_prompt_versions (
            prompt_id, version, content, change_summary,
            created_by, created_by_email, is_current
          ) VALUES (
            v_prompt_id, v_current_version + 1, p_content, p_change_summary,
            p_user_id, p_user_email, true
          ) RETURNING id INTO v_new_version_id;
          UPDATE system_prompts SET updated_at = NOW() WHERE id = v_prompt_id;
          RETURN v_new_version_id;
        END;
        $$ LANGUAGE plpgsql
      `);
      results.push("✓ update_prompt_content function created");

      // Step 6: Create rollback_prompt function
      await client.query(`
        CREATE OR REPLACE FUNCTION rollback_prompt(
          p_prompt_key VARCHAR,
          p_version INTEGER,
          p_user_id UUID DEFAULT NULL,
          p_user_email VARCHAR DEFAULT NULL
        ) RETURNS UUID AS $$
        DECLARE
          v_prompt_id UUID;
          v_old_content TEXT;
          v_new_version_id UUID;
        BEGIN
          SELECT id INTO v_prompt_id FROM system_prompts WHERE prompt_key = p_prompt_key;
          IF v_prompt_id IS NULL THEN
            RAISE EXCEPTION 'Prompt not found: %', p_prompt_key;
          END IF;
          SELECT content INTO v_old_content
          FROM system_prompt_versions
          WHERE prompt_id = v_prompt_id AND version = p_version;
          IF v_old_content IS NULL THEN
            RAISE EXCEPTION 'Version % not found for prompt %', p_version, p_prompt_key;
          END IF;
          SELECT update_prompt_content(
            p_prompt_key, v_old_content, p_user_id, p_user_email,
            'Rollback to version ' || p_version
          ) INTO v_new_version_id;
          RETURN v_new_version_id;
        END;
        $$ LANGUAGE plpgsql
      `);
      results.push("✓ rollback_prompt function created");

      // Step 7: Create audit_log table
      await client.query(`
        CREATE TABLE IF NOT EXISTS audit_log (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          action VARCHAR(100) NOT NULL,
          entity_type VARCHAR(100) NOT NULL,
          entity_id VARCHAR(255),
          details JSONB,
          user_email VARCHAR(255),
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `);
      results.push("✓ audit_log table created");

      // Step 8: Create jobs table
      await client.query(`
        CREATE TABLE IF NOT EXISTS jobs (
          id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
          job_type VARCHAR(100) NOT NULL,
          step_id INTEGER NOT NULL,
          status VARCHAR(50) DEFAULT 'pending',
          payload JSONB,
          result JSONB,
          error_message TEXT,
          created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
          updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
      `);
      results.push("✓ jobs table created");

      // Step 9: Seed prompts
      let seededCount = 0;
      for (const prompt of INITIAL_PROMPTS) {
        // Check if prompt already exists
        const existing = await client.query(
          "SELECT id FROM system_prompts WHERE prompt_key = $1",
          [prompt.prompt_key]
        );

        if (existing.rows.length === 0) {
          // Insert new prompt
          const insertResult = await client.query(
            `INSERT INTO system_prompts (prompt_key, step_id, name, description, model, temperature, slot_number)
             VALUES ($1, $2, $3, $4, $5, $6, $7)
             RETURNING id`,
            [
              prompt.prompt_key,
              prompt.step_id,
              prompt.name,
              prompt.description,
              prompt.model,
              prompt.temperature,
              prompt.slot_number,
            ]
          );

          // Insert initial version
          await client.query(
            `INSERT INTO system_prompt_versions (prompt_id, version, content, change_summary, is_current)
             VALUES ($1, 1, $2, 'Initial version from n8n migration', true)`,
            [insertResult.rows[0].id, prompt.content]
          );

          seededCount++;
        }
      }
      results.push(`✓ Seeded ${seededCount} prompts (${INITIAL_PROMPTS.length - seededCount} already existed)`);

      return NextResponse.json({
        success: true,
        message: "Database setup complete",
        results,
      });
    } finally {
      client.release();
    }
  } catch (error) {
    console.error("Setup error:", error);
    return NextResponse.json(
      {
        error: "Setup failed",
        details: error instanceof Error ? error.message : String(error),
        results,
      },
      { status: 500 }
    );
  } finally {
    await pool.end();
  }
}
