/**
 * Server-side cache for Render logs
 * Prevents multiple SSE connections from hitting rate limits.
 *
 * The Render Logs API has a 30 requests/minute rate limit.
 * This cache ensures all SSE clients share one cached result,
 * reducing API calls from N (per client) to 1.
 */

export interface RenderLog {
  id: string;
  timestamp: string;
  message: string;
  level: string;
  type: string;
  service: string;
}

interface CachedLogs {
  logs: RenderLog[];
  timestamp: number;
  rateLimitRemaining: number;
  rateLimitReset: number;
}

// In-memory cache (survives across SSE connections but not server restarts)
const logCache: Map<string, CachedLogs> = new Map();

// Cache TTL in milliseconds (5 seconds)
const CACHE_TTL_MS = 5000;

// Minimum interval between API calls (even on cache miss)
let lastFetchTime = 0;
const MIN_FETCH_INTERVAL_MS = 2000; // 2 seconds minimum between fetches

// Track if we're currently rate limited
let isRateLimited = false;
let rateLimitResetTime = 0;

/**
 * Generate cache key including hours to prevent different time filters from sharing cache.
 * This fixes the bug where switching from "Live" (0.1h) to "24h" would return stale 6-minute data.
 */
export function getCacheKey(serviceIds: string[], hours?: number): string {
  const serviceKey = serviceIds.sort().join(",");
  // Include hours in cache key so different time filters don't share cache
  return hours !== undefined ? `${serviceKey}_${hours}h` : serviceKey;
}

export function getCachedLogs(serviceIds: string[], hours?: number): CachedLogs | null {
  const key = getCacheKey(serviceIds, hours);
  const cached = logCache.get(key);

  if (!cached) return null;

  // Check if cache is still valid
  if (Date.now() - cached.timestamp > CACHE_TTL_MS) {
    return null; // Cache expired
  }

  return cached;
}

export function setCachedLogs(
  serviceIds: string[],
  logs: RenderLog[],
  rateLimitRemaining: number,
  rateLimitReset: number,
  hours?: number
): void {
  const key = getCacheKey(serviceIds, hours);
  logCache.set(key, {
    logs,
    timestamp: Date.now(),
    rateLimitRemaining,
    rateLimitReset,
  });
}

/**
 * Check if we can make an API call.
 * Returns false if:
 * - We're currently rate limited
 * - We've made a fetch too recently
 */
export function canFetch(): boolean {
  const now = Date.now();

  // Check if we're still rate limited
  if (isRateLimited && now < rateLimitResetTime) {
    console.log(`[LogCache] Rate limited until ${new Date(rateLimitResetTime).toISOString()}`);
    return false;
  }

  // Check minimum fetch interval
  if (now - lastFetchTime < MIN_FETCH_INTERVAL_MS) {
    return false;
  }

  return true;
}

export function markFetchTime(): void {
  lastFetchTime = Date.now();
}

export function markRateLimited(resetTime: number): void {
  isRateLimited = true;
  rateLimitResetTime = resetTime * 1000; // Convert from seconds to ms
  console.warn(`[LogCache] Rate limited! Blocking fetches until ${new Date(rateLimitResetTime).toISOString()}`);
}

export function clearRateLimit(): void {
  isRateLimited = false;
  rateLimitResetTime = 0;
}

export function getRateLimitInfo(
  serviceIds: string[],
  hours?: number
): { remaining: number; resetAt: number } | null {
  const cached = logCache.get(getCacheKey(serviceIds, hours));
  if (!cached) return null;
  return {
    remaining: cached.rateLimitRemaining,
    resetAt: cached.rateLimitReset,
  };
}

export function isCurrentlyRateLimited(): boolean {
  if (!isRateLimited) return false;

  // Check if rate limit has expired
  if (Date.now() >= rateLimitResetTime) {
    clearRateLimit();
    return false;
  }

  return true;
}

export function getTimeUntilReset(): number {
  if (!isRateLimited) return 0;
  return Math.max(0, rateLimitResetTime - Date.now());
}
