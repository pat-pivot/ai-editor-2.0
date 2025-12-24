"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface NewsletterSlot {
  slot: number;
  label: string;
  headline: string;
  dek: string;
  bullets: string[];
  imageUrl: string;
  imageStatus: string;
  source: string;
  url: string;
}

// Interfaces for Airtable data
interface DecorationData {
  id: string;
  storyId: string;
  issueId: string;
  slotOrder: number;
  pivotId: string;
  headline: string;
  aiDek: string;
  label: string;
  b1: string;
  b2: string;
  b3: string;
  imagePrompt: string;
  imageStatus: string;
  imageUrl: string;
  raw: string;
  coreUrl: string;
  sourceId: string;
}

interface SelectedSlotsData {
  id: string;
  issueId: string;
  issueDate: string;
  subjectLine: string;
  status: string;
  socialPostStatus: string;
  slots: Array<{
    slot: number;
    headline: string;
    storyId: string;
    pivotId: string;
  }>;
}

const slotLabels: Record<number, string> = {
  1: "JOBS & ECONOMY",
  2: "TIER 1 AI",
  3: "INDUSTRY IMPACT",
  4: "EMERGING COMPANIES",
  5: "CONSUMER AI",
};

export default function NewsletterPage() {
  const [slots, setSlots] = useState<NewsletterSlot[]>([]);
  const [selectedSlots, setSelectedSlots] = useState<SelectedSlotsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedView, setSelectedView] = useState("preview");
  const [isSending, setIsSending] = useState(false);

  const fetchNewsletterData = useCallback(async () => {
    try {
      setLoading(true);

      // Fetch slots and decorations data in parallel
      const [slotsRes, decorationsRes] = await Promise.all([
        fetch("/api/slots"),
        fetch("/api/decorations"),
      ]);

      let slotsData: SelectedSlotsData | null = null;
      let decorations: DecorationData[] = [];

      if (slotsRes.ok) {
        const data = await slotsRes.json();
        slotsData = data.selectedSlots;
        setSelectedSlots(slotsData);
      }

      if (decorationsRes.ok) {
        const data = await decorationsRes.json();
        decorations = data.decorations || [];
      }

      // Map decorations to newsletter slots
      const newsletterSlots: NewsletterSlot[] = decorations
        .sort((a, b) => a.slotOrder - b.slotOrder)
        .map((d) => ({
          slot: d.slotOrder,
          label: d.label || slotLabels[d.slotOrder] || `SLOT ${d.slotOrder}`,
          headline: d.headline || "Untitled",
          dek: d.aiDek || "",
          bullets: [d.b1, d.b2, d.b3].filter(Boolean),
          imageUrl: d.imageUrl || `https://placehold.co/636x358/1a1a1a/ff6f00?text=Slot+${d.slotOrder}`,
          imageStatus: d.imageStatus || "pending",
          source: d.sourceId || "Unknown",
          url: d.coreUrl || "#",
        }));

      setSlots(newsletterSlots);
    } catch (error) {
      console.error("Error fetching newsletter data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNewsletterData();
  }, [fetchNewsletterData]);

  const handleTestSend = () => {
    setIsSending(true);
    setTimeout(() => setIsSending(false), 2000);
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-zinc-400">Loading newsletter data from Airtable...</div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Newsletter Preview</h1>
          <p className="text-zinc-400 mt-1">
            {selectedSlots?.issueDate || "No issue loaded"}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            Copy HTML
          </Button>
          <Button
            variant="outline"
            onClick={handleTestSend}
            disabled={isSending}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            {isSending ? "Sending..." : "Send Test"}
          </Button>
          <Button className="bg-orange-500 hover:bg-orange-600 text-white">
            Send to Mautic
          </Button>
        </div>
      </div>

      {/* Status Bar */}
      <Card className="bg-zinc-900 border-zinc-800 mb-6">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                {selectedSlots?.status === "sent" ? (
                  <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                    Sent
                  </Badge>
                ) : slots.length === 5 && slots.every(s => s.imageStatus === "generated") ? (
                  <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                    Ready to Send
                  </Badge>
                ) : slots.length > 0 ? (
                  <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
                    In Progress
                  </Badge>
                ) : (
                  <Badge className="bg-zinc-500/20 text-zinc-400 border-zinc-500/30">
                    Pending
                  </Badge>
                )}
              </div>
              <div className="text-sm text-zinc-400">
                Subject: <span className="text-white">{selectedSlots?.subjectLine || "Not generated"}</span>
              </div>
            </div>
            <div className="text-sm text-zinc-400">
              Scheduled: <span className="text-white">5:00 AM EST</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* View Tabs */}
      <Tabs value={selectedView} onValueChange={setSelectedView} className="mb-6">
        <TabsList className="bg-zinc-900 border border-zinc-800">
          <TabsTrigger
            value="preview"
            className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
          >
            Visual Preview
          </TabsTrigger>
          <TabsTrigger
            value="slots"
            className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
          >
            Slot Details
          </TabsTrigger>
          <TabsTrigger
            value="html"
            className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
          >
            HTML Source
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Content */}
      {selectedView === "preview" && (
        <Card className="bg-zinc-900 border-zinc-800 overflow-hidden">
          <CardContent className="p-0">
            {slots.length === 0 ? (
              <div className="p-8 text-center text-zinc-500">
                No newsletter content available. Decorations have not been generated yet.
              </div>
            ) : (
              <div className="bg-white p-8 max-w-2xl mx-auto">
                {/* Email Header */}
                <div className="text-center mb-8 pb-6 border-b border-gray-200">
                  <div className="text-2xl font-bold text-gray-900 mb-1">PIVOT 5</div>
                  <div className="text-sm text-gray-500">5 headlines, 5 minutes, 5 days a week</div>
                </div>

                {/* Stories */}
                {slots.map((slot) => (
                  <div key={slot.slot} className="mb-8 pb-8 border-b border-gray-200 last:border-0">
                    <div className="text-xs font-semibold text-orange-500 mb-2 tracking-wider">
                      {slot.label}
                    </div>
                    <h2 className="text-xl font-bold text-gray-900 mb-2">
                      {slot.headline}
                    </h2>
                    <p className="text-gray-600 mb-4 italic">{slot.dek}</p>
                    {slot.imageStatus === "generated" && slot.imageUrl ? (
                      <img
                        src={slot.imageUrl}
                        alt={slot.headline}
                        className="w-full rounded-lg mb-4 aspect-video object-cover"
                      />
                    ) : (
                      <div className="bg-gray-100 rounded-lg mb-4 aspect-video flex items-center justify-center">
                        <span className="text-gray-400">
                          {slot.imageStatus === "pending" ? "[Image Pending]" : "[Image Generation Failed]"}
                        </span>
                      </div>
                    )}
                    <ul className="space-y-3 mb-4">
                      {slot.bullets.map((bullet, i) => (
                        <li
                          key={i}
                          className="text-gray-700 text-sm leading-relaxed pl-4 border-l-2 border-orange-400"
                          dangerouslySetInnerHTML={{
                            __html: bullet.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),
                          }}
                        />
                      ))}
                    </ul>
                    <a
                      href={slot.url}
                      className="text-orange-500 text-sm font-medium hover:underline"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Read more at {slot.source} &rarr;
                    </a>
                  </div>
                ))}

                {/* Footer */}
                <div className="text-center text-xs text-gray-400 pt-6 border-t border-gray-200">
                  <p className="mb-2">You're receiving this because you signed up for Pivot 5.</p>
                  <p>
                    <a href="#" className="text-orange-500">Unsubscribe</a> |{" "}
                    <a href="#" className="text-orange-500">Manage Preferences</a>
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {selectedView === "slots" && (
        <div className="space-y-4">
          {slots.map((slot) => (
            <Card key={slot.slot} className="bg-zinc-900 border-zinc-800">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Badge className="bg-orange-500/20 text-orange-400 border-orange-500/30 mb-2">
                      Slot {slot.slot}: {slot.label}
                    </Badge>
                    <CardTitle className="text-white">{slot.headline}</CardTitle>
                    <CardDescription className="text-zinc-400 mt-1">
                      {slot.dek}
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-zinc-700 text-zinc-300"
                  >
                    Edit
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {slot.bullets.map((bullet, i) => (
                    <div key={i} className="flex gap-3">
                      <span className="text-orange-400 font-bold">•</span>
                      <span
                        className="text-zinc-300 text-sm"
                        dangerouslySetInnerHTML={{
                          __html: bullet.replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>'),
                        }}
                      />
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-4 mt-4 pt-4 border-t border-zinc-800 text-sm text-zinc-400">
                  <span>Source: {slot.source}</span>
                  <span>Image: Ready</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {selectedView === "html" && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <pre className="text-xs text-zinc-400 font-mono overflow-x-auto">
              {`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pivot 5 - December 23, 2024</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table width="640" cellpadding="0" cellspacing="0" style="background: #ffffff;">
          <!-- Header -->
          <tr>
            <td align="center" style="padding: 30px; border-bottom: 1px solid #eee;">
              <h1 style="margin: 0; font-family: Georgia, serif; font-size: 28px;">PIVOT 5</h1>
              <p style="margin: 5px 0 0; color: #666; font-size: 14px;">5 headlines, 5 minutes, 5 days a week</p>
            </td>
          </tr>

          <!-- Story blocks would go here -->
          <!-- ... -->

        </table>
      </td>
    </tr>
  </table>
</body>
</html>`}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
