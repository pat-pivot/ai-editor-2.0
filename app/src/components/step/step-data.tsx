"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

function MaterialIcon({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cn("material-symbols-outlined", className)}>
      {name}
    </span>
  );
}

interface StepDataProps {
  stepId: number;
  tableName: string;
  tableId: string;
  baseId: string;
}

// Mock data for different step tables
const mockPreFilterData = [
  { id: "rec_abc123", storyID: "p_abc123", headline: "OpenAI's $6.6B Raise Signals New AI Arms Race", slot: 1, score: 9.2, date: "Dec 23" },
  { id: "rec_def456", storyID: "p_def456", headline: "Google Unveils Gemini 3 Flash Preview", slot: 2, score: 8.8, date: "Dec 23" },
  { id: "rec_ghi789", storyID: "p_ghi789", headline: "Microsoft Copilot Expands to Enterprise", slot: 2, score: 8.5, date: "Dec 22" },
  { id: "rec_jkl012", storyID: "p_jkl012", headline: "Healthcare AI Adoption Hits 70% Milestone", slot: 3, score: 8.9, date: "Dec 23" },
  { id: "rec_mno345", storyID: "p_mno345", headline: "Startup Raises $50M for AI Developer Tools", slot: 4, score: 7.8, date: "Dec 23" },
  { id: "rec_pqr678", storyID: "p_pqr678", headline: "The Ethics of AI Dating Apps Spark Debate", slot: 5, score: 7.5, date: "Dec 23" },
  { id: "rec_stu901", storyID: "p_stu901", headline: "NVIDIA Stock Hits New All-Time High", slot: 1, score: 9.0, date: "Dec 22" },
  { id: "rec_vwx234", storyID: "p_vwx234", headline: "Meta Releases Llama 4 Open Source Model", slot: 2, score: 8.7, date: "Dec 22" },
];

const mockSelectedSlotsData = [
  { issue_date: "Pivot 5 - Dec 23", subject: "OpenAI's $6.6B Raise Signals New AI Arms Race", status: "decorated" },
  { issue_date: "Pivot 5 - Dec 22", subject: "Google Drops Gemini 3 Flash Preview", status: "sent" },
  { issue_date: "Pivot 5 - Dec 21", subject: "Meta's AI Ambitions Take Shape with Llama 4", status: "sent" },
  { issue_date: "Pivot 5 - Dec 20", subject: "NVIDIA Stock Hits New High on AI Demand", status: "sent" },
];

const mockDecorationData = [
  { id: "rec_dec1", headline: "OpenAI's $6.6B Raise Signals New AI Arms Race", slot: 1, image_status: "generated", decorated: true },
  { id: "rec_dec2", headline: "Google Unveils Gemini 3 Flash Preview", slot: 2, image_status: "generated", decorated: true },
  { id: "rec_dec3", headline: "Healthcare AI Adoption Hits 70%", slot: 3, image_status: "pending", decorated: false },
  { id: "rec_dec4", headline: "Startup Raises $50M for AI Tools", slot: 4, image_status: "pending", decorated: false },
  { id: "rec_dec5", headline: "The Ethics of AI Dating Apps", slot: 5, image_status: "pending", decorated: false },
];

