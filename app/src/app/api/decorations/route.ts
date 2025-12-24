import { NextResponse } from "next/server";
import { getDecorations } from "@/lib/airtable";

export async function GET() {
  try {
    const decorations = await getDecorations();
    return NextResponse.json({ decorations });
  } catch (error) {
    console.error("Error fetching decorations:", error);
    return NextResponse.json(
      { error: "Failed to fetch decorations" },
      { status: 500 }
    );
  }
}
