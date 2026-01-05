"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { formatDateET } from "@/lib/date-utils";

const ITEMS_PER_PAGE = 25;

interface NewsletterSelect {
  id: string;
  issueId: string;
  issueDate: string;
  slot: number;
  headline: string;
  storyId: string;
  pivotId: string;
}

const SLOT_COLORS: Record<number, string> = {
  1: "bg-blue-100 text-blue-800",
  2: "bg-green-100 text-green-800",
  3: "bg-purple-100 text-purple-800",
  4: "bg-orange-100 text-orange-800",
  5: "bg-pink-100 text-pink-800",
};

const SLOT_NAMES: Record<number, string> = {
  1: "Jobs",
  2: "Tier 1 AI",
  3: "Industry",
  4: "Startup",
  5: "Consumer",
};

export function NewsletterSelectsTable() {
  const [selects, setSelects] = useState<NewsletterSelect[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchSelects = async (skipCache = false) => {
    try {
      if (skipCache) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const url = `/api/airtable/newsletter-selects?limit=100${skipCache ? "&refresh=true" : ""}`;
      const response = await fetch(url);
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setSelects(data.selects || []);
        setCurrentPage(1); // Reset to first page on refresh
      }
    } catch (err) {
      console.error("Error fetching newsletter selects:", err);
      setError("Failed to fetch newsletter selects");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Pagination calculations
  const totalPages = Math.ceil(selects.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedSelects = selects.slice(startIndex, endIndex);

  useEffect(() => {
    fetchSelects();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
          <span className="ml-2 text-zinc-500">Loading newsletter selects...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6">
          <div className="text-center text-zinc-500">
            <p className="text-red-500 mb-2">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchSelects(true)}
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-zinc-500">
            Showing {startIndex + 1}-{Math.min(endIndex, selects.length)} of {selects.length} selects
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchSelects(true)}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[15%]">Issue Date</TableHead>
                <TableHead className="w-[10%]">Slot</TableHead>
                <TableHead className="w-[55%]">Headline</TableHead>
                <TableHead className="w-[20%]">Story ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedSelects.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-zinc-500 py-8">
                    No newsletter selects found
                  </TableCell>
                </TableRow>
              ) : (
                paginatedSelects.map((select) => (
                  <TableRow key={select.id}>
                    <TableCell>
                      <span className="text-sm text-zinc-600">
                        {formatDateET(select.issueDate)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge className={SLOT_COLORS[select.slot] || "bg-gray-100 text-gray-800"}>
                        {select.slot}: {SLOT_NAMES[select.slot] || "Unknown"}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[400px]">
                      <span className="line-clamp-2 text-sm">{select.headline}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-zinc-500 font-mono">
                        {select.storyId ? select.storyId.substring(0, 12) + "..." : "-"}
                      </span>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-zinc-500">
              Page {currentPage} of {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4 mr-1" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {/* Link to full Airtable */}
        <div className="mt-4 text-center">
          <a
            href="https://airtable.com/appglKSJZxmA9iHpl/tblzt2z7r512Kto3O"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-zinc-400 hover:text-zinc-600 transition-colors"
          >
            View full table in Airtable &rarr;
          </a>
        </div>
      </CardContent>
    </Card>
  );
}
