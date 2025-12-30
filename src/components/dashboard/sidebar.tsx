"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: string;
  stepNumber?: number;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navigation: NavSection[] = [
  {
    title: "PIPELINE",
    items: [
      { name: "Overview", href: "/", icon: "dashboard" },
      { name: "Ingest", href: "/step/0", icon: "cloud_download", stepNumber: 0 },
      { name: "Pre-Filter", href: "/step/1", icon: "filter_alt", stepNumber: 1 },
      { name: "Slot Selection", href: "/step/2", icon: "checklist", stepNumber: 2 },
      { name: "Decoration", href: "/step/3", icon: "edit_note", stepNumber: 3 },
      { name: "HTML Compile", href: "/step/4", icon: "code", stepNumber: 4 },
      { name: "Send & Social", href: "/step/5", icon: "send", stepNumber: 5 },
    ],
  },
  {
    title: "DATA",
    items: [
      { name: "Stories", href: "/data/stories", icon: "article" },
      { name: "Sources", href: "/data/sources", icon: "source" },
      { name: "Issues", href: "/data/issues", icon: "newspaper" },
    ],
  },
  {
    title: "ANALYTICS",
    items: [
      { name: "Mautic", href: "/analytics", icon: "analytics" },
    ],
  },
  {
    title: "SANDBOX",
    items: [
      { name: "FreshRSS Pipeline", href: "/sandbox", icon: "science" },
    ],
  },
];

function MaterialIcon({ name, className }: { name: string; className?: string }) {
  return (
    <span className={cn("material-symbols-outlined text-lg", className)}>
      {name}
    </span>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/";
    }
    return pathname.startsWith(href);
  };

  return (
    <div className="flex h-full w-64 flex-col bg-sidebar border-r border-sidebar-border">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-6 border-b border-sidebar-border">
        <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
          <span className="text-primary-foreground font-bold text-sm">P5</span>
        </div>
        <div className="flex flex-col">
          <span className="text-base font-semibold text-sidebar-foreground leading-tight">AI Editor</span>
          <span className="text-xs text-muted-foreground">v2.0</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {navigation.map((section) => (
          <div key={section.title} className="mb-6">
            <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground tracking-wider">
              {section.title}
            </h3>
            <div className="space-y-1">
              {section.items.map((item) => {
                const active = isActive(item.href);

                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
                    )}
                  >
                    <MaterialIcon
                      name={item.icon}
                      className={active ? "text-sidebar-primary" : ""}
                    />
                    <span className="flex items-center gap-2">
                      {item.stepNumber && (
                        <span className={cn(
                          "flex h-5 w-5 items-center justify-center rounded text-xs font-medium",
                          active
                            ? "bg-sidebar-primary text-sidebar-primary-foreground"
                            : "bg-sidebar-accent text-sidebar-accent-foreground"
                        )}>
                          {item.stepNumber}
                        </span>
                      )}
                      {item.name}
                    </span>
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-4">
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors"
        >
          <MaterialIcon name="settings" />
          Settings
        </Link>
        <div className="flex items-center gap-3 mt-3 px-3">
          <div className="h-8 w-8 rounded-full bg-sidebar-accent flex items-center justify-center">
            <span className="text-xs text-sidebar-foreground font-medium">PS</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-sidebar-foreground truncate">Pat Simmons</p>
            <p className="text-xs text-muted-foreground truncate">Admin</p>
          </div>
        </div>
      </div>
    </div>
  );
}
