import { NextRequest, NextResponse } from "next/server";
import {
  getPromptVersions,
  rollbackPrompt,
  getPromptByKey,
} from "@/lib/db";

// GET /api/prompts/versions?key=slot_1_prefilter
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const promptKey = searchParams.get("key");

    if (!promptKey) {
      return NextResponse.json(
        { error: "key query parameter is required" },
        { status: 400 }
      );
    }

    const versions = await getPromptVersions(promptKey);
    return NextResponse.json({ versions });
  } catch (error) {
    console.error("Error fetching prompt versions:", error);
    return NextResponse.json(
      { error: "Failed to fetch prompt versions" },
      { status: 500 }
    );
  }
}

// POST /api/prompts/versions - Rollback to a previous version
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { promptKey, version, userEmail } = body;

    if (!promptKey) {
      return NextResponse.json(
        { error: "promptKey is required" },
        { status: 400 }
      );
    }

    if (version === undefined || typeof version !== "number") {
      return NextResponse.json(
        { error: "version (number) is required" },
        { status: 400 }
      );
    }

    const result = await rollbackPrompt(promptKey, version, userEmail);

    // Fetch updated prompt to return
    const prompt = await getPromptByKey(promptKey);

    return NextResponse.json({
      success: true,
      message: `Rolled back to version ${version}`,
      versionId: result.versionId,
      prompt,
    });
  } catch (error) {
    console.error("Error rolling back prompt:", error);
    return NextResponse.json(
      { error: "Failed to rollback prompt" },
      { status: 500 }
    );
  }
}
