"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type JobStatus = "queued" | "running" | "completed" | "failed";

interface Job {
  id: string;
  type: string;
  status: JobStatus;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  duration?: string;
  result?: string;
  error?: string;
}

const mockJobs: Job[] = [
  {
    id: "job_001",
    type: "prefilter_stories",
    status: "completed",
    createdAt: "2024-12-23 21:00:00",
    startedAt: "2024-12-23 21:00:01",
    completedAt: "2024-12-23 21:00:15",
    duration: "14s",
    result: "47 stories processed, 127 slot entries created",
  },
  {
    id: "job_002",
    type: "select_slots",
    status: "completed",
    createdAt: "2024-12-23 23:55:00",
    startedAt: "2024-12-23 23:55:01",
    completedAt: "2024-12-23 23:55:42",
    duration: "41s",
    result: "5 slots selected successfully",
  },
  {
    id: "job_003",
    type: "decorate_story",
    status: "completed",
    createdAt: "2024-12-23 09:25:00",
    startedAt: "2024-12-23 09:25:02",
    completedAt: "2024-12-23 09:26:33",
    duration: "1m 31s",
    result: "Story rec_123 decorated",
  },
  {
    id: "job_004",
    type: "generate_image",
    status: "running",
    createdAt: "2024-12-23 09:30:00",
    startedAt: "2024-12-23 09:30:01",
  },
  {
    id: "job_005",
    type: "generate_image",
    status: "queued",
    createdAt: "2024-12-23 09:30:05",
  },
  {
    id: "job_006",
    type: "compile_html",
    status: "failed",
    createdAt: "2024-12-22 22:00:00",
    startedAt: "2024-12-22 22:00:01",
    completedAt: "2024-12-22 22:00:05",
    duration: "4s",
    error: "Missing decoration data for slot 3",
  },
];

function getStatusBadge(status: JobStatus) {
  switch (status) {
    case "queued":
      return <Badge className="bg-zinc-500/20 text-zinc-400 border-zinc-500/30">Queued</Badge>;
    case "running":
      return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">Running</Badge>;
    case "completed":
      return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Completed</Badge>;
    case "failed":
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Failed</Badge>;
  }
}

function getJobTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    prefilter_stories: "Pre-Filter Stories",
    select_slots: "Slot Selection",
    decorate_story: "Decorate Story",
    generate_image: "Generate Image",
    compile_html: "Compile HTML",
    send_via_mautic: "Send via Mautic",
    sync_social_posts: "Sync Social Posts",
  };
  return labels[type] || type;
}

export default function JobsPage() {
  const [jobs] = useState<Job[]>(mockJobs);
  const [selectedTab, setSelectedTab] = useState("all");

  const filteredJobs = jobs.filter((job) => {
    if (selectedTab === "all") return true;
    return job.status === selectedTab;
  });

  const queuedCount = jobs.filter((j) => j.status === "queued").length;
  const runningCount = jobs.filter((j) => j.status === "running").length;
  const completedCount = jobs.filter((j) => j.status === "completed").length;
  const failedCount = jobs.filter((j) => j.status === "failed").length;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Job Monitor</h1>
          <p className="text-zinc-400 mt-1">
            View and manage background job execution
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            Clear Completed
          </Button>
          <Button className="bg-orange-500 hover:bg-orange-600 text-white">
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-zinc-300">{queuedCount}</div>
            <div className="text-sm text-zinc-400">Queued</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-400">{runningCount}</div>
            <div className="text-sm text-zinc-400">Running</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-400">{completedCount}</div>
            <div className="text-sm text-zinc-400">Completed</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-red-400">{failedCount}</div>
            <div className="text-sm text-zinc-400">Failed</div>
          </CardContent>
        </Card>
      </div>

      {/* Queue Status */}
      <Card className="bg-zinc-900 border-zinc-800 mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Redis Queue Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm text-zinc-300">Worker connected</span>
            </div>
            <div className="text-sm text-zinc-400">
              Queues: <span className="text-zinc-300">high, default, low</span>
            </div>
            <div className="text-sm text-zinc-400">
              Last heartbeat: <span className="text-zinc-300">2 seconds ago</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Jobs Table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <Tabs value={selectedTab} onValueChange={setSelectedTab}>
          <div className="border-b border-zinc-800 px-4">
            <TabsList className="bg-transparent h-12">
              <TabsTrigger
                value="all"
                className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
              >
                All ({jobs.length})
              </TabsTrigger>
              <TabsTrigger
                value="queued"
                className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
              >
                Queued ({queuedCount})
              </TabsTrigger>
              <TabsTrigger
                value="running"
                className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
              >
                Running ({runningCount})
              </TabsTrigger>
              <TabsTrigger
                value="completed"
                className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
              >
                Completed ({completedCount})
              </TabsTrigger>
              <TabsTrigger
                value="failed"
                className="data-[state=active]:bg-zinc-800 text-zinc-400 data-[state=active]:text-white"
              >
                Failed ({failedCount})
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value={selectedTab} className="m-0">
            <Table>
              <TableHeader>
                <TableRow className="border-zinc-800 hover:bg-transparent">
                  <TableHead className="text-zinc-400">Job ID</TableHead>
                  <TableHead className="text-zinc-400">Type</TableHead>
                  <TableHead className="text-zinc-400">Status</TableHead>
                  <TableHead className="text-zinc-400">Created</TableHead>
                  <TableHead className="text-zinc-400">Duration</TableHead>
                  <TableHead className="text-zinc-400">Result / Error</TableHead>
                  <TableHead className="text-zinc-400 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredJobs.map((job) => (
                  <TableRow key={job.id} className="border-zinc-800">
                    <TableCell className="font-mono text-sm text-zinc-300">
                      {job.id}
                    </TableCell>
                    <TableCell className="text-white">
                      {getJobTypeLabel(job.type)}
                    </TableCell>
                    <TableCell>{getStatusBadge(job.status)}</TableCell>
                    <TableCell className="text-zinc-400">{job.createdAt}</TableCell>
                    <TableCell className="text-zinc-300">
                      {job.duration || (job.status === "running" ? "..." : "-")}
                    </TableCell>
                    <TableCell className="max-w-xs">
                      {job.error ? (
                        <span className="text-red-400 text-sm truncate block">
                          {job.error}
                        </span>
                      ) : job.result ? (
                        <span className="text-zinc-400 text-sm truncate block">
                          {job.result}
                        </span>
                      ) : (
                        <span className="text-zinc-600">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {job.status === "failed" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-orange-400 hover:text-orange-300"
                        >
                          Retry
                        </Button>
                      )}
                      {job.status === "running" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-400 hover:text-red-300"
                        >
                          Cancel
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-zinc-400 hover:text-white"
                      >
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}
