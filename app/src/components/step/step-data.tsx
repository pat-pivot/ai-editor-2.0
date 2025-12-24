"use client";

import { useState, useEffect } from "react";
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

interface PreFilterRecord {
  id: string;
  storyId: string;
  headline: string;
  slot: number;
  datePublished: string;
  sourceId?: string;
}

interface SelectedSlotsRecord {
  id: string;
  issueId: string;
  issueDate: string;
  subjectLine: string;
  status: string;
  slots: Array<{
    slot: number;
    headline: string;
    storyId: string;
    pivotId: string;
  }>;
}

interface DecorationRecord {
  id: string;
  storyId: string;
  slotOrder: number;
  headline: string;
  aiDek: string;
  label: string;
  imageStatus: string;
  imageUrl: string;
}

export function StepData({ stepId, tableName, tableId, baseId }: StepDataProps) {
  const [loading, setLoading] = useState(true);
  const [preFilterData, setPreFilterData] = useState<PreFilterRecord[]>([]);
  const [slotsData, setSlotsData] = useState<SelectedSlotsRecord | null>(null);
  const [decorationData, setDecorationData] = useState<DecorationRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Filtering and pagination state
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const airtableUrl = `https://airtable.com/${baseId}/${tableId}`;

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);

        if (stepId === 1) {
          // Pre-Filter Log
          const res = await fetch("/api/stories?type=prefilter");
          if (!res.ok) throw new Error("Failed to fetch pre-filter data");
          const json = await res.json();
          setPreFilterData(json.stories || []);
        } else if (stepId === 2) {
          // Selected Slots
          const res = await fetch("/api/slots");
          if (!res.ok) throw new Error("Failed to fetch selected slots");
          const json = await res.json();
          setSlotsData(json.selectedSlots || null);
        } else if (stepId === 3) {
          // Decorations
          const res = await fetch("/api/decorations");
          if (!res.ok) throw new Error("Failed to fetch decorations");
          const json = await res.json();
          setDecorationData(json.decorations || []);
        }
        // Step 4 and 5 will show empty state with Airtable link for now
      } catch (err) {
        setError("Could not load data from Airtable. Check environment variables.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [stepId]);

  // Filter pre-filter data by selected slot
  const filteredPreFilterData = selectedSlot
    ? preFilterData.filter((item) => item.slot === selectedSlot)
    : preFilterData;

  // Pagination calculations
  const totalFilteredCount = stepId === 1 ? filteredPreFilterData.length
    : stepId === 2 ? (slotsData?.slots?.length || 0)
    : stepId === 3 ? decorationData.length
    : 0;

  const totalPages = Math.ceil(totalFilteredCount / pageSize);
  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;

  // Get paginated data
  const paginatedPreFilterData = filteredPreFilterData.slice(startIndex, endIndex);
  const paginatedDecorationData = decorationData.slice(startIndex, endIndex);

  const hasData = stepId === 1 ? preFilterData.length > 0
    : stepId === 2 ? slotsData !== null
    : stepId === 3 ? decorationData.length > 0
    : false;

  const dataCount = totalFilteredCount;

  // Reset to page 1 when filter changes
  useEffect(() => {
    setCurrentPage(1);
  }, [selectedSlot]);

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
          {/* Slot Filter - only show for Step 1 */}
          {stepId === 1 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Slot:</span>
              <div className="flex gap-1">
                <Button
                  variant={selectedSlot === null ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedSlot(null)}
                  className="px-3"
                >
                  All
                </Button>
                {[1, 2, 3, 4, 5].map((slot) => (
                  <Button
                    key={slot}
                    variant={selectedSlot === slot ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedSlot(slot)}
                    className="px-3"
                  >
                    {slot}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Data Table */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MaterialIcon name="sync" className="text-4xl text-gray-400 mb-3 animate-spin" />
            <p className="text-gray-600 font-medium">Loading data...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MaterialIcon name="error" className="text-4xl text-red-400 mb-3" />
            <p className="text-gray-600 font-medium">{error}</p>
            <p className="text-gray-500 text-sm mt-1">
              Check your Airtable connection and environment variables.
            </p>
          </div>
        ) : stepId === 1 ? (
          paginatedPreFilterData.length > 0 ? (
            <PreFilterTable data={paginatedPreFilterData} />
          ) : filteredPreFilterData.length === 0 && selectedSlot ? (
            <EmptyState
              icon="filter_alt_off"
              title={`No stories for Slot ${selectedSlot}`}
              description="Try selecting a different slot or view all slots."
            />
          ) : (
            <EmptyState
              icon="filter_alt"
              title="No pre-filtered stories yet"
              description="Stories will appear here after the pre-filter job runs."
            />
          )
        ) : stepId === 2 ? (
          slotsData ? (
            <SelectedSlotsTable data={slotsData} />
          ) : (
            <EmptyState
              icon="checklist"
              title="No selected slots yet"
              description="Slots will appear here after the slot selection job runs."
            />
          )
        ) : stepId === 3 ? (
          paginatedDecorationData.length > 0 ? (
            <DecorationTable data={paginatedDecorationData} />
          ) : (
            <EmptyState
              icon="edit_note"
              title="No decorations yet"
              description="Decorations will appear here after the decoration job runs."
            />
          )
        ) : stepId === 4 ? (
          <EmptyState
            icon="code"
            title="Newsletter Issues"
            description="View compiled newsletters in Airtable. API integration coming soon."
          />
        ) : (
          <EmptyState
            icon="send"
            title="Send & Social Archive"
            description="View sent newsletters in Airtable. API integration coming soon."
          />
        )}

        {/* Pagination - only show when there's data */}
        {hasData && dataCount > 0 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <span className="text-sm text-muted-foreground">
              Showing {startIndex + 1}-{Math.min(endIndex, dataCount)} of {dataCount}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              >
                <MaterialIcon name="chevron_left" className="text-lg" />
              </Button>
              <span className="text-sm font-medium px-2">
                {currentPage} / {totalPages || 1}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
              >
                <MaterialIcon name="chevron_right" className="text-lg" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function EmptyState({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <MaterialIcon name={icon} className="text-4xl text-gray-400 mb-3" />
      <p className="text-gray-600 font-medium">{title}</p>
      <p className="text-gray-500 text-sm mt-1">{description}</p>
    </div>
  );
}

function PreFilterTable({ data }: { data: PreFilterRecord[] }) {
  // Format date for display
  const formatDate = (dateStr: string) => {
    if (!dateStr) return "-";
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-24">Story ID</TableHead>
          <TableHead>Headline</TableHead>
          <TableHead className="w-16 text-center">Slot</TableHead>
          <TableHead className="w-28">Published</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="font-mono text-xs text-muted-foreground">
              {row.storyId}
            </TableCell>
            <TableCell className="font-medium">{row.headline}</TableCell>
            <TableCell className="text-center">
              <Badge variant="outline" className="font-mono">
                {row.slot}
              </Badge>
            </TableCell>
            <TableCell className="text-muted-foreground text-sm">
              {formatDate(row.datePublished)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function SelectedSlotsTable({ data }: { data: SelectedSlotsRecord }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
        <div>
          <span className="text-sm text-gray-500">Issue Date:</span>
          <span className="ml-2 font-medium">{data.issueDate || "Not set"}</span>
        </div>
        <div>
          <span className="text-sm text-gray-500">Status:</span>
          <Badge className="ml-2" variant={data.status === "decorated" ? "default" : "secondary"}>
            {data.status || "pending"}
          </Badge>
        </div>
        <div>
          <span className="text-sm text-gray-500">Subject:</span>
          <span className="ml-2 font-medium text-sm">{data.subjectLine || "Not generated"}</span>
        </div>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16 text-center">Slot</TableHead>
            <TableHead>Headline</TableHead>
            <TableHead className="w-32">Story ID</TableHead>
            <TableHead className="w-32">Pivot ID</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.slots.map((slot) => (
            <TableRow key={slot.slot}>
              <TableCell className="text-center">
                <Badge variant="outline" className="font-mono font-bold">
                  {slot.slot}
                </Badge>
              </TableCell>
              <TableCell className="font-medium">
                {slot.headline || <span className="text-gray-400 italic">Not selected</span>}
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {slot.storyId || "-"}
              </TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {slot.pivotId || "-"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function DecorationTable({ data }: { data: DecorationRecord[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16 text-center">Slot</TableHead>
          <TableHead>Headline</TableHead>
          <TableHead className="w-24">Label</TableHead>
          <TableHead className="w-24">Image</TableHead>
          <TableHead className="w-32">Story ID</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((row) => (
          <TableRow key={row.id}>
            <TableCell className="text-center">
              <Badge variant="outline" className="font-mono font-bold">
                {row.slotOrder}
              </Badge>
            </TableCell>
            <TableCell>
              <div className="font-medium">{row.headline}</div>
              {row.aiDek && (
                <div className="text-sm text-gray-500 mt-1 line-clamp-1">{row.aiDek}</div>
              )}
            </TableCell>
            <TableCell>
              <Badge variant="secondary" className="text-xs">
                {row.label || "AI NEWS"}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge
                variant={row.imageStatus === "generated" ? "default" : "secondary"}
                className={cn(
                  "text-xs",
                  row.imageStatus === "generated" && "bg-green-100 text-green-700",
                  row.imageStatus === "pending" && "bg-yellow-100 text-yellow-700",
                  row.imageStatus === "failed" && "bg-red-100 text-red-700"
                )}
              >
                {row.imageStatus || "pending"}
              </Badge>
            </TableCell>
            <TableCell className="font-mono text-xs text-muted-foreground">
              {row.storyId}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
