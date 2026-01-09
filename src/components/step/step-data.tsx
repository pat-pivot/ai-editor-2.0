"use client";

import { useState, useEffect, useMemo } from "react";
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
import { formatDateET } from "@/lib/date-utils";
import {
  RefreshCw,
  ExternalLink,
  Search,
  AlertCircle,
  Inbox,
  ChevronsUpDown,
  ArrowUp,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  Eye,
  Check,
  Code,
  CheckCircle,
  Send,
  Clock,
  Image,
  Hourglass,
} from "lucide-react";

interface StepDataProps {
  stepId: number;
  tableName: string;
  tableId: string;
  baseId: string;
}

interface PreFilterEntry {
  id: string;
  storyId: string;
  pivotId: string;
  headline: string;
  originalUrl: string;
  sourceId: string;
  datePublished: string;
  datePrefiltered: string;
  slot: number;
}

// Matches Story interface from src/lib/airtable.ts
interface NewsletterStory {
  id: string;
  storyId: string;
  pivotId: string;
  headline: string;
  source: string;
  date: string;
  eligibleSlots: number[];
  selected: boolean;
  selectedSlot?: number;
}

export function StepData({ stepId, tableName, tableId, baseId }: StepDataProps) {
  const airtableUrl = `https://airtable.com/${baseId}/${tableId}`;
  const [preFilterData, setPreFilterData] = useState<PreFilterEntry[]>([]);
  const [newsletterStories, setNewsletterStories] = useState<NewsletterStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 50; // Show 50 records per page

  // Pre-Filter sorting state (moved here from PreFilterTable to sort BEFORE pagination)
  const [preFilterSortField, setPreFilterSortField] = useState<"slot" | "date" | null>("date");
  const [preFilterSortDirection, setPreFilterSortDirection] = useState<"asc" | "desc">("desc");

  // Fetch data from API based on step
  const fetchData = async (forceRefresh: boolean = false) => {
    // Only fetch for Step 0 (Newsletter Stories) and Step 1 (Pre-Filter)
    if (stepId !== 0 && stepId !== 1) return;

    setLoading(true);
    setError(null);
    try {
      if (stepId === 0) {
        // Newsletter Stories (Step 0)
        const url = forceRefresh
          ? "/api/stories?type=stories&refresh=true"
          : "/api/stories?type=stories";
        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch newsletter stories");
        const data = await response.json();
        setNewsletterStories(data.stories || []);
      } else if (stepId === 1) {
        // Pre-Filter Log (Step 1)
        const url = forceRefresh
          ? "/api/stories?type=prefilter&refresh=true"
          : "/api/stories?type=prefilter";
        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch data");
        const data = await response.json();
        setPreFilterData(data.stories || []);
      }
      setLastSync(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [stepId]);

  // Listen for job completion to auto-refresh data with cache bypass
  useEffect(() => {
    const handleJobComplete = (event: Event) => {
      const customEvent = event as CustomEvent<{ stepId: number }>;
      if (customEvent.detail?.stepId === stepId) {
        // Force refresh to bypass cache and get fresh Airtable data
        fetchData(true);
      }
    };

    window.addEventListener("jobCompleted", handleJobComplete);
    return () => window.removeEventListener("jobCompleted", handleJobComplete);
  }, [stepId]);

  // Calculate slot counts
  const slotCounts = useMemo(() => {
    const counts: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    preFilterData.forEach((entry) => {
      if (entry.slot >= 1 && entry.slot <= 5) {
        counts[entry.slot]++;
      }
    });
    return counts;
  }, [preFilterData]);

  // Filter Pre-Filter data by slot only (Step 1) - search bar removed
  const filteredPreFilterData = useMemo(() => {
    let data = preFilterData;

    if (selectedSlot !== null) {
      data = data.filter((entry) => entry.slot === selectedSlot);
    }

    return data;
  }, [preFilterData, selectedSlot]);

  // Sort Pre-Filter data BEFORE pagination (fixes sorting across all pages)
  const sortedPreFilterData = useMemo(() => {
    if (!preFilterSortField) return filteredPreFilterData;

    return [...filteredPreFilterData].sort((a, b) => {
      if (preFilterSortField === "slot") {
        const diff = a.slot - b.slot;
        return preFilterSortDirection === "asc" ? diff : -diff;
      } else {
        // Sort by date
        const dateA = new Date(a.datePublished || 0).getTime();
        const dateB = new Date(b.datePublished || 0).getTime();
        const diff = dateA - dateB;
        return preFilterSortDirection === "asc" ? diff : -diff;
      }
    });
  }, [filteredPreFilterData, preFilterSortField, preFilterSortDirection]);

  // Handler for Pre-Filter sort
  const handlePreFilterSort = (field: "slot" | "date") => {
    if (preFilterSortField === field) {
      setPreFilterSortDirection(preFilterSortDirection === "asc" ? "desc" : "asc");
    } else {
      setPreFilterSortField(field);
      setPreFilterSortDirection(field === "slot" ? "asc" : "desc");
    }
    setCurrentPage(1); // Reset to first page when sorting changes
  };

  // Filter Newsletter Stories by search (Step 0)
  const filteredNewsletterStories = useMemo(() => {
    let data = newsletterStories;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      data = data.filter((entry) =>
        entry.headline.toLowerCase().includes(query) ||
        entry.pivotId.toLowerCase().includes(query) ||
        entry.storyId.toLowerCase().includes(query) ||
        entry.source.toLowerCase().includes(query)
      );
    }

    return data;
  }, [newsletterStories, searchQuery]);

  // Get active data based on step (use sortedPreFilterData for Step 1)
  const activeData = stepId === 0 ? filteredNewsletterStories : sortedPreFilterData;

  // Paginate filtered data
  const paginatedData = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return activeData.slice(startIndex, endIndex);
  }, [activeData, currentPage, pageSize]);

  const totalPages = Math.ceil(activeData.length / pageSize);

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedSlot, searchQuery, stepId]);

  const formatLastSync = () => {
    if (!lastSync) return "Never";
    const diff = Math.floor((Date.now() - lastSync.getTime()) / 1000);
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
    return lastSync.toLocaleTimeString();
  };

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
                Last sync: {formatLastSync()}
              </span>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => fetchData(true)}
                disabled={loading}
              >
                <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
                {loading ? "Syncing..." : "Sync Now"}
              </Button>
              <Button variant="outline" size="sm" className="gap-2" asChild>
                <a href={airtableUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4" />
                  Open in Airtable
                </a>
              </Button>
            </div>
          </CardAction>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {/* Filters - Only show search bar for Step 0 */}
        <div className="flex items-center gap-4 mb-4">
          {stepId === 0 && (
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search headlines, story IDs..."
                className="pl-10"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          )}
          {stepId === 1 && (
            <div className="flex gap-2">
              <Badge
                variant="outline"
                className={cn(
                  "cursor-pointer hover:bg-muted",
                  selectedSlot === null && "bg-primary text-primary-foreground hover:bg-primary/90"
                )}
                onClick={() => setSelectedSlot(null)}
              >
                All ({preFilterData.length})
              </Badge>
              {[1, 2, 3, 4, 5].map((slot) => (
                <Badge
                  key={slot}
                  variant="outline"
                  className={cn(
                    "cursor-pointer hover:bg-muted",
                    selectedSlot === slot && "bg-primary text-primary-foreground hover:bg-primary/90"
                  )}
                  onClick={() => setSelectedSlot(slot)}
                >
                  Slot {slot} ({slotCounts[slot]})
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Error State */}
        {error && (
          <div className="p-4 mb-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Subheader for Step 0 */}
        {stepId === 0 && (
          <p className="text-sm text-muted-foreground mb-4 -mt-2">
            Stories available for newsletter selection. Click any row to view in Airtable.
          </p>
        )}

        {/* Subheader for Step 1 */}
        {stepId === 1 && (
          <p className="text-sm text-muted-foreground mb-4 -mt-2">
            Stories prefiltered in the past 7 days. Click any row to view in Airtable.
          </p>
        )}

        {/* Data Table - varies by step */}
        {stepId === 0 && <NewsletterStoriesTable data={paginatedData as NewsletterStory[]} loading={loading} baseId={baseId} tableId={tableId} />}
        {stepId === 1 && <PreFilterTable
          data={paginatedData as PreFilterEntry[]}
          loading={loading}
          baseId={baseId}
          tableId={tableId}
          sortField={preFilterSortField}
          sortDirection={preFilterSortDirection}
          onSort={handlePreFilterSort}
        />}
        {stepId === 2 && <SelectedSlotsTable />}
        {stepId === 3 && <DecorationTable />}
        {stepId === 4 && <IssuesTable />}
        {stepId === 5 && <IssuesArchiveTable />}

        {/* Pagination */}
        <div className="flex items-center justify-between mt-4 pt-4 border-t">
          <span className="text-sm text-muted-foreground">
            Showing {paginatedData.length > 0 ? ((currentPage - 1) * pageSize + 1) : 0}
            -{Math.min(currentPage * pageSize, activeData.length)} of {activeData.length} records
            {stepId === 1 && selectedSlot !== null && ` (filtered from ${preFilterData.length})`}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm font-medium px-2">
              Page {currentPage} of {Math.max(1, totalPages)}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface PreFilterTableProps {
  data: PreFilterEntry[];
  loading: boolean;
  baseId: string;
  tableId: string;
  sortField: "slot" | "date" | null;
  sortDirection: "asc" | "desc";
  onSort: (field: "slot" | "date") => void;
}

function PreFilterTable({ data, loading, baseId, tableId, sortField, sortDirection, onSort }: PreFilterTableProps) {
  // Sorting is now handled by parent component (StepData) - we just display the pre-sorted data

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 text-muted-foreground animate-spin" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Inbox className="h-10 w-10 mb-2" />
        <p>No pre-filter records found (past 7 days)</p>
      </div>
    );
  }

  const SortIndicator = ({ field }: { field: "slot" | "date" }) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="h-3 w-3 opacity-50" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="h-3 w-3" />
    ) : (
      <ArrowDown className="h-3 w-3" />
    );
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="border-r border-zinc-200">Headline</TableHead>
          <TableHead className="w-28 border-r border-zinc-200">Source</TableHead>
          <TableHead
            className="w-20 text-center cursor-pointer hover:bg-muted/50 select-none"
            onClick={() => onSort("slot")}
          >
            <div className="flex items-center justify-center gap-1">
              Slot
              <SortIndicator field="slot" />
            </div>
          </TableHead>
          <TableHead
            className="w-44 cursor-pointer hover:bg-muted/50 select-none"
            onClick={() => onSort("date")}
          >
            <div className="flex items-center gap-1">
              Date Original Published
              <SortIndicator field="date" />
            </div>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow
            key={row.id}
            className="hover:bg-muted/50"
          >
            <TableCell className="border-r border-zinc-200">
              <a
                href={`https://airtable.com/${baseId}/${tableId}/${row.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 hover:underline line-clamp-2 flex items-start gap-1"
              >
                {row.headline}
                <ExternalLink className="h-3 w-3 flex-shrink-0 mt-1" />
              </a>
            </TableCell>
            <TableCell className="text-xs text-muted-foreground border-r border-zinc-200">
              {row.sourceId || "—"}
            </TableCell>
            <TableCell className="text-center">
              <Badge variant="outline" className="font-mono">
                {row.slot}
              </Badge>
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {formatDateET(row.datePublished)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// Newsletter Stories table for Step 0
function NewsletterStoriesTable({ data, loading, baseId, tableId }: { data: NewsletterStory[]; loading: boolean; baseId: string; tableId: string }) {
  const [sortField, setSortField] = useState<"slots" | "date" | null>("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const handleSort = (field: "slots" | "date") => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortedData = useMemo(() => {
    if (!sortField) return data;

    return [...data].sort((a, b) => {
      if (sortField === "slots") {
        // Sort by number of eligible slots
        const diff = (a.eligibleSlots?.length || 0) - (b.eligibleSlots?.length || 0);
        return sortDirection === "asc" ? diff : -diff;
      } else {
        const dateA = new Date(a.date || 0).getTime();
        const dateB = new Date(b.date || 0).getTime();
        const diff = dateA - dateB;
        return sortDirection === "asc" ? diff : -diff;
      }
    });
  }, [data, sortField, sortDirection]);

  const formatDate = (dateString: string) => {
    if (!dateString) return "—";
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
      });
    } catch {
      return dateString;
    }
  };

  const openInAirtable = (recordId: string) => {
    const url = `https://airtable.com/${baseId}/${tableId}/${recordId}`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 text-muted-foreground animate-spin" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Inbox className="h-10 w-10 mb-2" />
        <p>No newsletter stories found</p>
      </div>
    );
  }

  const SortIndicator = ({ field }: { field: "slots" | "date" }) => {
    if (sortField !== field) {
      return <ChevronsUpDown className="h-3 w-3 opacity-50" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp className="h-3 w-3" />
    ) : (
      <ArrowDown className="h-3 w-3" />
    );
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-28">Story ID</TableHead>
          <TableHead>Headline</TableHead>
          <TableHead className="w-24">Source</TableHead>
          <TableHead
            className="w-28 cursor-pointer hover:bg-muted/50 select-none"
            onClick={() => handleSort("slots")}
          >
            <div className="flex items-center gap-1">
              Slots
              <SortIndicator field="slots" />
            </div>
          </TableHead>
          <TableHead
            className="w-32 cursor-pointer hover:bg-muted/50 select-none"
            onClick={() => handleSort("date")}
          >
            <div className="flex items-center gap-1">
              Date
              <SortIndicator field="date" />
            </div>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedData.map((row) => (
          <TableRow
            key={row.id}
            className="cursor-pointer hover:bg-muted/50"
            onClick={() => openInAirtable(row.id)}
          >
            <TableCell className="font-mono text-xs text-muted-foreground">
              {row.storyId || row.pivotId || "—"}
            </TableCell>
            <TableCell className="font-medium">
              {row.headline || "Untitled"}
            </TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {row.source || "—"}
            </TableCell>
            <TableCell>
              <div className="flex gap-1 flex-wrap">
                {(row.eligibleSlots || []).map((slot) => (
                  <Badge key={slot} variant="outline" className="font-mono text-xs">
                    {slot}
                  </Badge>
                ))}
              </div>
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {formatDate(row.date)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// Placeholder tables for other steps (these would also need real data integration)
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
                <Eye className="h-4 w-4" />
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
                <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 gap-1">
                  <Check className="h-3 w-3" />
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
                <Eye className="h-4 w-4" />
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
                  <Eye className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm">
                  <Code className="h-4 w-4" />
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
              <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 gap-1">
                <Check className="h-3 w-3" />
                Sent
              </Badge>
            </TableCell>
            <TableCell className="font-mono text-muted-foreground">12,847</TableCell>
            <TableCell>
              <Button variant="ghost" size="sm">
                <Eye className="h-4 w-4" />
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
    decorated: { label: "Decorated", className: "bg-blue-100 text-blue-700 border-blue-200" },
    compiled: { label: "Compiled", className: "bg-blue-100 text-blue-700 border-blue-200" },
    sent: { label: "Sent", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    pending: { label: "Pending", className: "bg-gray-100 text-gray-600 border-gray-200" },
  }[status];

  const IconComponent = {
    decorated: CheckCircle,
    compiled: CheckCircle,
    sent: Send,
    pending: Clock,
  }[status];

  return (
    <Badge variant="outline" className={cn("gap-1", config.className)}>
      <IconComponent className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}

function ImageStatusBadge({ status }: { status: "generated" | "pending" | "error" }) {
  const config = {
    generated: { label: "Generated", className: "bg-emerald-100 text-emerald-700 border-emerald-200" },
    pending: { label: "Pending", className: "bg-gray-100 text-gray-600 border-gray-200" },
    error: { label: "Error", className: "bg-red-100 text-red-700 border-red-200" },
  }[status];

  const IconComponent = {
    generated: Image,
    pending: Hourglass,
    error: AlertCircle,
  }[status];

  return (
    <Badge variant="outline" className={cn("gap-1", config.className)}>
      <IconComponent className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}
