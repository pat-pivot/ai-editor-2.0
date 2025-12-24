import { Pool, PoolClient } from "pg";

// Create a connection pool
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: false } : false,
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
});

// Export query function
export async function query<T = unknown>(
  text: string,
  params?: unknown[]
): Promise<T[]> {
  const client = await pool.connect();
  try {
    const result = await client.query(text, params);
    return result.rows as T[];
  } finally {
    client.release();
  }
}

// Export transaction helper
export async function transaction<T>(
  callback: (client: PoolClient) => Promise<T>
): Promise<T> {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const result = await callback(client);
    await client.query("COMMIT");
    return result;
  } catch (e) {
    await client.query("ROLLBACK");
    throw e;
  } finally {
    client.release();
  }
}

// Types for system prompts
export interface SystemPrompt {
  id: string;
  prompt_key: string;
  step_id: number;
  name: string;
  description: string | null;
  model: string;
  temperature: number;
  slot_number: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptVersion {
  id: string;
  prompt_id: string;
  version: number;
  content: string;
  change_summary: string | null;
  created_by: string | null;
  created_by_email: string | null;
  is_current: boolean;
  created_at: string;
}

export interface PromptWithContent extends SystemPrompt {
  content: string;
  current_version: number;
  last_modified_by: string | null;
}

// Get all prompts for a step
export async function getPromptsByStep(stepId: number): Promise<PromptWithContent[]> {
  const sql = `
    SELECT
      sp.id,
      sp.prompt_key,
      sp.step_id,
      sp.name,
      sp.description,
      sp.model,
      sp.temperature,
      sp.slot_number,
      sp.is_active,
      sp.created_at,
      sp.updated_at,
      spv.content,
      spv.version as current_version,
      spv.created_by_email as last_modified_by
    FROM system_prompts sp
    LEFT JOIN system_prompt_versions spv ON sp.id = spv.prompt_id AND spv.is_current = true
    WHERE sp.step_id = $1 AND sp.is_active = true
    ORDER BY sp.slot_number NULLS LAST, sp.name
  `;
  return query<PromptWithContent>(sql, [stepId]);
}

// Get a single prompt by key
export async function getPromptByKey(promptKey: string): Promise<PromptWithContent | null> {
  const sql = `
    SELECT
      sp.id,
      sp.prompt_key,
      sp.step_id,
      sp.name,
      sp.description,
      sp.model,
      sp.temperature,
      sp.slot_number,
      sp.is_active,
      sp.created_at,
      sp.updated_at,
      spv.content,
      spv.version as current_version,
      spv.created_by_email as last_modified_by
    FROM system_prompts sp
    LEFT JOIN system_prompt_versions spv ON sp.id = spv.prompt_id AND spv.is_current = true
    WHERE sp.prompt_key = $1 AND sp.is_active = true
  `;
  const results = await query<PromptWithContent>(sql, [promptKey]);
  return results[0] ?? null;
}

// Get version history for a prompt
export async function getPromptVersions(promptKey: string): Promise<PromptVersion[]> {
  const sql = `
    SELECT
      spv.id,
      spv.prompt_id,
      spv.version,
      spv.content,
      spv.change_summary,
      spv.created_by,
      spv.created_by_email,
      spv.is_current,
      spv.created_at
    FROM system_prompt_versions spv
    JOIN system_prompts sp ON sp.id = spv.prompt_id
    WHERE sp.prompt_key = $1
    ORDER BY spv.version DESC
  `;
  return query<PromptVersion>(sql, [promptKey]);
}

// Update prompt content (creates new version)
export async function updatePromptContent(
  promptKey: string,
  content: string,
  userEmail?: string,
  changeSummary?: string
): Promise<{ versionId: string }> {
  const sql = `
    SELECT update_prompt_content($1, $2, NULL, $3, $4) as version_id
  `;
  const results = await query<{ version_id: string }>(sql, [
    promptKey,
    content,
    userEmail ?? null,
    changeSummary ?? null,
  ]);
  return { versionId: results[0].version_id };
}

// Rollback to a previous version
export async function rollbackPrompt(
  promptKey: string,
  version: number,
  userEmail?: string
): Promise<{ versionId: string }> {
  const sql = `
    SELECT rollback_prompt($1, $2, NULL, $3) as version_id
  `;
  const results = await query<{ version_id: string }>(sql, [
    promptKey,
    version,
    userEmail ?? null,
  ]);
  return { versionId: results[0].version_id };
}

export default pool;
