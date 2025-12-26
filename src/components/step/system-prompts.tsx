"use client";

import { useState, useEffect, Suspense, lazy, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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

interface DBPrompt {
  id: string;
  prompt_key: string;
  step_id: number;
  name: string;
  description: string;
  model: string;
  temperature: number;
  slot_number: number | null;
  content: string;
  version: number;
  updated_at: string;
}

interface SystemPromptsProps {
  stepId: number;
  prompts: PromptConfig[];
}

export function SystemPrompts({ stepId, prompts }: SystemPromptsProps) {
  const [expandedPrompts, setExpandedPrompts] = useState<Set<string>>(
    new Set([prompts[0]?.id])
  );
  const [editingPrompt, setEditingPrompt] = useState<string | null>(null);

  // Track original content from database
  const [originalContent, setOriginalContent] = useState<Record<string, string>>({});
  // Track current edited content
  const [editedContent, setEditedContent] = useState<Record<string, string>>({});
  // Track which prompts have unsaved changes
  const [hasChanges, setHasChanges] = useState<Set<string>>(new Set());
  // Track saving state
  const [saving, setSaving] = useState<string | null>(null);
  // Track loading state
  const [loading, setLoading] = useState(true);
  // Track error state
  const [error, setError] = useState<string | null>(null);

  // Metadata from database
  const [promptMeta, setPromptMeta] = useState<Record<string, { version: number; lastModified: string }>>({});

  // Load prompts from database API on mount
  useEffect(() => {
    async function loadPrompts() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/prompts?stepId=${stepId}`);
        if (!response.ok) {
          throw new Error("Failed to fetch prompts");
        }
        const data = await response.json();
        const dbPrompts: DBPrompt[] = data.prompts || [];

        const contentMap: Record<string, string> = {};
        const metaMap: Record<string, { version: number; lastModified: string }> = {};

        // Match prompts by prompt_key
        prompts.forEach((p) => {
          const dbPrompt = dbPrompts.find((dp) => dp.prompt_key === p.id);
          if (dbPrompt) {
            contentMap[p.id] = dbPrompt.content || "";
            metaMap[p.id] = {
              version: dbPrompt.version || 1,
              lastModified: dbPrompt.updated_at || new Date().toISOString(),
            };
          } else {
            // Fallback for prompts not in database
            contentMap[p.id] = `You are an AI assistant for the Pivot 5 newsletter pipeline.

Task: ${p.description}

Model: ${p.model}
Temperature: ${p.temperature}`;
            metaMap[p.id] = {
              version: 1,
              lastModified: new Date().toISOString(),
            };
          }
        });

        setOriginalContent(contentMap);
        setEditedContent(contentMap);
        setPromptMeta(metaMap);
      } catch (err) {
        console.error("Failed to load prompts:", err);
        setError(err instanceof Error ? err.message : "Failed to load prompts");
      } finally {
        setLoading(false);
      }
    }

    loadPrompts();
  }, [stepId, prompts]);

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

  const handleTextChange = useCallback((promptId: string, text: string) => {
    setEditedContent((prev) => ({ ...prev, [promptId]: text }));

    // Compare with original to track changes
    const original = originalContent[promptId] || "";
    if (text !== original) {
      setHasChanges((prev) => new Set([...prev, promptId]));
    } else {
      setHasChanges((prev) => {
        const next = new Set(prev);
        next.delete(promptId);
        return next;
      });
    }
  }, [originalContent]);

  const handleRevert = (promptId: string) => {
    // Restore to original content
    setEditedContent((prev) => ({
      ...prev,
      [promptId]: originalContent[promptId] || "",
    }));
    setHasChanges((prev) => {
      const next = new Set(prev);
      next.delete(promptId);
      return next;
    });
    setEditingPrompt(null);
  };

  const handleSave = async (promptId: string) => {
    setSaving(promptId);
    setError(null);
    try {
      const response = await fetch("/api/prompts", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          promptKey: promptId,
          content: editedContent[promptId],
          changeSummary: "Updated via dashboard",
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save prompt");
      }

      const data = await response.json();

      // Update original content to match saved content
      setOriginalContent((prev) => ({
        ...prev,
        [promptId]: editedContent[promptId],
      }));

      // Update metadata
      if (data.prompt) {
        setPromptMeta((prev) => ({
          ...prev,
          [promptId]: {
            version: data.prompt.version || (prev[promptId]?.version || 0) + 1,
            lastModified: data.prompt.updated_at || new Date().toISOString(),
          },
        }));
      }

      // Clear changes flag
      setHasChanges((prev) => {
        const next = new Set(prev);
        next.delete(promptId);
        return next;
      });

      setEditingPrompt(null);
    } catch (err) {
      console.error("Failed to save prompt:", err);
      setError(err instanceof Error ? err.message : "Failed to save prompt");
    } finally {
      setSaving(null);
    }
  };

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return "Unknown";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="rounded-md bg-muted/30 border p-8 text-center text-muted-foreground">
          Loading prompts from database...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Info banner */}
      <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-amber-800 text-sm flex items-start gap-2">
        <MaterialIcon name="info" className="text-amber-600 mt-0.5" />
        <div>
          <p className="font-medium">Prompts are stored in PostgreSQL with version history.</p>
          <p className="mt-1 text-amber-700">Note: Step 1 Pre-Filter prompts are not yet wired to the workers. See <code className="bg-amber-100 px-1 rounded">System-Prompt-Engineering-12-26-25.md</code> in the docs folder for details.</p>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 p-4 text-red-800 text-sm flex items-center gap-2">
          <MaterialIcon name="error" className="text-red-600" />
          <div>{error}</div>
        </div>
      )}

      {/* Prompt Cards */}
      {prompts.map((prompt) => {
        const isExpanded = expandedPrompts.has(prompt.id);
        const isEditing = editingPrompt === prompt.id;
        const promptHasChanges = hasChanges.has(prompt.id);
        const content = editedContent[prompt.id] ?? "";
        const meta = promptMeta[prompt.id];

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
                          Modified
                        </Badge>
                      )}
                    </div>
                    <CardDescription className="mt-1">{prompt.description}</CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <Badge variant="secondary" className="font-mono text-xs">
                    {prompt.model}
                  </Badge>
                  <Badge variant="outline" className="font-mono text-xs">
                    temp: {prompt.temperature}
                  </Badge>
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
                        {meta ? `v${meta.version} • Last modified: ${formatDate(meta.lastModified)}` : ""}
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
                          disabled={!promptHasChanges || saving === prompt.id}
                          onClick={() => handleSave(prompt.id)}
                        >
                          {saving === prompt.id ? (
                            <>
                              <MaterialIcon name="sync" className="text-base mr-1 animate-spin" />
                              Saving...
                            </>
                          ) : (
                            <>
                              <MaterialIcon name="save" className="text-base mr-1" />
                              Save
                            </>
                          )}
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
                      {meta ? `v${meta.version} • Last modified: ${formatDate(meta.lastModified)}` : ""}
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
