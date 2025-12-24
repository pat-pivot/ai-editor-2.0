// Step configuration for the 5-step pipeline

export interface StepConfig {
  id: number;
  name: string;
  description: string;
  schedule: string;
  icon: string;
  prompts: PromptConfig[];
  dataTable: {
    name: string;
    tableId: string;
    baseId: string;
  } | null;
}

export interface PromptConfig {
  id: string;
  name: string;
  model: string;
  temperature: number;
  description: string;
  slotNumber?: number;
}

export const stepConfigs: StepConfig[] = [
  {
    id: 1,
    name: "Pre-Filter",
    description: "Filter stories by slot eligibility using AI classification",
    schedule: "9:00 PM ET Monday-Friday",
    icon: "filter_alt",
    prompts: [
      { id: "slot_1_prefilter", name: "Slot 1 Pre-Filter", model: "gemini-2.0-flash", temperature: 0.3, description: "Macro AI impact - jobs, economy, markets", slotNumber: 1 },
      { id: "slot_2_prefilter", name: "Slot 2 Pre-Filter", model: "gemini-2.0-flash", temperature: 0.3, description: "Tier 1 AI companies + research", slotNumber: 2 },
      { id: "slot_3_prefilter", name: "Slot 3 Pre-Filter", model: "gemini-2.0-flash", temperature: 0.3, description: "Industry-specific AI applications", slotNumber: 3 },
      { id: "slot_4_prefilter", name: "Slot 4 Pre-Filter", model: "gemini-2.0-flash", temperature: 0.3, description: "Emerging companies and startups", slotNumber: 4 },
      { id: "slot_5_prefilter", name: "Slot 5 Pre-Filter", model: "gemini-2.0-flash", temperature: 0.3, description: "Consumer AI and human interest", slotNumber: 5 },
    ],
    dataTable: {
      name: "Pre-Filter Log",
      tableId: "tbl72YMsm9iRHj3sp",
      baseId: "appglKSJZxmA9iHpl",
    },
  },
  {
    id: 2,
    name: "Slot Selection",
    description: "5 sequential Claude agents select the best story for each slot",
    schedule: "11:55 PM ET Monday-Friday",
    icon: "checklist",
    prompts: [
      { id: "slot_1_agent", name: "Slot 1 Agent", model: "claude-sonnet-4-5-20250929", temperature: 0.7, description: "Select lead story for macro AI impact", slotNumber: 1 },
      { id: "slot_2_agent", name: "Slot 2 Agent", model: "claude-sonnet-4-5-20250929", temperature: 0.7, description: "Select Tier 1 company story", slotNumber: 2 },
      { id: "slot_3_agent", name: "Slot 3 Agent", model: "claude-sonnet-4-5-20250929", temperature: 0.7, description: "Select industry impact story", slotNumber: 3 },
      { id: "slot_4_agent", name: "Slot 4 Agent", model: "claude-sonnet-4-5-20250929", temperature: 0.7, description: "Select emerging company story", slotNumber: 4 },
      { id: "slot_5_agent", name: "Slot 5 Agent", model: "claude-sonnet-4-5-20250929", temperature: 0.7, description: "Select consumer/human interest story", slotNumber: 5 },
      { id: "subject_line", name: "Subject Line Generator", model: "claude-sonnet-4-5-20250929", temperature: 0.8, description: "Generate compelling email subject line" },
    ],
    dataTable: {
      name: "Selected Slots",
      tableId: "tblzt2z7r512Kto3O",
      baseId: "appglKSJZxmA9iHpl",
    },
  },
  {
    id: 3,
    name: "Decoration",
    description: "Generate headlines, bullets, deks, and images for selected stories",
    schedule: "9:25 PM & 9:30 PM ET Monday-Friday",
    icon: "edit_note",
    prompts: [
      { id: "content_cleaner", name: "Content Cleaner", model: "gemini-2.0-flash", temperature: 0.1, description: "Remove ads, navigation, and formatting artifacts" },
      { id: "headline_generator", name: "Headline Generator", model: "claude-sonnet-4-5-20250929", temperature: 0.7, description: "Generate punchy Title Case headlines" },
      { id: "bullet_generator", name: "Bullet Generator", model: "claude-sonnet-4-5-20250929", temperature: 0.5, description: "Generate 3 informative bullet points" },
      { id: "bold_formatter", name: "Bold Formatter", model: "claude-sonnet-4-5-20250929", temperature: 0.3, description: "Apply markdown bold to key phrases" },
      { id: "image_prompt", name: "Image Prompt Generator", model: "claude-sonnet-4-5-20250929", temperature: 0.8, description: "Generate descriptive image prompts" },
      { id: "image_generator", name: "Image Generator", model: "gemini-2.0-flash-imagen-3", temperature: 0.7, description: "Generate newsletter images" },
    ],
    dataTable: {
      name: "Decoration",
      tableId: "tbla16LJCf5Z6cRn3",
      baseId: "appglKSJZxmA9iHpl",
    },
  },
  {
    id: 4,
    name: "HTML Compile",
    description: "Compile decorated stories into responsive HTML email template",
    schedule: "10:00 PM ET Monday-Friday",
    icon: "code",
    prompts: [
      { id: "summary_generator", name: "Summary Generator", model: "claude-sonnet-4-5-20250929", temperature: 0.5, description: "Generate 15-word newsletter summary" },
    ],
    dataTable: {
      name: "Newsletter Issues",
      tableId: "tbl7mcCCGbjEfli25",
      baseId: "appwSozYTkrsQWUXB",
    },
  },
  {
    id: 5,
    name: "Send & Social",
    description: "Send email via Mautic and sync stories to social posting queue",
    schedule: "5:00 AM ET Tuesday-Saturday",
    icon: "send",
    prompts: [],
    dataTable: {
      name: "Newsletter Issues Archive",
      tableId: "tblHo0xNj8nbzMHNI",
      baseId: "appwSozYTkrsQWUXB",
    },
  },
];

export function getStepConfig(id: number): StepConfig | undefined {
  return stepConfigs.find((step) => step.id === id);
}

export function getStepName(id: number): string {
  const step = getStepConfig(id);
  return step?.name ?? `Step ${id}`;
}
