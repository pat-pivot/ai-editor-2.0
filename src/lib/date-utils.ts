/**
 * Date utilities for consistent Eastern Time formatting across the dashboard.
 * All dates are displayed in ET (Eastern Time) for Pivot 5 operations.
 */

const ET_TIMEZONE = "America/New_York";

/**
 * Format a date for display in Eastern Time
 * @param date - Date object, ISO string, or timestamp
 * @returns Formatted date string like "Dec 23, 2025 9:00:15 PM ET"
 */
export function formatDateET(date: Date | string | number): string {
  const d = new Date(date);

  if (isNaN(d.getTime())) {
    return "Invalid date";
  }

  return d.toLocaleString("en-US", {
    timeZone: ET_TIMEZONE,
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  }) + " ET";
}

/**
 * Format a date for display without seconds (for next run predictions)
 * @param date - Date object, ISO string, or timestamp
 * @returns Formatted date string like "Dec 24, 2025 9:00 PM ET"
 */
export function formatDateETShort(date: Date | string | number): string {
  const d = new Date(date);

  if (isNaN(d.getTime())) {
    return "Invalid date";
  }

  return d.toLocaleString("en-US", {
    timeZone: ET_TIMEZONE,
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }) + " ET";
}

/**
 * Format duration in seconds to human-readable format
 * @param seconds - Duration in seconds
 * @returns Formatted duration like "1m 42s" or "2h 5m 30s"
 */
export function formatDuration(seconds: number): string {
  if (seconds < 0) return "0s";

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

  return parts.join(" ");
}

/**
 * Get time ago string (e.g., "2 hours ago", "5 minutes ago")
 * @param date - Date object, ISO string, or timestamp
 * @returns Relative time string
 */
export function timeAgo(date: Date | string | number): string {
  const d = new Date(date);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return diffDays === 1 ? "1 day ago" : `${diffDays} days ago`;
  }
  if (diffHours > 0) {
    return diffHours === 1 ? "1 hour ago" : `${diffHours} hours ago`;
  }
  if (diffMins > 0) {
    return diffMins === 1 ? "1 minute ago" : `${diffMins} minutes ago`;
  }
  return "just now";
}

/**
 * Get the next cron run time based on schedule
 * @param cronSchedule - Cron schedule string (e.g., "0 6,14,22 * * *")
 * @returns Next run date in ET
 */
export function getNextCronRun(cronSchedule: string): Date {
  // Simple implementation for common patterns
  // For full cron support, consider using a library like node-cron or cron-parser

  const now = new Date();
  const etNow = new Date(now.toLocaleString("en-US", { timeZone: ET_TIMEZONE }));

  // Parse basic hour-based cron (e.g., "0 6,14,22 * * *")
  const parts = cronSchedule.split(" ");
  if (parts.length >= 2) {
    const minute = parseInt(parts[0]) || 0;
    const hours = parts[1].split(",").map(h => parseInt(h)).filter(h => !isNaN(h));

    if (hours.length > 0) {
      // Find next hour that's in the future
      const currentHour = etNow.getHours();
      const currentMinute = etNow.getMinutes();

      // Check today's remaining hours
      for (const hour of hours) {
        if (hour > currentHour || (hour === currentHour && minute > currentMinute)) {
          const nextRun = new Date(etNow);
          nextRun.setHours(hour, minute, 0, 0);
          return nextRun;
        }
      }

      // All today's hours passed, use first hour tomorrow
      const nextRun = new Date(etNow);
      nextRun.setDate(nextRun.getDate() + 1);
      nextRun.setHours(hours[0], minute, 0, 0);
      return nextRun;
    }
  }

  // Default: return 24 hours from now
  const nextRun = new Date(now);
  nextRun.setDate(nextRun.getDate() + 1);
  return nextRun;
}
