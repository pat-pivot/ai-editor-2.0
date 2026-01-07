"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  RefreshCw,
  ExternalLink,
  Eye,
  Code,
  Mail,
  Copy,
  Check,
  AlertCircle,
  FileText,
} from "lucide-react";

interface NewsletterPreviewData {
  html: string;
  subject_line: string;
  summary: string;
  issue_id: string;
  send_date: string;
  status: string;
  scheduled_send_time?: string;
  scheduled_at?: string;
  record_id: string;
}

interface HtmlPreviewProps {
  onPreviewLoad?: (data: NewsletterPreviewData) => void;
}

export function HtmlPreview({ onPreviewLoad }: HtmlPreviewProps) {
  const [previewData, setPreviewData] = useState<NewsletterPreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"preview" | "html">("preview");
  const [copied, setCopied] = useState(false);

  const fetchPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/newsletter/preview");
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to fetch preview");
      }
      const data = await response.json();
      setPreviewData(data);
      onPreviewLoad?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [onPreviewLoad]);

  useEffect(() => {
    fetchPreview();
  }, [fetchPreview]);

  // Listen for job completion to refresh preview
  useEffect(() => {
    const handleJobComplete = (event: Event) => {
      const customEvent = event as CustomEvent<{ stepId: number }>;
      if (customEvent.detail?.stepId === 4) {
        fetchPreview();
      }
    };

    window.addEventListener("jobCompleted", handleJobComplete);
    return () => window.removeEventListener("jobCompleted", handleJobComplete);
  }, [fetchPreview]);

  const copyHtmlToClipboard = async () => {
    if (!previewData?.html) return;
    try {
      await navigator.clipboard.writeText(previewData.html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center">
            <RefreshCw className="h-8 w-8 text-muted-foreground animate-spin mb-4" />
            <p className="text-muted-foreground">Loading newsletter preview...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center">
            <AlertCircle className="h-8 w-8 text-red-500 mb-4" />
            <p className="text-red-600 font-medium mb-2">Failed to load preview</p>
            <p className="text-muted-foreground text-sm mb-4">{error}</p>
            <Button variant="outline" onClick={fetchPreview}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!previewData || !previewData.html) {
    return (
      <Card>
        <CardContent className="py-12">
          <div className="flex flex-col items-center justify-center">
            <FileText className="h-10 w-10 text-muted-foreground mb-4" />
            <p className="text-muted-foreground font-medium mb-2">No newsletter ready</p>
            <p className="text-sm text-muted-foreground">
              Compile the newsletter first to see a preview
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <CardTitle className="text-base">Email Preview</CardTitle>
              <Badge
                variant="outline"
                className={cn(
                  previewData.status === "next-send" && "bg-blue-100 text-blue-700 border-blue-200",
                  previewData.status === "scheduled" && "bg-emerald-100 text-emerald-700 border-emerald-200",
                  previewData.status === "sent" && "bg-gray-100 text-gray-600 border-gray-200"
                )}
              >
                {previewData.status === "next-send" && "Ready to Send"}
                {previewData.status === "scheduled" && "Scheduled"}
                {previewData.status === "sent" && "Sent"}
                {!["next-send", "scheduled", "sent"].includes(previewData.status) && previewData.status}
              </Badge>
            </div>
            <CardDescription className="flex items-center gap-2">
              <Mail className="h-4 w-4" />
              <span className="font-medium text-foreground">{previewData.subject_line}</span>
            </CardDescription>
          </div>
          <CardAction>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={fetchPreview}
              disabled={loading}
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
              Refresh
            </Button>
          </CardAction>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Summary */}
        {previewData.summary && (
          <div className="mb-4 p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Preheader: </span>
              {previewData.summary}
            </p>
          </div>
        )}

        {/* Tabbed View */}
        <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "preview" | "html")}>
          <div className="flex items-center justify-between mb-4">
            <TabsList className="bg-zinc-100">
              <TabsTrigger value="preview" className="data-[state=active]:bg-white gap-2">
                <Eye className="h-4 w-4" />
                Preview
              </TabsTrigger>
              <TabsTrigger value="html" className="data-[state=active]:bg-white gap-2">
                <Code className="h-4 w-4" />
                Raw HTML
              </TabsTrigger>
            </TabsList>

            {activeTab === "html" && (
              <Button
                variant="outline"
                size="sm"
                onClick={copyHtmlToClipboard}
                className="gap-2"
              >
                {copied ? (
                  <>
                    <Check className="h-4 w-4 text-emerald-500" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy HTML
                  </>
                )}
              </Button>
            )}
          </div>

          <TabsContent value="preview" className="mt-0">
            <div className="border rounded-lg overflow-hidden bg-white">
              <iframe
                srcDoc={previewData.html}
                title="Newsletter Preview"
                className="w-full h-[600px] border-0"
                sandbox="allow-same-origin"
              />
            </div>
          </TabsContent>

          <TabsContent value="html" className="mt-0">
            <div className="border rounded-lg overflow-hidden">
              <pre className="p-4 bg-zinc-950 text-zinc-100 text-xs font-mono overflow-auto max-h-[600px] whitespace-pre-wrap break-all">
                <code>{previewData.html}</code>
              </pre>
            </div>
          </TabsContent>
        </Tabs>

        {/* Issue Info */}
        <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Issue: <span className="font-mono">{previewData.issue_id}</span>
            {previewData.send_date && (
              <> | Date: {new Date(previewData.send_date).toLocaleDateString()}</>
            )}
          </span>
          <span className="font-mono text-xs">
            {previewData.html.length.toLocaleString()} characters
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
