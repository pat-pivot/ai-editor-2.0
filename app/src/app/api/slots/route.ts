import { NextResponse } from "next/server";
import { getSelectedSlots } from "@/lib/airtable";

export async function GET() {
  try {
    const selectedSlots = await getSelectedSlots();
    return NextResponse.json({ selectedSlots });
  } catch (error) {
    console.error("Error fetching selected slots:", error);
    return NextResponse.json(
      { error: "Failed to fetch selected slots" },
      { status: 500 }
    );
  }
}
