"use client";

import { useState, Suspense, lazy } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { PromptConfig } from "@/lib/step-config";

// Lazy load Monaco editor to avoid SSR issues
const PromptEditor = lazy(() =>
  import("@/components/ui/prompt-editor").then((mod) => ({ default: mod.PromptEditor }))
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

// Mock prompt content - in production this would come from PostgreSQL
const mockPromptContent: Record<string, string> = {
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
  headline_generator: `Generate a punchy, engaging headline for this newsletter story.

REQUIREMENTS:
- Title Case formatting
- Maximum 80 characters
- Punchy and attention-grabbing
- Avoid clickbait or sensationalism
- Accurately represent the story content

Return ONLY the headline text, no quotes or explanation.`,
  bullet_generator: `Generate 3 informative bullet points for this newsletter story.

REQUIREMENTS:
- Each bullet is exactly 2 sentences
- Maximum 260 characters per bullet
- First bullet: Main announcement or news
- Second bullet: Key details and context
- Third bullet: Business impact or implications

Format:
• [Bullet 1]
• [Bullet 2]
• [Bullet 3]`,
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
                    <Suspense
                      fallback={
                        <div className="w-full h-64 rounded-md border bg-muted/30 flex items-center justify-center text-muted-foreground text-sm">
                          Loading editor...
                        </div>
                      }
                    >
                      <PromptEditor
                        value={content}
                        onChange={(value) => handleTextChange(prompt.id, value)}
                        minHeight={256}
                        maxHeight={400}
                      />
                    </Suspense>
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
                    <Suspense
                      fallback={
                        <div className="w-full h-64 rounded-md border bg-muted/30 flex items-center justify-center text-muted-foreground text-sm">
                          Loading...
                        </div>
                      }
                    >
                      <PromptEditor
                        value={content || "(No prompt content)"}
                        onChange={() => {}}
                        readOnly
                        minHeight={200}
                        maxHeight={256}
                      />
                    </Suspense>
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
