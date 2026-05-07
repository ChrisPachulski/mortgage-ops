// orchestration/lockfile.mjs
// Cross-process mutex for serializing DuckDB writes via data/.lock.
// Ported verbatim from career-ops/scripts/lockfile.mjs (Phase 9 PATTERNS.md
// Critical Issue 1) with three renames: CAREER_OPS -> MORTGAGE_OPS,
// .career-ops.lock -> .lock, header citation block.
//
// PERS-04 + PERS-05 + ROADMAP SC-3: 60s stale-lock recovery.
// Plan 09-01 D-01-01: writeFileSync(flag:'w') + read-back-and-verify is the
// poor-man's compare-and-swap (PATTERNS Critical Issue 1). flag:'wx' (O_EXCL)
// is INTENTIONALLY NOT USED — it would crash on every acquire because the
// existing stale lock would still be on disk; the existing code intentionally
// OVERWRITES stale locks at lines acquireLock:if(!existing||isStale(existing)).
//
// Plan 09-01 D-01-02: stale recovery is acquired_at-based (JSON content),
// NOT mtime-based. Deliberate: mtime is vulnerable to filesystem `touch`
// and clock-skew between fs-clock and process-clock. The JSON-content
// timestamp is set deterministically by the writer in the same wall-clock
// domain that reads it back.

import { writeFileSync, readFileSync, unlinkSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const MORTGAGE_OPS = dirname(dirname(fileURLToPath(import.meta.url)));
const LOCK_PATH = join(MORTGAGE_OPS, 'data', '.lock');

export const STALE_THRESHOLD_MS = 60_000;
export const DEFAULT_TIMEOUT_MS = 30_000;
export const POLL_INTERVAL_MS = 100;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export function readLock() {
  if (!existsSync(LOCK_PATH)) return null;
  try {
    return JSON.parse(readFileSync(LOCK_PATH, 'utf-8'));
  } catch (e) {
    // Corrupt or partially-written lock — treat as absent so caller overwrites.
    return null;
  }
}

export function isStale(lock) {
  if (!lock || typeof lock.acquired_at !== 'number') return true;
  const age = Date.now() - lock.acquired_at;
  return age > STALE_THRESHOLD_MS;
}

export async function acquireLock({ timeoutMs = DEFAULT_TIMEOUT_MS, reason = '' } = {}) {
  const deadline = Date.now() + timeoutMs;
  const myLock = { pid: process.pid, acquired_at: Date.now(), reason };

  while (Date.now() < deadline) {
    const existing = readLock();
    if (!existing || isStale(existing)) {
      try {
        // flag:'w' = O_TRUNC | O_CREAT | O_WRONLY (NOT O_EXCL — see header comment).
        writeFileSync(LOCK_PATH, JSON.stringify(myLock, null, 2), { flag: 'w' });
        // Read-back-and-verify: poor-man's compare-and-swap.
        const readBack = readLock();
        if (readBack && readBack.pid === process.pid && readBack.acquired_at === myLock.acquired_at) {
          return myLock;
        }
      } catch (e) {
        // Race: another process wrote between our read and write. Retry.
      }
    }
    await sleep(POLL_INTERVAL_MS);
  }
  const blocker = readLock();
  throw new Error(`Lock acquire timeout after ${timeoutMs}ms. Blocker: ${JSON.stringify(blocker)}`);
}

export function releaseLock(myLock) {
  const existing = readLock();
  if (existing && existing.pid === myLock.pid && existing.acquired_at === myLock.acquired_at) {
    try {
      unlinkSync(LOCK_PATH);
    } catch (e) {
      // Already gone — fine.
    }
  }
  // If existing.pid != myLock.pid, another process owns the lock now. Do not unlink.
}

export async function withLock(fn, opts = {}) {
  const lock = await acquireLock(opts);
  try {
    return await fn();
  } finally {
    releaseLock(lock);
  }
}
