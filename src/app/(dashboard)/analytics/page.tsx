"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface EmailStats {
  issueDate: string;
  subject: string;
  sent: number;
  delivered: number;
  opens: number;
  uniqueOpens: number;
  clicks: number;
  uniqueClicks: number;
  bounces: number;
  unsubscribes: number;
}

const mockStats: EmailStats[] = [
  {
    issueDate: "Dec 23, 2024",
    subject: "AI reshapes 30% of jobs; OpenAI hits 95% coding accuracy...",
    sent: 4087,
    delivered: 4052,
    opens: 2847,
    uniqueOpens: 1823,
    clicks: 412,
    uniqueClicks: 287,
    bounces: 35,
    unsubscribes: 8,
  },
  {
    issueDate: "Dec 22, 2024",
    subject: "Google's Gemini 2.0 launches; Microsoft's AI revenue hits $10B...",
    sent: 4079,
    delivered: 4044,
    opens: 2912,
    uniqueOpens: 1876,
    clicks: 456,
    uniqueClicks: 312,
    bounces: 35,
    unsubscribes: 5,
  },
  {
    issueDate: "Dec 21, 2024",
    subject: "NVIDIA announces H200 chip; AI regulation bill advances...",
    sent: 4071,
    delivered: 4036,
    opens: 2756,
    uniqueOpens: 1798,
    clicks: 389,
    uniqueClicks: 267,
    bounces: 35,
    unsubscribes: 12,
  },
  {
    issueDate: "Dec 20, 2024",
    subject: "Anthropic raises $2B; AI-powered drug discovery breakthrough...",
    sent: 4065,
    delivered: 4030,
    opens: 2834,
    uniqueOpens: 1845,
    clicks: 423,
    uniqueClicks: 298,
    bounces: 35,
    unsubscribes: 6,
  },
  {
    issueDate: "Dec 19, 2024",
    subject: "OpenAI's Sora launches publicly; Meta's AI agents go live...",
    sent: 4058,
    delivered: 4023,
    opens: 3012,
    uniqueOpens: 1923,
    clicks: 512,
    uniqueClicks: 356,
    bounces: 35,
    unsubscribes: 4,
  },
];

function formatPercent(numerator: number, denominator: number): string {
  if (denominator === 0) return "0%";
  return ((numerator / denominator) * 100).toFixed(1) + "%";
}

