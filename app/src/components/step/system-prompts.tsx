"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { PromptConfig } from "@/lib/step-config";

// Dynamic import with SSR disabled - Monaco requires browser DOM
const PromptEditor = dynamic(
  () => import("@/components/ui/prompt-editor").then((mod) => mod.PromptEditor),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-64 rounded-md border bg-muted/30 flex items-center justify-center text-muted-foreground text-sm">
        Loading editor...
      </div>
    ),
  }
);

function MaterialIcon({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cn("material-symbols-outlined", className)}>
      {name}
    </span>
  );
}

interface SystemPromptsProps {
  stepId: number;
  prompts: PromptConfig[];
}

// Prompt content - in production this would come from PostgreSQL
const mockPromptContent: Record<string, string> = {
  // Step 1: Pre-Filter Prompts
  slot_1_prefilter: `You are an AI news editor for Pivot 5, a daily AI newsletter.

SLOT 1 CRITERIA:
- Focus: AI impact on jobs, economy, stock market, broad societal impact
- Freshness: Must be published within last 24 hours
- Priority: Major announcements affecting general public

Evaluate each article and return JSON:
{
  "eligible": true/false,
  "score": 1-10,
  "reason": "brief explanation"
}`,
  slot_2_prefilter: `You are an AI news editor for Pivot 5, a daily AI newsletter.

SLOT 2 CRITERIA:
- Focus: Tier 1 AI companies (OpenAI, Google, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon) + economic themes + research breakthroughs
- Freshness: Published within last 48 hours
- Priority: Research papers, major product launches, significant partnerships

Evaluate each article and return JSON:
{
  "eligible": true/false,
  "score": 1-10,
  "reason": "brief explanation"
}`,
  slot_3_prefilter: `You are an AI news editor for Pivot 5, a daily AI newsletter.

SLOT 3 CRITERIA:
- Focus: Industry-specific AI applications (healthcare, finance, legal, manufacturing, etc.)
- Freshness: Published within last 48 hours
- Priority: Real-world AI deployments, industry transformation stories

Evaluate each article and return JSON:
{
  "eligible": true/false,
  "score": 1-10,
  "reason": "brief explanation"
}`,
  slot_4_prefilter: `You are an AI news editor for Pivot 5, a daily AI newsletter.

SLOT 4 CRITERIA:
- Focus: Emerging AI companies, startups, funding rounds, new entrants
- Freshness: Published within last 48 hours
- Priority: Series A+ funding, notable product launches, acquisitions

Evaluate each article and return JSON:
{
  "eligible": true/false,
  "score": 1-10,
  "reason": "brief explanation"
}`,
  slot_5_prefilter: `You are an AI news editor for Pivot 5, a daily AI newsletter.

SLOT 5 CRITERIA:
- Focus: Consumer AI, human interest, AI in daily life, creative AI
- Freshness: Published within last 72 hours
- Priority: Stories with broad appeal, viral potential, relatable impact

Evaluate each article and return JSON:
{
  "eligible": true/false,
  "score": 1-10,
  "reason": "brief explanation"
}`,

  // Step 2: Slot Selection Agent Prompts
  slot_1_agent: `You are selecting the LEAD story for Pivot 5 AI newsletter.

SLOT 1 FOCUS: Macro AI impact - jobs, economy, markets, broad societal change

RULES:
1. Don't select stories covering same topics as yesterday
2. Slot 1 company can't repeat from yesterday's Slot 1
3. Prioritize highest source credibility scores
4. Look for stories with broad appeal and significant impact
5. Avoid overly technical or niche topics

Return your selection as JSON:
{
  "storyId": "selected story ID",
  "headline": "story headline",
  "reason": "why this story was selected"
}`,
  slot_2_agent: `You are selecting the SLOT 2 story for Pivot 5 AI newsletter.

SLOT 2 FOCUS: Tier 1 AI companies + research breakthroughs

TIER 1 COMPANIES: OpenAI, Google/DeepMind, Meta, NVIDIA, Microsoft, Anthropic, xAI, Amazon

RULES:
1. Story must feature a Tier 1 company OR major research breakthrough
2. Cannot repeat company from Slot 1
3. Cannot repeat same company from yesterday's Slot 2
4. Prioritize announcements, launches, partnerships over opinion pieces

Return your selection as JSON:
{
  "storyId": "selected story ID",
  "headline": "story headline",
  "reason": "why this story was selected"
}`,
  slot_3_agent: `You are selecting the SLOT 3 story for Pivot 5 AI newsletter.

SLOT 3 FOCUS: Industry-specific AI applications

TARGET INDUSTRIES: Healthcare, Finance, Legal, Manufacturing, Education, Retail, Transportation

RULES:
1. Must show real AI deployment or transformation in a specific industry
2. Cannot overlap with companies in Slots 1-2
3. Prioritize stories with measurable impact or ROI
4. Avoid vague "AI will revolutionize X" predictions

Return your selection as JSON:
{
  "storyId": "selected story ID",
  "headline": "story headline",
  "reason": "why this story was selected"
}`,
  slot_4_agent: `You are selecting the SLOT 4 story for Pivot 5 AI newsletter.

SLOT 4 FOCUS: Emerging companies and startups

CRITERIA:
- Series A or later funding rounds
- New product launches from emerging players
- Acquisitions of AI startups
- Notable pivot to AI by established companies

RULES:
1. Cannot feature Tier 1 companies (save for Slot 2)
2. Prioritize funding news with clear AI focus
3. Look for companies with traction, not just concepts

Return your selection as JSON:
{
  "storyId": "selected story ID",
  "headline": "story headline",
  "reason": "why this story was selected"
}`,
  slot_5_agent: `You are selecting the SLOT 5 story for Pivot 5 AI newsletter.

SLOT 5 FOCUS: Consumer AI and human interest

CRITERIA:
- AI tools everyday people use
- Creative AI applications
- Viral AI moments
- Human stories about AI impact
- AI in entertainment, art, music

RULES:
1. Should be the most accessible/relatable story of the 5
2. Can be lighter in tone than other slots
3. Good candidates: AI apps going viral, celebrity AI use, AI art controversies

Return your selection as JSON:
{
  "storyId": "selected story ID",
  "headline": "story headline",
  "reason": "why this story was selected"
}`,
  subject_line: `Generate a compelling email subject line for today's Pivot 5 newsletter.

GIVEN: The 5 headlines selected for today's newsletter

REQUIREMENTS:
- Maximum 60 characters (including spaces)
- Must reference the lead story (Slot 1) or most compelling story
- Use urgency without being clickbait
- Avoid: ALL CAPS, excessive punctuation, spam triggers

EXAMPLES OF GOOD SUBJECT LINES:
- "OpenAI's GPT-5 Changes Everything"
- "Why Goldman Sachs Just Hired 1,000 AI Engineers"
- "The AI Feature Apple Hid in iOS 18"

Return ONLY the subject line text, no quotes.`,

  // Step 3: Decoration Prompts
  content_cleaner: `Clean the following article content for newsletter processing.

REMOVE:
- Navigation elements
- Advertisement text
- Social sharing prompts
- Related article links
- Author bios and bylines
- Cookie consent notices
- Subscription prompts

PRESERVE:
- Main article text
- Relevant quotes
- Key statistics and data
- Company/product names

Return the cleaned content as plain text.`,
  headline_generator: `Generate a punchy, engaging headline for this newsletter story.

REQUIREMENTS:
- Title Case formatting
- Maximum 80 characters
- Punchy and attention-grabbing
- Avoid clickbait or sensationalism
- Accurately represent the story content

STYLE GUIDE:
- Use active voice
- Lead with the most newsworthy element
- Include company/product name when relevant
- Numbers are attention-grabbing when appropriate

Return ONLY the headline text, no quotes or explanation.`,
  bullet_generator: `Generate 3 informative bullet points for this newsletter story.

REQUIREMENTS:
- Each bullet is exactly 2 sentences
- Maximum 260 characters per bullet
- First bullet: Main announcement or news
- Second bullet: Key details and context
- Third bullet: Business impact or implications

STYLE GUIDE:
- Start each bullet with an action verb or key noun
- Include specific numbers, names, dates when available
- Avoid redundancy between bullets

Format:
• [Bullet 1]
• [Bullet 2]
• [Bullet 3]`,
  bold_formatter: `Apply markdown bold formatting to key phrases in these bullet points.

BOLD THESE ELEMENTS:
- Company names (first mention only)
- Product names
- Dollar amounts and percentages
- Key metrics and statistics
- Important dates or timeframes

DO NOT BOLD:
- Common words (the, a, is, are)
- Entire sentences
- More than 2-3 phrases per bullet

Return the bullets with **bold** markdown applied.`,
  image_prompt: `Generate an image prompt for an AI image generator.

CONTEXT: This image will accompany a newsletter story about AI/technology.

REQUIREMENTS:
- Photorealistic or high-quality editorial illustration style
- No text in the image
- Professional, editorial quality
- Relevant to the story topic
- Safe for work, no controversial imagery

FORMAT:
"[Style], [Subject], [Setting/Background], [Lighting], [Mood]"

EXAMPLE:
"Professional editorial photograph, modern office with holographic AI displays, warm ambient lighting, innovative and futuristic mood"

Return ONLY the image prompt, no quotes or explanation.`,
  image_generator: `Generate a newsletter header image based on the provided prompt.

TECHNICAL REQUIREMENTS:
- Aspect ratio: 16:9
- Resolution: 1200x675 minimum
- Style: Professional editorial
- No text overlays
- No watermarks

OUTPUT: Base64 encoded image or image URL`,

  // Step 4: HTML Compile Prompts
  summary_generator: `Generate a 15-word summary of today's newsletter for the email preheader.

GIVEN: The 5 headlines for today's newsletter

REQUIREMENTS:
- Exactly 15 words (no more, no less)
- Captures the theme or top story
- Compelling enough to encourage opens
- No emojis

Return ONLY the 15-word summary.`,
};

