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
  Image,
  Hourglass,
  CheckCircle,
  Send,
  Clock,
  Pencil,
  Check,
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

// Airtable constants
const AI_EDITOR_BASE_ID = "appglKSJZxmA9iHpl";
const SELECTED_SLOTS_TABLE_ID = "tblzt2z7r512Kto3O";
const DECORATION_TABLE_ID = "tbla16LJCf5Z6cRn3";

// Interfaces for API responses
interface SelectedSlotsIssue {
  id: string;
  issueId: number;
  issueDate: string;
  subjectLine: string;
  status: string;
  slots: Array<{
    slot: number;
    headline: string;
    storyId: string;
    pivotId: string;
    source: string;
  }>;
}

interface DecorationEntry {
  id: string;
  storyId: string;
  issueId: string;
  issueDate: string;
  slot: number;
  headline: string;
  aiDek: string;
  label: string;
  b1: string;
  b2: string;
  b3: string;
  imageStatus: string;
  imageUrl: string;
  pivotnewsUrl: string;
}

/**
 * Format issue date from ISO format to human-readable format
 * e.g., "2026-01-12" -> "January 12th, 2026"
 */
function formatIssueDateHuman(dateString: string): string {
  if (!dateString) return "—";

  // Handle both "2026-01-12" ISO format and "Jan 12" short format
  const date = new Date(dateString);
  if (isNaN(date.getTime())) {
    // If parsing fails, return as-is (might be "Jan 09" format already)
    return dateString;
  }

  const day = date.getUTCDate();
  const suffix =
    day === 1 || day === 21 || day === 31
      ? "st"
      : day === 2 || day === 22
      ? "nd"
      : day === 3 || day === 23
      ? "rd"
      : "th";

  const formatted = date.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });

  // Replace the day number with day + suffix
  return formatted.replace(/(\d+)/, `$1${suffix}`);
}

