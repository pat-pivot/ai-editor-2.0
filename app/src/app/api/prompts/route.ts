import { NextRequest, NextResponse } from "next/server";
import {
  getPromptsByStep,
  getPromptByKey,
  updatePromptContent,
} from "@/lib/db";

// GET /api/prompts?stepId=1 or GET /api/prompts?key=slot_1_prefilter
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const stepId = searchParams.get("stepId");
    const promptKey = searchParams.get("key");

    if (promptKey) {
      // Get single prompt by key
      const prompt = await getPromptByKey(promptKey);
      if (!prompt) {
        return NextResponse.json(
          { error: "Prompt not found" },
          { status: 404 }
        );
      }
      return NextResponse.json({ prompt });
    }

    if (stepId) {
      // Get all prompts for a step
      const prompts = await getPromptsByStep(parseInt(stepId, 10));
      return NextResponse.json({ prompts });
    }

    return NextResponse.json(
      { error: "Either stepId or key query parameter is required" },
      { status: 400 }
    );
  } catch (error) {
    console.error("Error fetching prompts:", error);
    return NextResponse.json(
      { error: "Failed to fetch prompts" },
      { status: 500 }
    );
  }
}

// PATCH /api/prompts - Update prompt content (creates new version)
export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json();
    const { promptKey, content, userEmail, changeSummary } = body;

    if (!promptKey) {
      return NextResponse.json(
        { error: "promptKey is required" },
        { status: 400 }
      );
    }

    if (content === undefined) {
      return NextResponse.json(
        { error: "content is required" },
        { status: 400 }
      );
    }

    const result = await updatePromptContent(
      promptKey,
      content,
      userEmail,
      changeSummary
    );

    // Fetch updated prompt to return
    const prompt = await getPromptByKey(promptKey);

    return NextResponse.json({
      success: true,
      versionId: result.versionId,
      prompt,
    });
  } catch (error) {
    console.error("Error updating prompt:", error);
    return NextResponse.json(
      { error: "Failed to update prompt" },
      { status: 500 }
    );
  }
}
