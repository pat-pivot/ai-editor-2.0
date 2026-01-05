/**
 * AI Editor 2.0 - Airtable Articles API
 *
 * GET /api/airtable/articles
 *   Returns recently ingested articles from the AI Editor 2.0 "Articles - All Ingested" table.
 *   Table ID: tblMfRgSNSyoRIhx1 in base appglKSJZxmA9iHpl
 *
 * Query Parameters:
 *   - limit: Maximum number of records (default: 50)
 *   - refresh: Set to 'true' to skip cache
 *
 * Returns:
 * {
 *   "articles": [
 *     {
 *       "id": "recXXX",
 *       "pivotId": "p_abc123",
 *       "headline": "Article title...",
 *       "sourceName": "Reuters",
 *       "originalUrl": "https://...",
 *       "dateIngested": "2025-01-05T14:30:00Z",
 *       "fitStatus": "selected|approved|skipped_low_score|rejected",
 *       "interestScore": 75
 *     }
 *   ]
 * }
 */

import { NextRequest, NextResponse } from "next/server";
import { getArticles } from "@/lib/airtable";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const limitParam = searchParams.get("limit");
  const refresh = searchParams.get("refresh") === "true";

  const limit = limitParam ? parseInt(limitParam, 10) : 50;

  try {
    const articles = await getArticles(limit, refresh);

    return NextResponse.json({ articles });
  } catch (error) {
    console.error("[Airtable Articles API] Error:", error);

    const errorMessage = error instanceof Error ? error.message : "Unknown error";

    // Check for configuration errors
    if (errorMessage.includes("not configured")) {
      return NextResponse.json({
        articles: [],
        message: "Airtable not configured. Set AIRTABLE_API_KEY and AI_EDITOR_BASE_ID.",
      });
    }

    return NextResponse.json(
      { error: "Failed to fetch articles", details: errorMessage },
      { status: 500 }
    );
  }
}