export function SystemPrompts({ stepId, prompts }: SystemPromptsProps) {
  const [expandedPrompts, setExpandedPrompts] = useState<Set<string>>(
    new Set([prompts[0]?.id])
  );
  const [editingPrompt, setEditingPrompt] = useState<string | null>(null);
  const [promptTexts, setPromptTexts] = useState<Record<string, string>>(mockPromptContent);
  const [hasChanges, setHasChanges] = useState<Set<string>>(new Set());

  const toggleExpand = (promptId: string) => {
    setExpandedPrompts((prev) => {
      const next = new Set(prev);
      if (next.has(promptId)) {
        next.delete(promptId);
      } else {
        next.add(promptId);
      }
      return next;
    });
  };

  const handleEdit = (promptId: string) => {
    setEditingPrompt(promptId);
    if (!expandedPrompts.has(promptId)) {
      setExpandedPrompts((prev) => new Set([...prev, promptId]));
    }
  };

  const handleSave = (promptId: string) => {
    setEditingPrompt(null);
    setHasChanges((prev) => {
      const next = new Set(prev);
      next.delete(promptId);
      return next;
    });
    // In production, this would call an API to save to PostgreSQL
  };

  const handleRevert = (promptId: string) => {
    setPromptTexts((prev) => ({
      ...prev,
      [promptId]: mockPromptContent[promptId] ?? "",
    }));
    setHasChanges((prev) => {
      const next = new Set(prev);
      next.delete(promptId);
      return next;
    });
    setEditingPrompt(null);
  };

  const handleTextChange = (promptId: string, text: string) => {
    setPromptTexts((prev) => ({ ...prev, [promptId]: text }));
    if (text !== mockPromptContent[promptId]) {
      setHasChanges((prev) => new Set([...prev, promptId]));
    } else {
      setHasChanges((prev) => {
        const next = new Set(prev);
        next.delete(promptId);
        return next;
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Warning Banner */}
      <Card className="border-amber-200 bg-amber-50">
        <CardContent className="py-3 flex items-center gap-3">
          <MaterialIcon name="warning" className="text-amber-600 text-xl" />
          <span className="text-sm text-amber-800">
            Changes take effect on the next execution. Test carefully before saving.
          </span>
        </CardContent>
      </Card>

      {/* Prompt Cards */}
      {prompts.map((prompt) => {
        const isExpanded = expandedPrompts.has(prompt.id);
        const isEditing = editingPrompt === prompt.id;
        const promptHasChanges = hasChanges.has(prompt.id);
        const content = promptTexts[prompt.id] ?? "";

        return (
          <Card key={prompt.id}>
            <CardHeader className="pb-4 cursor-pointer" onClick={() => !isEditing && toggleExpand(prompt.id)}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <MaterialIcon
                    name={isExpanded ? "expand_less" : "expand_more"}
                    className="text-muted-foreground"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-base">{prompt.name}</CardTitle>
                      {prompt.slotNumber && (
                        <Badge variant="outline" className="font-mono text-xs">
                          Slot {prompt.slotNumber}
                        </Badge>
                      )}
                      {promptHasChanges && (
                        <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                          Unsaved
                        </Badge>
                      )}
                    </div>
                    <CardDescription className="mt-1">{prompt.description}</CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  {isExpanded && !isEditing && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(prompt.id)}
                    >
                      <MaterialIcon name="edit" className="text-base" />
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>

            {isExpanded && (
              <CardContent className="pt-0">
                {isEditing ? (
                  <div className="space-y-4">
                    <PromptEditor
                      value={content}
                      onChange={(value) => handleTextChange(prompt.id, value)}
                      minHeight={256}
                      maxHeight={400}
                    />
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        Last modified: Dec 20, 2025 by pat@pivotstudio.ai
                      </span>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRevert(prompt.id)}
                        >
                          Revert
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleSave(prompt.id)}
                          disabled={!promptHasChanges}
                          className="bg-emerald-600 hover:bg-emerald-700"
                        >
                          <MaterialIcon name="save" className="text-base mr-1" />
                          Save Changes
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <PromptEditor
                      value={content || "(No prompt content)"}
                      onChange={() => {}}
                      readOnly
                      minHeight={200}
                      maxHeight={256}
                    />
                    <span className="text-xs text-muted-foreground">
                      Last modified: Dec 20, 2025 by pat@pivotstudio.ai
                    </span>
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        );
      })}
    </div>
  );
}