function SelectedSlotsTable() {
  const [issues, setIssues] = useState<SelectedSlotsIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentIssueIndex, setCurrentIssueIndex] = useState(0);
  const [editingSubject, setEditingSubject] = useState<string>("");
  const [isEditingSubject, setIsEditingSubject] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveTimeout, setSaveTimeout] = useState<NodeJS.Timeout | null>(null);

  const fetchIssues = async (skipCache = false) => {
    try {
      setLoading(true);
      setError(null);
      const url = `/api/airtable/selected-slots?limit=20${skipCache ? "&refresh=true" : ""}`;
      const response = await fetch(url);
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setIssues(data.issues || []);
        if (data.issues?.length > 0) {
          setEditingSubject(data.issues[0].subjectLine || "");
        }
      }
    } catch (err) {
      console.error("Error fetching selected slots:", err);
      setError("Failed to fetch selected slots");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIssues();
  }, []);

  // Update editing subject when changing issues and reset edit mode
  useEffect(() => {
    if (issues[currentIssueIndex]) {
      setEditingSubject(issues[currentIssueIndex].subjectLine || "");
      setIsEditingSubject(false); // Exit edit mode when switching issues
    }
  }, [currentIssueIndex, issues]);

  // Clear pending save timeout when switching issues
  useEffect(() => {
    return () => {
      if (saveTimeout) {
        clearTimeout(saveTimeout);
      }
    };
  }, [currentIssueIndex, saveTimeout]);

  // Debounced save for subject line
  const handleSubjectChange = (value: string) => {
    setEditingSubject(value);

    // Clear existing timeout
    if (saveTimeout) {
      clearTimeout(saveTimeout);
    }

    // Set new timeout for auto-save after 500ms
    const timeout = setTimeout(() => {
      saveSubjectLine(value);
    }, 500);
    setSaveTimeout(timeout);
  };

  const saveSubjectLine = async (subjectLine: string) => {
    const currentIssue = issues[currentIssueIndex];
    if (!currentIssue) return;

    // Don't save if value hasn't changed
    if (subjectLine === currentIssue.subjectLine) return;

    try {
      setIsSaving(true);
      const response = await fetch("/api/airtable/selected-slots", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recordId: currentIssue.id,
          subject_line: subjectLine,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save");
      }

      // Update local state optimistically
      setIssues((prev) =>
        prev.map((issue, idx) =>
          idx === currentIssueIndex
            ? { ...issue, subjectLine }
            : issue
        )
      );
    } catch (err) {
      console.error("Error saving subject line:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const currentIssue = issues[currentIssueIndex];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 text-muted-foreground animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="h-10 w-10 mb-2 text-red-500" />
        <p className="text-red-500">{error}</p>
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={() => fetchIssues(true)}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Inbox className="h-10 w-10 mb-2" />
        <p>No selected slots issues found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Subject Line (TOP LEFT) */}
      <div className="flex items-center gap-4 p-4 bg-muted/30 rounded-lg">
        <div className="flex-1 flex items-center gap-2">
          <span className="text-sm font-semibold whitespace-nowrap">Subject:</span>
          {isEditingSubject ? (
            <>
              <Input
                value={editingSubject}
                onChange={(e) => setEditingSubject(e.target.value)}
                placeholder="Enter subject line..."
                className="flex-1"
                autoFocus
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  saveSubjectLine(editingSubject);
                  setIsEditingSubject(false);
                }}
                disabled={isSaving}
              >
                {isSaving ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Check className="h-4 w-4 text-green-600" />
                )}
              </Button>
            </>
          ) : (
            <>
              <span className="flex-1 text-sm truncate">
                {currentIssue?.subjectLine || "No subject line"}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditingSubject(true)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Slots Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-20 text-center">Slot</TableHead>
            <TableHead>Headline</TableHead>
            <TableHead className="w-32">Source</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {currentIssue?.slots.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                No slots populated for this issue
              </TableCell>
            </TableRow>
          ) : (
            currentIssue?.slots.map((slot) => (
              <TableRow key={`${currentIssue.id}-slot-${slot.slot}`}>
                <TableCell className="text-center">
                  <Badge variant="outline" className="font-mono">
                    {slot.slot}
                  </Badge>
                </TableCell>
                <TableCell>
                  <a
                    href={`https://airtable.com/${AI_EDITOR_BASE_ID}/${SELECTED_SLOTS_TABLE_ID}/${currentIssue.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline flex items-start gap-1"
                  >
                    {slot.headline || "—"}
                    <ExternalLink className="h-3 w-3 flex-shrink-0 mt-1" />
                  </a>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {slot.source || "—"}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* Pagination (BOTTOM RIGHT) */}
      <div className="flex items-center justify-end gap-4 pt-4 mt-4 border-t">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={currentIssueIndex <= 0}
            onClick={() => {
              // Clear any pending save when navigating
              if (saveTimeout) clearTimeout(saveTimeout);
              setCurrentIssueIndex((i) => Math.max(0, i - 1));
            }}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium min-w-[180px] text-center">
            {formatIssueDateHuman(currentIssue?.issueDate || "")}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={currentIssueIndex >= issues.length - 1}
            onClick={() => {
              // Clear any pending save when navigating
              if (saveTimeout) clearTimeout(saveTimeout);
              setCurrentIssueIndex((i) => Math.min(issues.length - 1, i + 1));
            }}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <span className="text-xs text-muted-foreground ml-2">
            Issue {currentIssueIndex + 1} of {issues.length}
          </span>
        </div>
      </div>
    </div>
  );
}

function DecorationTable() {
  const [decorations, setDecorations] = useState<DecorationEntry[]>([]);
  const [uniqueIssueDates, setUniqueIssueDates] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIssueDate, setSelectedIssueDate] = useState<string>("");
  const [imageModalUrl, setImageModalUrl] = useState<string | null>(null);

  const fetchDecorations = async (skipCache = false) => {
    try {
      setLoading(true);
      setError(null);
      const url = `/api/airtable/decorations?limit=200${skipCache ? "&refresh=true" : ""}`;
      const response = await fetch(url);
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setDecorations(data.decorations || []);
        setUniqueIssueDates(data.uniqueIssueDates || []);
        // Select the first (newest) issue date by default
        if (data.uniqueIssueDates?.length > 0 && !selectedIssueDate) {
          setSelectedIssueDate(data.uniqueIssueDates[0]);
        }
      }
    } catch (err) {
      console.error("Error fetching decorations:", err);
      setError("Failed to fetch decorations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecorations();
  }, []);

  // Filter decorations by selected issue date
  const filteredDecorations = useMemo(() => {
    if (!selectedIssueDate) return decorations;
    return decorations.filter((d) => d.issueDate === selectedIssueDate);
  }, [decorations, selectedIssueDate]);

  // Get current issue date index for navigation
  const currentIssueDateIndex = uniqueIssueDates.indexOf(selectedIssueDate);

  const handlePrevIssue = () => {
    if (currentIssueDateIndex > 0) {
      setSelectedIssueDate(uniqueIssueDates[currentIssueDateIndex - 1]);
    }
  };

  const handleNextIssue = () => {
    if (currentIssueDateIndex < uniqueIssueDates.length - 1) {
      setSelectedIssueDate(uniqueIssueDates[currentIssueDateIndex + 1]);
    }
  };

  // Get label badge color
  const getLabelBadgeClass = (label: string) => {
    const labelColors: Record<string, string> = {
      WORK: "bg-blue-100 text-blue-700 border-blue-200",
      ENTERPRISE: "bg-purple-100 text-purple-700 border-purple-200",
      POLICY: "bg-amber-100 text-amber-700 border-amber-200",
      HEALTH: "bg-emerald-100 text-emerald-700 border-emerald-200",
      EDUCATION: "bg-cyan-100 text-cyan-700 border-cyan-200",
      FUNDING: "bg-green-100 text-green-700 border-green-200",
      ETHICS: "bg-red-100 text-red-700 border-red-200",
      CONSUMER: "bg-pink-100 text-pink-700 border-pink-200",
      CREATIVE: "bg-indigo-100 text-indigo-700 border-indigo-200",
    };
    return labelColors[label?.toUpperCase()] || "bg-gray-100 text-gray-700 border-gray-200";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="h-8 w-8 text-muted-foreground animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <AlertCircle className="h-10 w-10 mb-2 text-red-500" />
        <p className="text-red-500">{error}</p>
        <Button
          variant="outline"
          size="sm"
          className="mt-4"
          onClick={() => fetchDecorations(true)}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Retry
        </Button>
      </div>
    );
  }

  if (decorations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Inbox className="h-10 w-10 mb-2" />
        <p>No decorated stories found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Issue Date Navigation */}
      <div className="flex items-center justify-between gap-4 p-4 bg-muted/30 rounded-lg">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={currentIssueDateIndex <= 0}
            onClick={handlePrevIssue}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm font-medium min-w-[100px] text-center">
            {selectedIssueDate || "—"}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={currentIssueDateIndex >= uniqueIssueDates.length - 1}
            onClick={handleNextIssue}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <span className="text-xs text-muted-foreground ml-2">
            Issue {currentIssueDateIndex + 1} of {uniqueIssueDates.length}
          </span>
        </div>
        <span className="text-sm text-muted-foreground">
          {filteredDecorations.length} stories
        </span>
      </div>

      {/* Decorations Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-20 text-center">Slot</TableHead>
            <TableHead className="w-[30%]">Headline</TableHead>
            <TableHead className="w-[25%]">AI Deck</TableHead>
            <TableHead className="w-24">Label</TableHead>
            <TableHead className="w-28">Status</TableHead>
            <TableHead className="w-20 text-center">Preview</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredDecorations.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                No decorated stories for this issue
              </TableCell>
            </TableRow>
          ) : (
            filteredDecorations.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="text-center">
                  <Badge variant="outline" className="font-mono">
                    {row.slot || "—"}
                  </Badge>
                </TableCell>
                <TableCell>
                  <a
                    href={`https://airtable.com/${AI_EDITOR_BASE_ID}/${DECORATION_TABLE_ID}/${row.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-600 hover:text-blue-800 hover:underline line-clamp-2 flex items-start gap-1"
                  >
                    {row.headline || "—"}
                    <ExternalLink className="h-3 w-3 flex-shrink-0 mt-1" />
                  </a>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  <span className="line-clamp-2">{row.aiDek || "—"}</span>
                </TableCell>
                <TableCell>
                  {row.label ? (
                    <Badge variant="outline" className={cn("text-xs", getLabelBadgeClass(row.label))}>
                      {row.label}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell>
                  <ImageStatusBadge
                    status={
                      row.imageStatus === "generated"
                        ? "generated"
                        : row.imageStatus === "needs_image"
                        ? "pending"
                        : "pending"
                    }
                  />
                </TableCell>
                <TableCell className="text-center">
                  {row.imageUrl ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setImageModalUrl(row.imageUrl)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* Link to Airtable */}
      <div className="text-center pt-2">
        <a
          href={`https://airtable.com/${AI_EDITOR_BASE_ID}/${DECORATION_TABLE_ID}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-zinc-400 hover:text-zinc-600 transition-colors"
        >
          View full table in Airtable &rarr;
        </a>
      </div>

      {/* Image Preview Modal */}
      {imageModalUrl && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={() => setImageModalUrl(null)}
        >
          <div
            className="bg-white rounded-lg p-2 max-w-4xl max-h-[90vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-end mb-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setImageModalUrl(null)}
              >
                Close
              </Button>
            </div>
            <img
              src={imageModalUrl}
              alt="Generated image preview"
              className="max-w-full h-auto rounded"
              onError={(e) => {
                (e.target as HTMLImageElement).src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300'%3E%3Crect fill='%23f0f0f0' width='400' height='300'/%3E%3Ctext fill='%23999' font-family='sans-serif' font-size='16' x='50%25' y='50%25' text-anchor='middle' dy='.3em'%3EImage failed to load%3C/text%3E%3C/svg%3E";
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function IssuesTable() {
  // Placeholder for Step 4 - HTML Compile (not yet implemented)
  return (
    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
      <Inbox className="h-10 w-10 mb-2" />
      <p>HTML Compile data integration coming soon</p>
      <p className="text-sm mt-2">Step 4 is not yet implemented</p>
    </div>
  );
}

function IssuesArchiveTable() {
  // Placeholder for Step 5 - Social Sync (not yet implemented)
  return (
    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
      <Inbox className="h-10 w-10 mb-2" />
      <p>Social Sync data integration coming soon</p>
      <p className="text-sm mt-2">Step 5 is not yet implemented</p>
    </div>
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
