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
import { Loader2, RefreshCw, ExternalLink, ChevronLeft, ChevronRight } from "lucide-react";
import { formatDateET } from "@/lib/date-utils";

const ITEMS_PER_PAGE = 25;

interface Article {
  id: string;
  pivotId: string;
  headline: string;
  sourceName: string;
  originalUrl: string;
  dateIngested: string;
  fitStatus: string;
  interestScore: number | null;
}

// Fit status badge styling
function getFitStatusBadge(status: string) {
  switch (status) {
    case "selected":
      return <Badge className="bg-green-100 text-green-800 text-xs">Selected</Badge>;
    case "approved":
      return <Badge className="bg-blue-100 text-blue-800 text-xs">Approved</Badge>;
    case "skipped_low_score":
      return <Badge className="bg-yellow-100 text-yellow-800 text-xs">Low Score</Badge>;
    case "rejected":
      return <Badge className="bg-red-100 text-red-800 text-xs">Rejected</Badge>;
    default:
      return status ? <Badge variant="outline" className="text-xs">{status}</Badge> : null;
  }
}

export function ArticlesTable() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchArticles = async (skipCache = false) => {
    try {
      if (skipCache) setRefreshing(true);
      else setLoading(true);
      setError(null);

      const url = `/api/airtable/articles?limit=100${skipCache ? "&refresh=true" : ""}`;
      const response = await fetch(url);
      const data = await response.json();

      if (data.error) {
        setError(data.error);
      } else {
        setArticles(data.articles || []);
        setCurrentPage(1); // Reset to first page on refresh
      }
    } catch (err) {
      console.error("Error fetching articles:", err);
      setError("Failed to fetch articles");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Pagination calculations
  const totalPages = Math.ceil(articles.length / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  const paginatedArticles = articles.slice(startIndex, endIndex);

  useEffect(() => {
    fetchArticles();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
          <span className="ml-2 text-zinc-500">Loading articles...</span>
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
              onClick={() => fetchArticles(true)}
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
            Showing {startIndex + 1}-{Math.min(endIndex, articles.length)} of {articles.length} articles
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchArticles(true)}
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
                <TableHead className="w-[10%]">Pivot ID</TableHead>
                <TableHead className="w-[35%]">Headline</TableHead>
                <TableHead className="w-[12%]">Source</TableHead>
                <TableHead className="w-[10%]">Status</TableHead>
                <TableHead className="w-[8%]">Score</TableHead>
                <TableHead className="w-[5%]">Link</TableHead>
                <TableHead className="w-[20%]">Date Ingested</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedArticles.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-zinc-500 py-8">
                    No articles found
                  </TableCell>
                </TableRow>
              ) : (
                paginatedArticles.map((article) => (
                  <TableRow key={article.id}>
                    <TableCell>
                      <span className="text-xs font-mono text-zinc-500">{article.pivotId}</span>
                    </TableCell>
                    <TableCell className="max-w-[300px]">
                      <span className="line-clamp-2 text-sm">{article.headline}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-zinc-600">{article.sourceName}</span>
                    </TableCell>
                    <TableCell>
                      {getFitStatusBadge(article.fitStatus)}
                    </TableCell>
                    <TableCell>
                      {article.interestScore !== null && (
                        <span className="text-sm text-zinc-600">{article.interestScore}</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {article.originalUrl && (
                        <a
                          href={article.originalUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center text-blue-600 hover:text-blue-800 text-sm"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-zinc-500">
                        {formatDateET(article.dateIngested)}
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
            href="https://airtable.com/appglKSJZxmA9iHpl/tblMfRgSNSyoRIhx1"
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
