"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface Source {
  id: string;
  name: string;
  credibilityScore: number;
  storiesCount: number;
  lastUsed: string;
}

function StarRating({
  score,
  onChange,
}: {
  score: number;
  onChange?: (score: number) => void;
}) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          onClick={() => onChange?.(star)}
          className={`h-5 w-5 ${
            star <= score ? "text-orange-400" : "text-zinc-600"
          } ${onChange ? "cursor-pointer hover:text-orange-300" : "cursor-default"}`}
        >
          <svg fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </button>
      ))}
    </div>
  );
}

export default function SourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [newSourceName, setNewSourceName] = useState("");
  const [updating, setUpdating] = useState<string | null>(null);

  const fetchSources = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch("/api/sources");
      if (!response.ok) {
        throw new Error("Failed to fetch sources");
      }
      const data = await response.json();
      setSources(data.sources || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sources");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSources();
  }, [fetchSources]);

  const filteredSources = sources.filter((source) =>
    source.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const updateScore = async (id: string, score: number) => {
    setUpdating(id);
    try {
      const response = await fetch("/api/sources", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, credibilityScore: score }),
      });

      if (!response.ok) {
        throw new Error("Failed to update source");
      }

      setSources((prev) =>
        prev.map((s) => (s.id === id ? { ...s, credibilityScore: score } : s))
      );
    } catch (err) {
      console.error("Error updating source:", err);
    } finally {
      setUpdating(null);
    }
  };

  const addSource = async () => {
    if (!newSourceName.trim()) return;

    try {
      const response = await fetch("/api/sources", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newSourceName.trim(), credibilityScore: 3 }),
      });

      if (!response.ok) {
        throw new Error("Failed to add source");
      }

      const data = await response.json();
      setSources((prev) => [
        ...prev,
        {
          ...data.source,
          storiesCount: 0,
          lastUsed: "Never",
        },
      ]);
      setNewSourceName("");
    } catch (err) {
      console.error("Error adding source:", err);
    }
  };

  const removeSource = async (id: string) => {
    try {
      const response = await fetch(`/api/sources?id=${id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error("Failed to delete source");
      }

      setSources((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      console.error("Error deleting source:", err);
    }
  };

  const averageScore =
    sources.length > 0
      ? sources.reduce((acc, s) => acc + s.credibilityScore, 0) / sources.length
      : 0;

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-zinc-400">Loading sources from Airtable...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <Card className="bg-red-500/10 border-red-500/30">
          <CardContent className="p-6">
            <div className="text-red-400 mb-4">{error}</div>
            <Button onClick={fetchSources} variant="outline" className="border-red-500/30 text-red-400">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Source Credibility</h1>
          <p className="text-zinc-400 mt-1">
            Manage source ratings for pre-filter scoring
          </p>
        </div>
        <Button
          onClick={fetchSources}
          className="bg-orange-500 hover:bg-orange-600 text-white"
        >
          Refresh from Airtable
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-white">{sources.length}</div>
            <div className="text-sm text-zinc-400">Total Sources</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-white">
              {averageScore.toFixed(1)}
            </div>
            <div className="text-sm text-zinc-400">Average Rating</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-400">
              {sources.filter((s) => s.credibilityScore >= 4).length}
            </div>
            <div className="text-sm text-zinc-400">High Credibility</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-orange-400">
              {sources.reduce((acc, s) => acc + (s.storiesCount || 0), 0)}
            </div>
            <div className="text-sm text-zinc-400">Total Stories</div>
          </CardContent>
        </Card>
      </div>

      {/* Add Source */}
      <Card className="bg-zinc-900 border-zinc-800 mb-6">
        <CardHeader className="pb-3">
          <CardTitle className="text-white text-base">Add New Source</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Input
              placeholder="Enter source name..."
              value={newSourceName}
              onChange={(e) => setNewSourceName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addSource()}
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
            />
            <Button
              onClick={addSource}
              className="bg-orange-500 hover:bg-orange-600 text-white"
            >
              Add Source
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Search */}
      <Card className="bg-zinc-900 border-zinc-800 mb-6">
        <CardContent className="p-4">
          <Input
            placeholder="Search sources..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
          />
        </CardContent>
      </Card>

      {/* Sources Table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-zinc-400">Source Name</TableHead>
              <TableHead className="text-zinc-400">Credibility Score</TableHead>
              <TableHead className="text-zinc-400">Stories Count</TableHead>
              <TableHead className="text-zinc-400">Last Used</TableHead>
              <TableHead className="text-zinc-400 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredSources
              .sort((a, b) => b.credibilityScore - a.credibilityScore)
              .map((source) => (
                <TableRow key={source.id} className="border-zinc-800">
                  <TableCell className="font-medium text-white">
                    {source.name}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <StarRating
                        score={source.credibilityScore}
                        onChange={(score) => updateScore(source.id, score)}
                      />
                      {updating === source.id && (
                        <span className="text-xs text-zinc-500">Saving...</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-zinc-300">
                    {source.storiesCount || 0}
                  </TableCell>
                  <TableCell className="text-zinc-400">
                    {source.lastUsed || "Never"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeSource(source.id)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    >
                      Remove
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  );
}
