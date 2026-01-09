"use client";

import { useState, useEffect, useCallback } from "react";
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

interface SubscriberStats {
  total: number;
  growth: number;
  newThisPeriod: number;
  unsubscribesThisPeriod: number;
}

function formatPercent(numerator: number, denominator: number): string {
  if (denominator === 0) return "0%";
  return ((numerator / denominator) * 100).toFixed(1) + "%";
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<EmailStats[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState("7d");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [subscribers, setSubscribers] = useState<SubscriberStats>({
    total: 0,
    growth: 0,
    newThisPeriod: 0,
    unsubscribesThisPeriod: 0,
  });

  // Fetch analytics data from API
  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/analytics?period=${selectedPeriod}`);
      const data = await response.json();

      if (data.success) {
        setStats(data.emails || []);
        setSubscribers(data.subscribers || {
          total: 0,
          growth: 0,
          newThisPeriod: 0,
          unsubscribesThisPeriod: 0,
        });
      } else {
        console.error("Analytics API error:", data.error);
      }
    } catch (error) {
      console.error("Failed to fetch analytics:", error);
    } finally {
      setLoading(false);
    }
  }, [selectedPeriod]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await fetch("/api/analytics/sync", { method: "POST" });
      await fetchAnalytics();
    } catch (error) {
      console.error("Sync failed:", error);
    } finally {
      setSyncing(false);
    }
  };

  // Calculate aggregate stats from fetched data
  const totalSent = stats.reduce((acc, s) => acc + s.sent, 0);
  const totalDelivered = stats.reduce((acc, s) => acc + s.delivered, 0);
  const totalOpens = stats.reduce((acc, s) => acc + s.uniqueOpens, 0);
  const totalClicks = stats.reduce((acc, s) => acc + s.uniqueClicks, 0);

  const avgOpenRate = totalDelivered > 0 ? (totalOpens / totalDelivered) * 100 : 0;
  const avgClickRate = totalOpens > 0 ? (totalClicks / totalOpens) * 100 : 0;

  return (
    <div className="p-8 bg-zinc-50 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">Analytics</h1>
          <p className="text-zinc-600 mt-1">
            Email performance metrics from Mautic
          </p>
        </div>
        <div className="flex gap-2">
          <div className="flex rounded-lg overflow-hidden border border-zinc-200">
            {["7d", "30d", "90d"].map((period) => (
              <button
                key={period}
                onClick={() => setSelectedPeriod(period)}
                className={`px-4 py-2 text-sm ${
                  selectedPeriod === period
                    ? "bg-zinc-100 text-zinc-900"
                    : "bg-white text-zinc-600 hover:text-zinc-900"
                }`}
              >
                {period === "7d" ? "7 Days" : period === "30d" ? "30 Days" : "90 Days"}
              </button>
            ))}
          </div>
          <Button
            onClick={handleSync}
            disabled={syncing}
            className="bg-orange-500 hover:bg-orange-600 text-white disabled:opacity-50"
          >
            {syncing ? "Syncing..." : "Sync from Mautic"}
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-600 text-sm">Total Subscribers</span>
              {subscribers.growth !== 0 && (
                <Badge className={`${subscribers.growth > 0 ? 'bg-green-500/10 text-green-600 border-green-500/30' : 'bg-red-500/10 text-red-600 border-red-500/30'}`}>
                  {subscribers.growth > 0 ? '+' : ''}{subscribers.growth} this week
                </Badge>
              )}
            </div>
            <div className="text-3xl font-bold text-zinc-900">
              {loading ? "..." : subscribers.total.toLocaleString()}
            </div>
            <div className="text-sm text-zinc-500 mt-1">Active contacts (List 21)</div>
          </CardContent>
        </Card>

        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-600 text-sm">Avg Open Rate</span>
            </div>
            <div className="text-3xl font-bold text-zinc-900">
              {loading ? "..." : `${avgOpenRate.toFixed(1)}%`}
            </div>
            <div className="text-sm text-zinc-500 mt-1">Unique opens / delivered</div>
          </CardContent>
        </Card>

        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-600 text-sm">Avg Click Rate</span>
            </div>
            <div className="text-3xl font-bold text-zinc-900">
              {loading ? "..." : `${avgClickRate.toFixed(1)}%`}
            </div>
            <div className="text-sm text-zinc-500 mt-1">Unique clicks / opens</div>
          </CardContent>
        </Card>

        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-zinc-600 text-sm">Delivery Rate</span>
            </div>
            <div className="text-3xl font-bold text-zinc-900">
              {loading ? "..." : formatPercent(totalDelivered, totalSent)}
            </div>
            <div className="text-sm text-zinc-500 mt-1">
              {stats.reduce((acc, s) => acc + s.bounces, 0)} bounces
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bot Filter Notice */}
      <Card className="bg-blue-50 border-blue-200 mb-6">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm text-blue-700">
                <strong>Bot filtering enabled:</strong> Open and click metrics exclude security server pre-fetches (Apple MPP, Outlook, etc.) for accurate engagement data.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Email Performance Table */}
      <Card className="bg-white border-zinc-200 shadow-sm">
        <CardHeader>
          <CardTitle className="text-zinc-900">Email Performance</CardTitle>
          <CardDescription className="text-zinc-600">
            {loading ? "Loading..." : `Last ${stats.length} issues sent`}
          </CardDescription>
        </CardHeader>
        {loading ? (
          <CardContent>
            <p className="text-zinc-500 text-center py-8">Loading email stats...</p>
          </CardContent>
        ) : stats.length === 0 ? (
          <CardContent>
            <p className="text-zinc-500 text-center py-8">No emails found in this period</p>
          </CardContent>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-200 hover:bg-transparent">
                <TableHead className="text-zinc-600">Issue</TableHead>
                <TableHead className="text-zinc-600">Subject</TableHead>
                <TableHead className="text-zinc-600 text-right">Sent</TableHead>
                <TableHead className="text-zinc-600 text-right">Open Rate</TableHead>
                <TableHead className="text-zinc-600 text-right">Click Rate</TableHead>
                <TableHead className="text-zinc-600 text-right">Clicks</TableHead>
                <TableHead className="text-zinc-600 text-right">Unsubs</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stats.map((email, i) => (
                <TableRow key={i} className="border-zinc-200">
                  <TableCell className="text-zinc-900 font-medium">
                    {email.issueDate}
                  </TableCell>
                  <TableCell className="text-zinc-700 max-w-xs truncate">
                    {email.subject}
                  </TableCell>
                  <TableCell className="text-zinc-700 text-right">
                    {email.sent.toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={
                      email.delivered > 0 && (email.uniqueOpens / email.delivered) * 100 > 45
                        ? "text-green-600"
                        : "text-zinc-700"
                    }>
                      {formatPercent(email.uniqueOpens, email.delivered)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={
                      email.uniqueOpens > 0 && (email.uniqueClicks / email.uniqueOpens) * 100 > 15
                        ? "text-green-600"
                        : "text-zinc-700"
                    }>
                      {formatPercent(email.uniqueClicks, email.uniqueOpens)}
                    </span>
                  </TableCell>
                  <TableCell className="text-zinc-700 text-right">
                    {email.uniqueClicks}
                  </TableCell>
                  <TableCell className="text-right">
                    <span className={email.unsubscribes > 10 ? "text-red-500" : "text-zinc-500"}>
                      {email.unsubscribes}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* Bottom Cards */}
      <div className="grid grid-cols-2 gap-6 mt-6">
        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-zinc-900 text-base">Top Clicked Stories ({selectedPeriod === "7d" ? "Last 7 Days" : selectedPeriod === "30d" ? "Last 30 Days" : "Last 90 Days"})</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-zinc-500 text-center py-4">Loading...</p>
            ) : stats.length === 0 ? (
              <p className="text-zinc-500 text-center py-4">No data available</p>
            ) : (
              <div className="space-y-3">
                <p className="text-zinc-500 text-sm">Top stories based on email click data - coming soon</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-white border-zinc-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-zinc-900 text-base">Subscriber Growth</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-zinc-600">New subscribers ({selectedPeriod})</span>
                <span className="text-green-600 font-medium">
                  {loading ? "..." : `+${subscribers.newThisPeriod}`}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-600">Unsubscribes ({selectedPeriod})</span>
                <span className="text-red-500 font-medium">
                  {loading ? "..." : `-${subscribers.unsubscribesThisPeriod}`}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-600">Net growth ({selectedPeriod})</span>
                <span className={`font-medium ${subscribers.growth >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                  {loading ? "..." : `${subscribers.growth >= 0 ? '+' : ''}${subscribers.growth}`}
                </span>
              </div>
              <div className="border-t border-zinc-200 pt-4 mt-4">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-600">Total subscribers</span>
                  <span className="text-zinc-900 font-medium">
                    {loading ? "..." : subscribers.total.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
