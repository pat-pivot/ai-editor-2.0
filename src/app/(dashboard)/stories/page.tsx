"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

interface Story {
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

function SlotBadge({ slot }: { slot: number }) {
  const colors: Record<number, string> = {
    1: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    2: "bg-purple-500/20 text-purple-400 border-purple-500/30",
    3: "bg-green-500/20 text-green-400 border-green-500/30",
    4: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    5: "bg-pink-500/20 text-pink-400 border-pink-500/30",
  };

  const labels: Record<number, string> = {
    1: "Jobs/Economy",
    2: "Tier 1 AI",
    3: "Industry",
    4: "Emerging",
    5: "Consumer",
  };

  return (
    <Badge className={colors[slot]}>
      {slot}: {labels[slot]}
    </Badge>
  );
}

export default function StoriesPage() {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterSlot, setFilterSlot] = useState<number | null>(null);

  const fetchStories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch("/api/stories");
      if (!response.ok) {
        throw new Error("Failed to fetch stories");
      }
      const data = await response.json();
      setStories(data.stories || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stories");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStories();
  }, [fetchStories]);

  const filteredStories = stories.filter((story) => {
    const matchesSearch =
      story.headline.toLowerCase().includes(searchQuery.toLowerCase()) ||
      story.source.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesSlot =
      filterSlot === null || story.eligibleSlots.includes(filterSlot);
    return matchesSearch && matchesSlot;
  });

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center h-full">
        <div className="text-zinc-400">Loading stories from Airtable...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <Card className="bg-red-500/10 border-red-500/30">
          <CardContent className="p-6">
            <div className="text-red-400 mb-4">{error}</div>
            <Button onClick={fetchStories} variant="outline" className="border-red-500/30 text-red-400">
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
          <h1 className="text-2xl font-bold text-white">Stories</h1>
          <p className="text-zinc-400 mt-1">
            View and manage newsletter stories from Airtable
          </p>
        </div>
        <Button
          onClick={fetchStories}
          className="bg-orange-500 hover:bg-orange-600 text-white"
        >
          Refresh from Airtable
        </Button>
      </div>

      {/* Filters */}
      <Card className="bg-zinc-900 border-zinc-800 mb-6">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <Input
                placeholder="Search stories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-zinc-400">Filter by slot:</span>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((slot) => (
                  <Button
                    key={slot}
                    variant="outline"
                    size="sm"
                    onClick={() => setFilterSlot(filterSlot === slot ? null : slot)}
                    className={
                      filterSlot === slot
                        ? "bg-orange-500 border-orange-500 text-white"
                        : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"
                    }
                  >
                    {slot}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stories Table */}
      <Card className="bg-zinc-900 border-zinc-800">
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-zinc-400">Headline</TableHead>
              <TableHead className="text-zinc-400">Source</TableHead>
              <TableHead className="text-zinc-400">Date</TableHead>
              <TableHead className="text-zinc-400">Eligible Slots</TableHead>
              <TableHead className="text-zinc-400">Status</TableHead>
              <TableHead className="text-zinc-400 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredStories.length === 0 ? (
              <TableRow className="border-zinc-800">
                <TableCell colSpan={6} className="text-center text-zinc-500 py-8">
                  No stories found
                </TableCell>
              </TableRow>
            ) : (
              filteredStories.map((story) => (
                <TableRow key={story.id} className="border-zinc-800">
                  <TableCell className="max-w-md">
                    <div className="font-medium text-white truncate">
                      {story.headline}
                    </div>
                    <div className="text-xs text-zinc-500">{story.pivotId}</div>
                  </TableCell>
                  <TableCell className="text-zinc-300">{story.source}</TableCell>
                  <TableCell className="text-zinc-400">{story.date}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {story.eligibleSlots.map((slot) => (
                        <SlotBadge key={slot} slot={slot} />
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    {story.selected ? (
                      <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                        Selected (Slot {story.selectedSlot})
                      </Badge>
                    ) : (
                      <Badge className="bg-zinc-500/20 text-zinc-400 border-zinc-500/30">
                        Available
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-zinc-400 hover:text-white"
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4 mt-6">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-white">{stories.length}</div>
            <div className="text-sm text-zinc-400">Total Stories</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-400">
              {stories.filter((s) => s.selected).length}
            </div>
            <div className="text-sm text-zinc-400">Selected for Today</div>
          </CardContent>
        </Card>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-orange-400">
              {stories.filter((s) => !s.selected).length}
            </div>
            <div className="text-sm text-zinc-400">Available</div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
