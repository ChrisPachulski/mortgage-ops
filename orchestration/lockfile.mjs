// orchestration/lockfile.mjs
// Cross-process mutex for serializing DuckDB writes via data/.lock.
// Ported verbatim from career-ops/scripts/lockfile.mjs (Phase 9 PATTERNS.md
// Critical Issue 1) with three renames: CAREER_OPS -> MORTGAGE_OPS,
// .career-ops.lock -> .lock, header citation block.
//
// PERS-04 + PERS-05 + ROADMAP SC-3: 60s stale-lock recovery.
// Plan 09-01 D-01-01: acquisition uses O_EXCL (`wx`) so creating data/.lock is
// the compare-and-swap. Stale locks are removed only while holding
// data/.lock.stale-recovery, also acquired with O_EXCL.
//
// Plan 09-01 D-01-02: stale recovery is acquired_at-based (JSON content),
// NOT mtime-based. Deliberate: mtime is vulnerable to filesystem `touch`
// and clock-skew between fs-clock and process-clock. The JSON-content
// timestamp is set deterministically by the writer in the same wall-clock
// domain that reads it back.

import { closeSync, existsSync, openSync, readFileSync, unlinkSync, writeFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const MORTGAGE_OPS = dirname(dirname(fileURLToPath(import.meta.url)));
const LOCK_PATH = process.env.MORTGAGE_OPS_LOCK_PATH || join(MORTGAGE_OPS, 'data', '.lock');
const STALE_RECOVERY_LOCK_PATH = `${LOCK_PATH}.stale-recovery`;

export const STALE_THRESHOLD_MS = 60_000;
export const DEFAULT_TIMEOUT_MS = 30_000;
export const POLL_INTERVAL_MS = 100;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function readJsonFile(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch (e) {
    // Corrupt or partially-written lock — treat as absent so caller overwrites.
    return null;
  }
}

export function readLock() {
  return readJsonFile(LOCK_PATH);
}

export function isStale(lock) {
  if (!lock || typeof lock.acquired_at !== 'number') return true;
  const age = Date.now() - lock.acquired_at;
  return age > STALE_THRESHOLD_MS;
}

function writeExclusiveJson(path, payload) {
  const fd = openSync(path, 'wx');
  try {
    writeFileSync(fd, JSON.stringify(payload, null, 2));
  } finally {
    closeSync(fd);
  }
}

function unlinkIfExists(path) {
  try {
    unlinkSync(path);
  } catch (e) {
    if (e.code !== 'ENOENT') {
      throw e;
    }
  }
}

function tryClearStaleRecoveryLock() {
  const recovery = readJsonFile(STALE_RECOVERY_LOCK_PATH);
  if ((recovery && isStale(recovery)) || (recovery === null && existsSync(STALE_RECOVERY_LOCK_PATH))) {
    unlinkIfExists(STALE_RECOVERY_LOCK_PATH);
  }
}

function sameLock(a, b) {
  if (!a || !b) {
    return a === b;
  }
  return a.pid === b.pid && a.acquired_at === b.acquired_at;
}

function tryRemoveStaleLock(observedLock) {
  if (observedLock && !isStale(observedLock)) {
    return false;
  }

  const recoveryLock = {
    pid: process.pid,
    acquired_at: Date.now(),
    reason: 'stale-lock-recovery',
  };

  try {
    writeExclusiveJson(STALE_RECOVERY_LOCK_PATH, recoveryLock);
  } catch (e) {
    if (e.code === 'EEXIST') {
      tryClearStaleRecoveryLock();
      return false;
    }
    throw e;
  }

  try {
    const current = readLock();
    if ((current === null || isStale(current)) && sameLock(current, observedLock)) {
      unlinkIfExists(LOCK_PATH);
      return true;
    }
    return false;
  } finally {
    const currentRecovery = readJsonFile(STALE_RECOVERY_LOCK_PATH);
    if (sameLock(currentRecovery, recoveryLock)) {
      unlinkIfExists(STALE_RECOVERY_LOCK_PATH);
    }
  }
}

export async function acquireLock({ timeoutMs = DEFAULT_TIMEOUT_MS, reason = '' } = {}) {
  const deadline = Date.now() + timeoutMs;
  const myLock = { pid: process.pid, acquired_at: Date.now(), reason };

  while (Date.now() < deadline) {
    try {
      writeExclusiveJson(LOCK_PATH, myLock);
      return myLock;
    } catch (e) {
      if (e.code !== 'EEXIST') {
        throw e;
      }
      const existing = readLock();
      tryRemoveStaleLock(existing);
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