export function StepData({ stepId, tableName, tableId, baseId }: StepDataProps) {
  const airtableUrl = `https://airtable.com/${baseId}/${tableId}`;

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="text-base">{tableName}</CardTitle>
            <CardDescription className="mt-1 font-mono text-xs">
              Base: {baseId} | Table: {tableId}
            </CardDescription>
          </div>
          <CardAction>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground">
                Last sync: 2 minutes ago
              </span>
              <Button variant="outline" size="sm" className="gap-2">
                <MaterialIcon name="sync" className="text-base" />
                Sync Now
              </Button>
              <Button variant="outline" size="sm" className="gap-2" asChild>
                <a href={airtableUrl} target="_blank" rel="noopener noreferrer">
                  <MaterialIcon name="open_in_new" className="text-base" />
                  Open in Airtable
                </a>
              </Button>
            </div>
          </CardAction>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Filters */}
        <div className="flex items-center gap-4 mb-4">
          <div className="relative flex-1 max-w-sm">
            <MaterialIcon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-lg" />
            <Input
              placeholder="Search..."
              className="pl-10"
            />
          </div>
          {stepId === 1 && (
            <div className="flex gap-2">
              <Badge variant="outline" className="cursor-pointer hover:bg-muted">All (47)</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-muted">Slot 1 (8)</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-muted">Slot 2 (12)</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-muted">Slot 3 (10)</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-muted">Slot 4 (9)</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-muted">Slot 5 (8)</Badge>
            </div>
          )}
        </div>

        {/* Data Table - varies by step */}
        {stepId === 1 && <PreFilterTable />}
        {stepId === 2 && <SelectedSlotsTable />}
        {stepId === 3 && <DecorationTable />}
        {stepId === 4 && <IssuesTable />}
        {stepId === 5 && <IssuesArchiveTable />}

        {/* Pagination */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <span className="text-sm text-muted-foreground">
            Showing 1-8 of 47
          </span>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" disabled>
              <MaterialIcon name="chevron_left" className="text-lg" />
            </Button>
            <span className="text-sm font-medium px-2">1</span>
            <Button variant="outline" size="sm">
              <MaterialIcon name="chevron_right" className="text-lg" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function PreFilterTable() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-24">Story ID</TableHead>
          <TableHead>Headline</TableHead>
          <TableHead className="w-16 text-center">Slot</TableHead>
          <TableHead className="w-20 text-right">Score</TableHead>
          <TableHead className="w-24">Date</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {mockPreFilterData.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs text-muted-foreground">
              {row.storyID}
            </TableCell>
            <TableCell className="font-medium">{row.headline}</TableCell>
            <TableCell className="text-center">
              <Badge variant="outline" className="font-mono">
                {row.slot}
              </Badge>
            </TableCell>
            <TableCell className="text-right font-mono">{row.score}</TableCell>
            <TableCell className="text-muted-foreground">{row.date}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function SelectedSlotsTable() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-40">Issue Date</TableHead>
          <TableHead>Subject Line</TableHead>
          <TableHead className="w-28">Status</TableHead>
          <TableHead className="w-24">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {mockSelectedSlotsData.map((row, index) => (
          <TableRow key={index}>
            <TableCell className="font-medium">{row.issue_date}</TableCell>
            <TableCell>{row.subject}</TableCell>
            <TableCell>
              <StatusBadge status={row.status as "decorated" | "sent" | "pending"} />
            </TableCell>
            <TableCell>
              <Button variant="ghost" size="sm">
                <MaterialIcon name="visibility" className="text-lg" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function DecorationTable() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16 text-center">Slot</TableHead>
          <TableHead>Headline</TableHead>
          <TableHead className="w-28">Decorated</TableHead>
          <TableHead className="w-28">Image</TableHead>
          <TableHead className="w-24">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {mockDecorationData.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="text-center">
              <Badge variant="outline" className="font-mono">
                {row.slot}
              </Badge>
            </TableCell>
            <TableCell className="font-medium">{row.headline}</TableCell>
            <TableCell>
              {row.decorated ? (
                <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                  <MaterialIcon name="check" className="text-xs mr-1" />
                  Complete
                </Badge>
              ) : (
                <Badge variant="outline" className="text-muted-foreground">
                  Pending
                </Badge>
              )}
            </TableCell>
            <TableCell>
              <ImageStatusBadge status={row.image_status as "generated" | "pending" | "error"} />
            </TableCell>
            <TableCell>
              <Button variant="ghost" size="sm">
                <MaterialIcon name="visibility" className="text-lg" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function IssuesTable() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-32">Date</TableHead>
          <TableHead>Subject</TableHead>
          <TableHead className="w-28">Status</TableHead>
          <TableHead className="w-32">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {mockSelectedSlotsData.map((row, index) => (
          <TableRow key={index}>
            <TableCell className="font-medium">{row.issue_date.replace("Pivot 5 - ", "")}</TableCell>
            <TableCell>{row.subject}</TableCell>
            <TableCell>
              <StatusBadge status={row.status as "decorated" | "sent" | "pending"} />
            </TableCell>
            <TableCell>
              <div className="flex gap-1">
                <Button variant="ghost" size="sm">
                  <MaterialIcon name="visibility" className="text-lg" />
                </Button>
                <Button variant="ghost" size="sm">
                  <MaterialIcon name="code" className="text-lg" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function IssuesArchiveTable() {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-32">Date</TableHead>
          <TableHead>Subject</TableHead>
          <TableHead className="w-28">Sent Status</TableHead>
          <TableHead className="w-24">Recipients</TableHead>
          <TableHead className="w-24">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {mockSelectedSlotsData.filter(r => r.status === "sent").map((row, index) => (
          <TableRow key={index}>
            <TableCell className="font-medium">{row.issue_date.replace("Pivot 5 - ", "")}</TableCell>
            <TableCell>{row.subject}</TableCell>
            <TableCell>
              <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                <MaterialIcon name="check" className="text-xs mr-1" />
                Sent
              </Badge>
            </TableCell>
            <TableCell className="font-mono text-muted-foreground">12,847</TableCell>
            <TableCell>
              <Button variant="ghost" size="sm">
                <MaterialIcon name="visibility" className="text-lg" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function StatusBadge({ status }: { status: "decorated" | "sent" | "pending" | "compiled" }) {
  const config = {
    decorated: { icon: "check_circle", label: "Decorated", className: "bg-blue-100 text-blue-700 border-blue-200" },
    compiled: { icon: "check_circle", label: "Compiled", className: "bg-blue-100 text-blue-700 border-blue-200" },
    sent: { icon: "send", label: "Sent", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    pending: { icon: "schedule", label: "Pending", className: "bg-gray-100 text-gray-600 border-gray-200" },
  }[status];

  return (
    <Badge variant="outline" className={cn("gap-1", config.className)}>
      <MaterialIcon name={config.icon} className="text-xs" />
      {config.label}
    </Badge>
  );
}

function ImageStatusBadge({ status }: { status: "generated" | "pending" | "error" }) {
  const config = {
    generated: { icon: "image", label: "Generated", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    pending: { icon: "hourglass_empty", label: "Pending", className: "bg-gray-100 text-gray-600 border-gray-200" },
    error: { icon: "error", label: "Error", className: "bg-red-100 text-red-700 border-red-200" },
  }[status];

  return (
    <Badge variant="outline" className={cn("gap-1", config.className)}>
      <MaterialIcon name={config.icon} className="text-xs" />
      {config.label}
    </Badge>
  );
}
