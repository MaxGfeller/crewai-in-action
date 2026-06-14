/**
 * Tiny request-body validation helpers for the demo-app auth routes.
 *
 * We intentionally avoid pulling in zod / valibot for the chapter - the
 * book teaches the smallest reasonable thing. The patterns below are
 * deliberately easy to read rather than maximally generic.
 */

export class ValidationError extends Error {
  constructor(public readonly field: string, message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export interface SignupInput {
  email: string;
  password: string;
  name: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface ChickenInput {
  name: string;
  breed?: string | null;
  age_months?: number | null;
  weight_kg?: number | null;
  status?: string | null;
  notes?: string | null;
}

function normaliseEmail(value: unknown): string {
  if (typeof value !== "string" || !EMAIL_RE.test(value.trim())) {
    throw new ValidationError("email", "valid email is required");
  }
  return value.trim().toLowerCase();
}

function requireString(value: unknown, field: string, min: number, max: number): string {
  if (typeof value !== "string") {
    throw new ValidationError(field, `${field} is required`);
  }
  const trimmed = value.trim();
  if (trimmed.length < min || trimmed.length > max) {
    throw new ValidationError(
      field,
      `${field} must be between ${min} and ${max} characters`,
    );
  }
  return trimmed;
}

function requirePassword(value: unknown): string {
  if (typeof value !== "string") {
    throw new ValidationError("password", "password is required");
  }
  if (value.length < 12) {
    throw new ValidationError("password", "password must be at least 12 characters");
  }
  if (value.length > 256) {
    throw new ValidationError("password", "password is too long");
  }
  return value;
}

export function parseSignup(body: unknown): SignupInput {
  if (!body || typeof body !== "object") {
    throw new ValidationError("body", "request body must be a JSON object");
  }
  const raw = body as Record<string, unknown>;
  return {
    email: normaliseEmail(raw.email),
    password: requirePassword(raw.password),
    name: requireString(raw.name, "name", 1, 120),
  };
}

export function parseLogin(body: unknown): LoginInput {
  if (!body || typeof body !== "object") {
    throw new ValidationError("body", "request body must be a JSON object");
  }
  const raw = body as Record<string, unknown>;
  return {
    email: normaliseEmail(raw.email),
    password: requireString(raw.password, "password", 1, 256),
  };
}

export function parseChicken(body: unknown): ChickenInput {
  if (!body || typeof body !== "object") {
    throw new ValidationError("body", "request body must be a JSON object");
  }
  const raw = body as Record<string, unknown>;
  const name = requireString(raw.name, "name", 1, 120);

  const numberOrNull = (v: unknown, field: string): number | null => {
    if (v === null || v === undefined) return null;
    if (typeof v !== "number" || !Number.isFinite(v)) {
      throw new ValidationError(field, `${field} must be a number`);
    }
    return v;
  };

  const stringOrNull = (v: unknown, field: string, max: number): string | null => {
    if (v === null || v === undefined) return null;
    if (typeof v !== "string") {
      throw new ValidationError(field, `${field} must be a string`);
    }
    const trimmed = v.trim();
    if (trimmed.length > max) {
      throw new ValidationError(field, `${field} must be at most ${max} characters`);
    }
    return trimmed;
  };

  return {
    name,
    breed: stringOrNull(raw.breed, "breed", 80),
    age_months: (() => {
      const v = numberOrNull(raw.age_months, "age_months");
      if (v === null) return null;
      if (v < 0 || v > 1200) {
        throw new ValidationError("age_months", "age_months out of range");
      }
      return v;
    })(),
    weight_kg: (() => {
      const v = numberOrNull(raw.weight_kg, "weight_kg");
      if (v === null) return null;
      if (v < 0 || v > 1000) {
        throw new ValidationError("weight_kg", "weight_kg out of range");
      }
      return v;
    })(),
    status: stringOrNull(raw.status ?? "active", "status", 40),
    notes: stringOrNull(raw.notes, "notes", 4000),
  };
}

/**
 * Simple sliding-window in-memory rate limiter, scoped per process. Fine for
 * the demo (single-node) and the chapter (teaches the pattern); a real
 * deployment should swap this for a Redis-backed limiter.
 */
export class RateLimiter {
  private readonly windowMs: number;
  private readonly max: number;
  private readonly hits = new Map<string, number[]>();

  constructor(windowMs = 60_000, max = 10) {
    this.windowMs = windowMs;
    this.max = max;
  }

  check(key: string): { allowed: boolean; retryAfterSec: number } {
    const now = Date.now();
    const cutoff = now - this.windowMs;
    const prior = (this.hits.get(key) ?? []).filter((t) => t > cutoff);
    if (prior.length >= this.max) {
      const oldest = prior[0];
      const retryAfterSec = Math.max(1, Math.ceil((oldest + this.windowMs - now) / 1000));
      this.hits.set(key, prior);
      return { allowed: false, retryAfterSec };
    }
    prior.push(now);
    this.hits.set(key, prior);
    return { allowed: true, retryAfterSec: 0 };
  }
}

/**
 * Lightweight CSRF guard: reject state-changing requests (anything other
 * than GET / HEAD / OPTIONS) whose Origin does not match an allowed host.
 * This is not a substitute for a proper CSRF token, but it stops the
 * trivial cross-site form posts the demo-app is otherwise vulnerable to.
 */
const ALLOWED_ORIGIN_SUFFIXES = [
  "localhost:3000",
  "127.0.0.1:3000",
];

export function isSameOrigin(req: { method?: string; headers: { get(name: string): string | null } }): boolean {
  const method = (req.method ?? "GET").toUpperCase();
  if (method === "GET" || method === "HEAD" || method === "OPTIONS") {
    return true;
  }
  const origin = req.headers.get("origin") ?? req.headers.get("referer") ?? "";
  if (!origin) {
    // Block cross-site state-changing requests that don't even send an
    // Origin / Referer - those are almost always bots or attackers.
    return false;
  }
  try {
    const url = new URL(origin);
    const host = url.host;
    return ALLOWED_ORIGIN_SUFFIXES.some(
      (suffix) => host === suffix || host.endsWith(`.${suffix}`),
    );
  } catch {
    return false;
  }
}
