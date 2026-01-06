# AI Editor 2.0 - UI Design System & Theme Configuration

**Date:** December 23, 2025
**Project:** AI Editor Dashboard UI
**Status:** SPECIFICATION
**Domain:** `app.pivotmedia.ai`
**Theme Source:** TweakCN (shadcn/ui registry)

---

## Table of Contents

1. [Design Philosophy](#design-philosophy)
2. [Installation](#installation)
3. [Theme Configuration](#theme-configuration)
4. [Typography](#typography)
5. [Color System](#color-system)
6. [Shadows & Elevation](#shadows--elevation)
7. [Card Components](#card-components)
8. [Iconography](#iconography)
9. [Component Patterns](#component-patterns)
10. [Sidebar Navigation](#sidebar-navigation)
11. [Data Tables](#data-tables)
12. [Code Editor](#code-editor)

---

## Design Philosophy

### Core Principles

1. **Professional SaaS Aesthetic** - Clean, modern, enterprise-grade appearance
2. **Card-Based Layout** - Elevated cards with subtle shadows create visual hierarchy
3. **Minimal Iconography** - Icons used sparingly, primarily in sidebar navigation
4. **No Gradients** - Solid colors only, flat design with depth from shadows
5. **OKLCH Color Space** - Perceptually uniform colors for Tailwind v4

### Visual Identity

- **Modern Dashboard** - Inspired by contemporary admin panels (Linear, Vercel, Stripe)
- **Orange Accent** - Primary brand color `oklch(0.6886 0.1887 47.6087)`
- **Neutral Foundation** - Gray-scale backgrounds with white card surfaces
- **Professional Typography** - Inter for UI, JetBrains Mono for code/logs

---

## Installation

### Install Theme via shadcn CLI

```bash
npx shadcn@latest add https://tweakcn.com/r/themes/cmjj0upk1000504jp7tsc92wp
```

### Required Dependencies

```bash
# Core
npm install tailwindcss@^4.0.0
npm install @radix-ui/react-icons
npm install lucide-react

# Google Material Icons (Professional iconography)
npm install @material-symbols/font-400
```

### Font Setup (Google Fonts)

```html
<!-- Add to _document.tsx or layout.tsx -->
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=JetBrains+Mono:wght@100..800&family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&display=swap"
  rel="stylesheet"
/>
```

---

## Theme Configuration

### Complete CSS Variables (globals.css)

```css
@import "tailwindcss";

@theme inline {
  /* Typography */
  --font-sans: "Inter", sans-serif;
  --font-serif: "Source Serif 4", serif;
  --font-mono: "JetBrains Mono", monospace;

  /* Spacing & Radius */
  --spacing: 0.25rem;
  --radius: 0.375rem;
  --tracking-normal: 0em;

  /* Shadow System (Critical for card styling) */
  --shadow-2xs: 0 1px hsl(0 0% 0% / 0.05);
  --shadow-xs: 0 1px 2px 0 hsl(0 0% 0% / 0.05);
  --shadow-sm: 0 1px 3px 0 hsl(0 0% 0% / 0.1), 0 1px 2px -1px hsl(0 0% 0% / 0.1);
  --shadow-md: 0 4px 6px -1px hsl(0 0% 0% / 0.1), 0 2px 4px -2px hsl(0 0% 0% / 0.1);
  --shadow-lg: 0 10px 15px -3px hsl(0 0% 0% / 0.1), 0 4px 6px -4px hsl(0 0% 0% / 0.1);
  --shadow-xl: 0 20px 25px -5px hsl(0 0% 0% / 0.1), 0 8px 10px -6px hsl(0 0% 0% / 0.1);
  --shadow-2xl: 0 25px 50px -12px hsl(0 0% 0% / 0.25);

  /* ============================================
     LIGHT MODE COLORS (OKLCH)
     ============================================ */

  /* Base */
  --color-background: oklch(1 0 0);
  --color-foreground: oklch(0.2686 0 0);

  /* Primary - Orange Accent */
  --color-primary: oklch(0.6886 0.1887 47.6087);
  --color-primary-foreground: oklch(0.9869 0.0214 95.2774);

  /* Secondary */
  --color-secondary: oklch(0.9694 0 0);
  --color-secondary-foreground: oklch(0.2046 0 0);

  /* Muted */
  --color-muted: oklch(0.9694 0 0);
  --color-muted-foreground: oklch(0.5563 0 0);

  /* Accent */
  --color-accent: oklch(0.9869 0.0214 95.2774);
  --color-accent-foreground: oklch(0.2046 0 0);

  /* Destructive (Errors) */
  --color-destructive: oklch(0.6368 0.2078 25.3313);
  --color-destructive-foreground: oklch(0.9869 0.0214 95.2774);

  /* Card (Critical for elevated card styling) */
  --color-card: oklch(1 0 0);
  --color-card-foreground: oklch(0.2686 0 0);

  /* Popover */
  --color-popover: oklch(1 0 0);
  --color-popover-foreground: oklch(0.2686 0 0);

  /* Borders */
  --color-border: oklch(0.9219 0 0);
  --color-input: oklch(0.9219 0 0);
  --color-ring: oklch(0.6886 0.1887 47.6087);

  /* Sidebar (Left navigation) */
  --color-sidebar: oklch(0.9869 0.0214 95.2774);
  --color-sidebar-foreground: oklch(0.2686 0 0);
  --color-sidebar-primary: oklch(0.6886 0.1887 47.6087);
  --color-sidebar-primary-foreground: oklch(0.9869 0.0214 95.2774);
  --color-sidebar-accent: oklch(0.9694 0 0);
  --color-sidebar-accent-foreground: oklch(0.2046 0 0);
  --color-sidebar-border: oklch(0.9219 0 0);
  --color-sidebar-ring: oklch(0.6886 0.1887 47.6087);

  /* Chart Colors (Data visualization) */
  --color-chart-1: oklch(0.6886 0.1887 47.6087);
  --color-chart-2: oklch(0.6886 0.1887 165.6087);
  --color-chart-3: oklch(0.4686 0.1887 47.6087);
  --color-chart-4: oklch(0.6886 0.1887 283.6087);
  --color-chart-5: oklch(0.8886 0.1887 47.6087);
}

/* ============================================
   DARK MODE COLORS (OKLCH)
   ============================================ */

.dark {
  --color-background: oklch(0.2046 0 0);
  --color-foreground: oklch(0.9219 0 0);

  --color-primary: oklch(0.7686 0.1647 70.0804);
  --color-primary-foreground: oklch(0.2686 0 0);

  --color-secondary: oklch(0.2686 0 0);
  --color-secondary-foreground: oklch(0.9219 0 0);

  --color-muted: oklch(0.2686 0 0);
  --color-muted-foreground: oklch(0.7087 0 0);

  --color-accent: oklch(0.2686 0 0);
  --color-accent-foreground: oklch(0.9219 0 0);

  --color-destructive: oklch(0.6368 0.2078 25.3313);
  --color-destructive-foreground: oklch(0.9219 0 0);

  --color-card: oklch(0.2686 0 0);
  --color-card-foreground: oklch(0.9219 0 0);

  --color-popover: oklch(0.2686 0 0);
  --color-popover-foreground: oklch(0.9219 0 0);

  --color-border: oklch(0.3726 0 0);
  --color-input: oklch(0.3726 0 0);
  --color-ring: oklch(0.7686 0.1647 70.0804);

  --color-sidebar: oklch(0.2046 0 0);
  --color-sidebar-foreground: oklch(0.9219 0 0);
  --color-sidebar-primary: oklch(0.7686 0.1647 70.0804);
  --color-sidebar-primary-foreground: oklch(0.2686 0 0);
  --color-sidebar-accent: oklch(0.2686 0 0);
  --color-sidebar-accent-foreground: oklch(0.9219 0 0);
  --color-sidebar-border: oklch(0.3726 0 0);
  --color-sidebar-ring: oklch(0.7686 0.1647 70.0804);

  --color-chart-1: oklch(0.6886 0.1887 165.6087);
  --color-chart-2: oklch(0.6886 0.1887 283.6087);
  --color-chart-3: oklch(0.6886 0.1887 47.6087);
  --color-chart-4: oklch(0.8886 0.1887 165.6087);
  --color-chart-5: oklch(0.4686 0.1887 283.6087);
}
```

---

## Typography

### Font Stack

| Use Case | Font Family | Weight Range |
|----------|-------------|--------------|
| **UI Text** | Inter | 400-700 |
| **Headings** | Inter | 600-700 |
| **Body/Prose** | Source Serif 4 | 400-600 |
| **Code/Logs** | JetBrains Mono | 400-500 |

### Type Scale

```css
/* Tailwind v4 type scale */
.text-xs    { font-size: 0.75rem; line-height: 1rem; }
.text-sm    { font-size: 0.875rem; line-height: 1.25rem; }
.text-base  { font-size: 1rem; line-height: 1.5rem; }
.text-lg    { font-size: 1.125rem; line-height: 1.75rem; }
.text-xl    { font-size: 1.25rem; line-height: 1.75rem; }
.text-2xl   { font-size: 1.5rem; line-height: 2rem; }
.text-3xl   { font-size: 1.875rem; line-height: 2.25rem; }
```

### Usage Examples

```tsx
// Page heading
<h1 className="text-2xl font-semibold tracking-tight">Pipeline Overview</h1>

// Section heading
<h2 className="text-lg font-medium">Today's Issue</h2>

// Body text
<p className="text-sm text-muted-foreground">Last run: 2 hours ago</p>

// Log entry (monospace)
<code className="font-mono text-xs">9:00:02.456  INFO  [AIRTABLE_READ]</code>

// Label
<label className="text-sm font-medium">Model</label>
```

---

## Color System

### Semantic Colors

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `primary` | Orange `oklch(0.6886 0.1887 47.6087)` | Lime `oklch(0.7686 0.1647 70.0804)` | Buttons, links, focus rings |
| `secondary` | Light gray | Dark gray | Secondary buttons |
| `destructive` | Red `oklch(0.6368 0.2078 25.3313)` | Red | Delete, errors |
| `muted` | Light gray | Dark gray | Disabled states |
| `accent` | Cream | Dark gray | Hover states, badges |

### Status Colors (for pipeline visualization)

```tsx
const statusColors = {
  complete: "text-emerald-600",    // ✓ Complete
  running: "text-orange-500",      // ● Running (pulsing)
  pending: "text-gray-400",        // ○ Pending
  warning: "text-amber-500",       // ⚠ Warning
  error: "text-red-500",           // ✗ Error
};
```

### Log Level Colors

```tsx
const logLevelColors = {
  DEBUG: "text-gray-400",
  INFO: "text-blue-500",
  WARN: "text-amber-500",
  ERROR: "text-red-500",
  FATAL: "text-red-600 font-bold",
};
```

---

## Shadows & Elevation

### Shadow Scale (Card Styling)

The shadow system creates visual hierarchy and depth. Use consistently:

| Level | Class | Usage |
|-------|-------|-------|
| **2xs** | `shadow-2xs` | Subtle elements, hover lift |
| **xs** | `shadow-xs` | Small elements, badges |
| **sm** | `shadow-sm` | Default card state |
| **md** | `shadow-md` | Elevated cards, primary cards |
| **lg** | `shadow-lg` | Modals, dropdowns |
| **xl** | `shadow-xl` | Floating elements, popovers |
| **2xl** | `shadow-2xl` | Hero cards, featured content |

### Card Elevation Pattern

```tsx
// Standard card (most common)
<Card className="shadow-sm border border-border">
  {/* content */}
</Card>

// Elevated card (for primary content)
<Card className="shadow-md border border-border">
  {/* content */}
</Card>

// Interactive card (hover state)
<Card className="shadow-sm hover:shadow-md transition-shadow duration-200 border border-border">
  {/* content */}
</Card>

// Featured/hero card
<Card className="shadow-lg border border-border">
  {/* content */}
</Card>
```

---

## Card Components

### Standard Card Pattern

```tsx
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// Pipeline step card
<Card className="shadow-sm border border-border">
  <CardHeader className="pb-3">
    <CardTitle className="text-base font-medium">Step 1: Pre-Filter</CardTitle>
    <CardDescription className="text-sm text-muted-foreground">
      Scheduled: 9:00 PM ET
    </CardDescription>
  </CardHeader>
  <CardContent>
    <div className="flex items-center gap-2">
      <span className="text-emerald-600">✓</span>
      <span className="text-sm">Complete</span>
    </div>
  </CardContent>
</Card>
```

### Metric Card

```tsx
// Metric/stat card
<Card className="shadow-sm border border-border">
  <CardHeader className="flex flex-row items-center justify-between pb-2">
    <CardTitle className="text-sm font-medium text-muted-foreground">
      Stories Processed
    </CardTitle>
    <span className="material-symbols-outlined text-muted-foreground">article</span>
  </CardHeader>
  <CardContent>
    <div className="text-2xl font-semibold">156</div>
    <p className="text-xs text-muted-foreground">+12 from yesterday</p>
  </CardContent>
</Card>
```

### Interactive Card

```tsx
// Clickable step card with hover effect
<Card
  className="shadow-sm hover:shadow-md transition-shadow duration-200 cursor-pointer border border-border"
  onClick={() => navigate(`/step/${step.number}`)}
>
  <CardHeader className="pb-2">
    <div className="flex items-center justify-between">
      <CardTitle className="text-sm font-medium">STEP {step.number}</CardTitle>
      <StatusBadge status={step.status} />
    </div>
  </CardHeader>
  <CardContent>
    <p className="text-sm">{step.name}</p>
    <p className="text-xs text-muted-foreground mt-1">{step.scheduledTime}</p>
  </CardContent>
</Card>
```

---

## Iconography

### Icon System

**Primary:** Google Material Symbols (400 weight)
**Fallback:** Lucide React

**Philosophy:** Icons used minimally, primarily in sidebar navigation. Avoid decorative icons.

### Installation

```tsx
// Import Material Symbols font in layout
import "@material-symbols/font-400";

// Usage in component
<span className="material-symbols-outlined">dashboard</span>
```

### Sidebar Icons (Complete List)

| Section | Icon | Material Symbol |
|---------|------|-----------------|
| Overview | Dashboard | `dashboard` |
| Step 1 | Filter | `filter_alt` |
| Step 2 | Checklist | `checklist` |
| Step 3 | Edit | `edit_note` |
| Step 4 | Code | `code` |
| Step 5 | Send | `send` |
| Stories | Article | `article` |
| Sources | Source | `source` |
| Issues | Newspaper | `newspaper` |
| Analytics | Analytics | `analytics` |
| Settings | Settings | `settings` |

### Icon Usage Pattern

```tsx
// Sidebar nav item
<NavItem
  icon={<span className="material-symbols-outlined text-lg">dashboard</span>}
  label="Overview"
  href="/"
/>

// With Lucide fallback (for complex icons)
import { Play, Pause, RotateCcw } from "lucide-react";

<Button size="sm" variant="outline">
  <Play className="h-4 w-4 mr-2" />
  Run Now
</Button>
```

### Icon Sizing

| Context | Size | Class |
|---------|------|-------|
| Sidebar nav | 20px | `text-lg` |
| Button icon | 16px | `h-4 w-4` |
| Metric card | 20px | `text-lg` |
| Inline text | 16px | `text-base` |

---

## Component Patterns

### Buttons

```tsx
// Primary action (Run Now, Save)
<Button className="bg-primary text-primary-foreground hover:bg-primary/90">
  Run Now
</Button>

// Secondary action
<Button variant="outline">
  View Logs
</Button>

// Destructive action
<Button variant="destructive">
  Delete
</Button>

// Ghost/tertiary
<Button variant="ghost">
  Cancel
</Button>

// With icon
<Button size="sm" variant="outline">
  <RotateCcw className="h-4 w-4 mr-2" />
  Retry
</Button>
```

### Status Badges

```tsx
const StatusBadge = ({ status }: { status: string }) => {
  const config = {
    complete: {
      icon: "✓",
      bg: "bg-emerald-100",
      text: "text-emerald-700",
      label: "Complete"
    },
    running: {
      icon: "●",
      bg: "bg-orange-100",
      text: "text-orange-700",
      label: "Running",
      pulse: true
    },
    pending: {
      icon: "○",
      bg: "bg-gray-100",
      text: "text-gray-600",
      label: "Pending"
    },
    error: {
      icon: "✗",
      bg: "bg-red-100",
      text: "text-red-700",
      label: "Error"
    },
  };

  const c = config[status];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${c.bg} ${c.text}`}>
      <span className={c.pulse ? "animate-pulse" : ""}>{c.icon}</span>
      {c.label}
    </span>
  );
};
```

### Form Inputs

```tsx
// Text input
<div className="space-y-2">
  <Label htmlFor="model" className="text-sm font-medium">
    Model
  </Label>
  <Input
    id="model"
    value="gemini-3-flash-preview"
    className="border-input bg-background"
  />
</div>

// Select
<div className="space-y-2">
  <Label className="text-sm font-medium">Temperature</Label>
  <Select defaultValue="0.3">
    <SelectTrigger className="border-input bg-background">
      <SelectValue />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="0.1">0.1</SelectItem>
      <SelectItem value="0.3">0.3</SelectItem>
      <SelectItem value="0.5">0.5</SelectItem>
      <SelectItem value="0.7">0.7</SelectItem>
    </SelectContent>
  </Select>
</div>
```

---

## Sidebar Navigation

### Layout Structure

```tsx
// app/(dashboard)/layout.tsx
export default function DashboardLayout({ children }) {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 border-r border-sidebar-border bg-sidebar flex-shrink-0">
        <Sidebar />
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="container mx-auto p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
```

### Sidebar Component

```tsx
const Sidebar = () => {
  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-sidebar-border">
        <Logo />
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {/* Pipeline Section */}
        <div className="px-3 mb-6">
          <h2 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Pipeline
          </h2>
          <NavItem icon="dashboard" label="Overview" href="/" />
          <NavItem icon="filter_alt" label="1. Pre-Filter" href="/step/1" />
          <NavItem icon="checklist" label="2. Slot Selection" href="/step/2" />
          <NavItem icon="edit_note" label="3. Decoration" href="/step/3" />
          <NavItem icon="code" label="4. HTML Compile" href="/step/4" />
          <NavItem icon="send" label="5. Send & Social" href="/step/5" />
        </div>

        {/* Data Section */}
        <div className="px-3 mb-6">
          <h2 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Data
          </h2>
          <NavItem icon="article" label="Stories" href="/data/stories" />
          <NavItem icon="source" label="Sources" href="/data/sources" />
          <NavItem icon="newspaper" label="Issues" href="/data/issues" />
        </div>

        {/* Analytics Section */}
        <div className="px-3">
          <h2 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Analytics
          </h2>
          <NavItem icon="analytics" label="Mautic" href="/analytics" />
        </div>
      </nav>

      {/* Settings (bottom) */}
      <div className="border-t border-sidebar-border p-3">
        <NavItem icon="settings" label="Settings" href="/settings" />
      </div>
    </div>
  );
};
```

### Nav Item Component

```tsx
interface NavItemProps {
  icon: string;
  label: string;
  href: string;
}

const NavItem = ({ icon, label, href }: NavItemProps) => {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(`${href}/`);

  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
        isActive
          ? "bg-sidebar-primary text-sidebar-primary-foreground"
          : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
      )}
    >
      <span className="material-symbols-outlined text-lg">{icon}</span>
      {label}
    </Link>
  );
};
```

---

## Data Tables

### Table Styling

```tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// Stories table
<Card className="shadow-sm border border-border">
  <CardHeader>
    <CardTitle className="text-base font-medium">Newsletter Stories</CardTitle>
  </CardHeader>
  <CardContent className="p-0">
    <Table>
      <TableHeader>
        <TableRow className="border-border hover:bg-muted/50">
          <TableHead className="font-medium">Story ID</TableHead>
          <TableHead className="font-medium">Headline</TableHead>
          <TableHead className="font-medium">Source</TableHead>
          <TableHead className="font-medium">Date</TableHead>
          <TableHead className="font-medium">Slots</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {stories.map((story) => (
          <TableRow key={story.id} className="border-border hover:bg-muted/50">
            <TableCell className="font-mono text-xs">{story.id}</TableCell>
            <TableCell className="max-w-xs truncate">{story.headline}</TableCell>
            <TableCell>{story.source}</TableCell>
            <TableCell className="text-muted-foreground">{story.date}</TableCell>
            <TableCell>
              <div className="flex gap-1">
                {story.slots.map((slot) => (
                  <Badge key={slot} variant="secondary" className="text-xs">
                    {slot}
                  </Badge>
                ))}
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </CardContent>
</Card>
```

### Execution Logs Table

```tsx
// Log entries table with monospace formatting
<Card className="shadow-sm border border-border">
  <CardHeader className="pb-3">
    <div className="flex items-center justify-between">
      <CardTitle className="text-base font-medium">Execution Logs</CardTitle>
      <div className="flex gap-2">
        <Select defaultValue="all">
          <SelectTrigger className="w-32 h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Levels</SelectItem>
            <SelectItem value="error">Errors</SelectItem>
            <SelectItem value="warn">Warnings</SelectItem>
          </SelectContent>
        </Select>
        <Button size="sm" variant="outline" className="h-8 text-xs">
          Export CSV
        </Button>
      </div>
    </div>
  </CardHeader>
  <CardContent className="p-0">
    <div className="font-mono text-xs bg-muted/30 rounded-b-lg overflow-hidden">
      {logs.map((log, i) => (
        <div
          key={i}
          className="flex gap-4 px-4 py-2 border-b border-border last:border-b-0 hover:bg-muted/50"
        >
          <span className="text-muted-foreground w-24 flex-shrink-0">
            {log.timestamp}
          </span>
          <span className={cn("w-12 flex-shrink-0", logLevelColors[log.level])}>
            {log.level}
          </span>
          <span className="text-muted-foreground w-40 flex-shrink-0">
            [{log.code}]
          </span>
          <span className="flex-1">{log.message}</span>
        </div>
      ))}
    </div>
  </CardContent>
</Card>
```

---

## Code Editor

### Monaco Editor for System Prompts

```tsx
import Editor from "@monaco-editor/react";

const SystemPromptEditor = ({ prompt, onSave }) => {
  const [value, setValue] = useState(prompt.text);
  const [isDirty, setIsDirty] = useState(false);

  return (
    <Card className="shadow-md border border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base font-medium">
              {prompt.name}
            </CardTitle>
            <CardDescription className="text-sm text-muted-foreground">
              Model: {prompt.model} | Temperature: {prompt.temperature}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={!isDirty}
              onClick={() => {
                setValue(prompt.text);
                setIsDirty(false);
              }}
            >
              Revert
            </Button>
            <Button
              size="sm"
              disabled={!isDirty}
              onClick={() => onSave(value)}
            >
              Save Changes
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="border-t border-border">
          <Editor
            height="400px"
            defaultLanguage="markdown"
            value={value}
            onChange={(v) => {
              setValue(v || "");
              setIsDirty(v !== prompt.text);
            }}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              fontSize: 13,
              fontFamily: "JetBrains Mono, monospace",
              lineNumbers: "on",
              wordWrap: "on",
              padding: { top: 16, bottom: 16 },
              scrollBeyondLastLine: false,
            }}
          />
        </div>
      </CardContent>
      <div className="px-4 py-2 border-t border-border bg-muted/30">
        <p className="text-xs text-muted-foreground">
          Last modified: {prompt.modifiedAt} by {prompt.modifiedBy}
        </p>
      </div>
    </Card>
  );
};
```

---

## Design Constraints

### DO

- Use shadows for elevation and visual hierarchy
- Use solid colors only (OKLCH color space)
- Keep iconography minimal (sidebar only)
- Use Inter for all UI text
- Use JetBrains Mono for code/logs
- Use cards with subtle borders and shadows
- Maintain consistent spacing (0.25rem base)
- Use 0.375rem border radius consistently

### DO NOT

- Use gradients (anywhere)
- Overuse icons (decorative icons)
- Use non-standard fonts
- Create custom shadow values (use the defined scale)
- Mix color spaces (stick to OKLCH)
- Add animations beyond subtle hover transitions
- Use rounded-full on large elements (except badges/pills)

---

## Reference Screenshots

The following screenshots informed this design system:

1. **Card styling with shadows** - Elevated cards with `shadow-sm` to `shadow-md`
2. **Dashboard layout** - Left sidebar navigation with metric cards
3. **Data tables** - Clean table styling with drag handles, badges, checkboxes

---

*Last updated: December 23, 2025*