export default function AnalyticsPage() {
  const [stats] = useState<EmailStats[]>(mockStats);
  const [selectedPeriod, setSelectedPeriod] = useState("7d");

  // Calculate aggregate stats
  const totalSent = stats.reduce((acc, s) => acc + s.sent, 0);
  const totalDelivered = stats.reduce((acc, s) => acc + s.delivered, 0);
  const totalOpens = stats.reduce((acc, s) => acc + s.uniqueOpens, 0);
  const totalClicks = stats.reduce((acc, s) => acc + s.uniqueClicks, 0);

  const avgOpenRate = totalDelivered > 0 ? (totalOpens / totalDelivered) * 100 : 0;
  const avgClickRate = totalOpens > 0 ? (totalClicks / totalOpens) * 100 : 0;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-zinc-400 mt-1">
            Email performance metrics from Mautic
          </p>
        </div>
        <div className="flex gap-2">
          <div className="flex rounded-lg overflow-hidden border border-zinc-800">
            {["7d", "30d", "90d"].map((period) => (
              <button
                key={period}
                onClick={() => setSelectedPeriod(period)}
                className={`px-4 py-2 text-sm ${
                  selectedPeriod === period
                    ? "bg-zinc-800 text-white"
                    : "bg-zinc-900 text-zinc-400 hover:text-white"
                }`}
              >
                {period === "7d" ? "7 Days" : period === "30d" ? "30 Days" : "90 Days"}
              </button>
            ))}
          </div>
          <Button className="bg-orange-500 hover:bg-orange-600 text-white">
            Sync from Mautic
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-400 text-sm">Total Subscribers</span>
              <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                +32 this week
              </Badge>
            </div>
            <div className="text-3xl font-bold text-white">4,087</div>
            <div className="text-sm text-zinc-500 mt-1">Active contacts</div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-400 text-sm">Avg Open Rate</span>
              <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                +2.3%
              </Badge>
            </div>
            <div className="text-3xl font-bold text-white">{avgOpenRate.toFixed(1)}%</div>
            <div className="text-sm text-zinc-500 mt-1">Unique opens / delivered</div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-400 text-sm">Avg Click Rate</span>
              <Badge className="bg-zinc-500/20 text-zinc-400 border-zinc-500/30">
                -0.5%
              </Badge>
            </div>
            <div className="text-3xl font-bold text-white">{avgClickRate.toFixed(1)}%</div>
            <div className="text-sm text-zinc-500 mt-1">Unique clicks / opens</div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-400 text-sm">Delivery Rate</span>
            </div>
            <div className="text-3xl font-bold text-white">
              {formatPercent(totalDelivered, totalSent)}
            </div>
            <div className="text-sm text-zinc-500 mt-1">
              {stats.reduce((acc, s) => acc + s.bounces, 0)} bounces
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bot Filter Notice */}
      <Card className="bg-blue-500/10 border-blue-500/30 mb-6">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <svg className="h-5 w-5 text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm text-blue-300">
                <strong>Bot filtering enabled:</strong> Open and click metrics exclude security server pre-fetches (Apple MPP, Outlook, etc.) for accurate engagement data.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Email Performance Table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white">Email Performance</CardTitle>
          <CardDescription className="text-zinc-400">
            Last {stats.length} issues sent
          </CardDescription>
        </CardHeader>
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-zinc-400">Issue</TableHead>
              <TableHead className="text-zinc-400">Subject</TableHead>
              <TableHead className="text-zinc-400 text-right">Sent</TableHead>
              <TableHead className="text-zinc-400 text-right">Open Rate</TableHead>
              <TableHead className="text-zinc-400 text-right">Click Rate</TableHead>
              <TableHead className="text-zinc-400 text-right">Clicks</TableHead>
              <TableHead className="text-zinc-400 text-right">Unsubs</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {stats.map((email, i) => (
              <TableRow key={i} className="border-zinc-800">
                <TableCell className="text-white font-medium">
                  {email.issueDate}
                </TableCell>
                <TableCell className="text-zinc-300 max-w-xs truncate">
                  {email.subject}
                </TableCell>
                <TableCell className="text-zinc-300 text-right">
                  {email.sent.toLocaleString()}
                </TableCell>
                <TableCell className="text-right">
                  <span className={
                    (email.uniqueOpens / email.delivered) * 100 > 45
                      ? "text-green-400"
                      : "text-zinc-300"
                  }>
                    {formatPercent(email.uniqueOpens, email.delivered)}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <span className={
                    (email.uniqueClicks / email.uniqueOpens) * 100 > 15
                      ? "text-green-400"
                      : "text-zinc-300"
                  }>
                    {formatPercent(email.uniqueClicks, email.uniqueOpens)}
                  </span>
                </TableCell>
                <TableCell className="text-zinc-300 text-right">
                  {email.uniqueClicks}
                </TableCell>
                <TableCell className="text-right">
                  <span className={email.unsubscribes > 10 ? "text-red-400" : "text-zinc-400"}>
                    {email.unsubscribes}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Top Links */}
      <div className="grid grid-cols-2 gap-6 mt-6">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-white text-base">Top Clicked Stories (Last 7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { title: "OpenAI's Sora launches publicly", clicks: 187, slot: 2 },
                { title: "NVIDIA announces H200 chip", clicks: 156, slot: 2 },
                { title: "AI reshapes 30% of jobs by 2030", clicks: 134, slot: 1 },
                { title: "Anthropic raises $2B at $20B valuation", clicks: 121, slot: 4 },
                { title: "Healthcare AI adoption hits 78%", clicks: 98, slot: 3 },
              ].map((story, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-zinc-800 last:border-0">
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-500 text-sm w-4">{i + 1}.</span>
                    <span className="text-zinc-300 text-sm">{story.title}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge className="bg-zinc-800 text-zinc-400 border-zinc-700 text-xs">
                      Slot {story.slot}
                    </Badge>
                    <span className="text-white font-medium text-sm">{story.clicks}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-white text-base">Subscriber Growth</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">New subscribers (7d)</span>
                <span className="text-green-400 font-medium">+47</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Unsubscribes (7d)</span>
                <span className="text-red-400 font-medium">-15</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Net growth (7d)</span>
                <span className="text-green-400 font-medium">+32</span>
              </div>
              <div className="border-t border-zinc-800 pt-4 mt-4">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">Monthly growth rate</span>
                  <span className="text-white font-medium">+3.2%</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
