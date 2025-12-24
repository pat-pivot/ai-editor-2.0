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
  score: number;
  date: string;
}

export function StepData({ stepId, tableName, tableId, baseId }: StepDataProps) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<PreFilterRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  const airtableUrl = `https://airtable.com/${baseId}/${tableId}`;

  useEffect(() => {
    async function fetchData() {
      if (stepId !== 1) {
        // Only pre-filter has API integration currently
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        const res = await fetch("/api/stories?type=prefilter");
        if (!res.ok) throw new Error("Failed to fetch data");
        const json = await res.json();
        setData(json.stories || []);
      } catch (err) {
        setError("Could not load data from Airtable");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [stepId]);

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
              Check your Airtable connection and try again.
            </p>
          </div>
        ) : stepId === 1 ? (
          data.length > 0 ? (
            <PreFilterTable data={data} />
          ) : (
            <EmptyState
              icon="filter_alt"
              title="No pre-filtered stories yet"
              description="Stories will appear here after the pre-filter job runs."
            />
          )
        ) : (
          <EmptyState
            icon="table_chart"
            title="Data table coming soon"
            description="This table will show data once the pipeline runs. View in Airtable for now."
          />
        )}

        {/* Pagination - only show when there's data */}
        {data.length > 0 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t">
            <span className="text-sm text-muted-foreground">
              Showing 1-{Math.min(data.length, 20)} of {data.length}
            </span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled>
                <MaterialIcon name="chevron_left" className="text-lg" />
              </Button>
              <span className="text-sm font-medium px-2">1</span>
              <Button variant="outline" size="sm" disabled={data.length <= 20}>
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
        {data.slice(0, 20).map((row) => (
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
            <TableCell className="text-right font-mono">{row.score?.toFixed(1) || "-"}</TableCell>
            <TableCell className="text-muted-foreground">{row.date}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
