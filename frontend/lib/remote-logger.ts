/**
 * Remote Logger - Sends frontend logs to backend for debugging
 *
 * Intercepts console.log/warn/error and batches entries to POST /logs/ingest.
 * Includes offline queueing and automatic retry.
 */

import { api } from './api';

const BATCH_INTERVAL_MS = 5000; // Send every 5 seconds
const MAX_BATCH_SIZE = 50; // Or when we hit 50 entries
const MAX_QUEUE_SIZE = 500; // Don't let queue grow unbounded

interface LogEntry {
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  timestamp: string;
  context?: Record<string, unknown>;
}

let logQueue: LogEntry[] = [];
let batchTimer: ReturnType<typeof setTimeout> | null = null;
let isInitialized = false;
let isSending = false;

// Store original console methods
const originalConsole = {
  log: console.log.bind(console),
  info: console.info.bind(console),
  warn: console.warn.bind(console),
  error: console.error.bind(console),
  debug: console.debug.bind(console),
};

function formatArgs(args: unknown[]): string {
  return args
    .map(arg => {
      if (typeof arg === 'string') return arg;
      if (arg instanceof Error) return `${arg.name}: ${arg.message}`;
      try {
        return JSON.stringify(arg);
      } catch {
        return String(arg);
      }
    })
    .join(' ');
}

function queueLog(level: LogEntry['level'], args: unknown[]): void {
  if (logQueue.length >= MAX_QUEUE_SIZE) {
    // Drop oldest entries if queue is full
    logQueue = logQueue.slice(-MAX_QUEUE_SIZE + 1);
  }

  logQueue.push({
    level,
    message: formatArgs(args),
    timestamp: new Date().toISOString(),
  });

  // Trigger send if we hit batch size
  if (logQueue.length >= MAX_BATCH_SIZE) {
    flushLogs();
  }
}

async function flushLogs(): Promise<void> {
  if (isSending || logQueue.length === 0) return;

  isSending = true;
  const entriesToSend = [...logQueue];
  logQueue = [];

  try {
    await api.sendLogs(entriesToSend);
  } catch (error) {
    // Put entries back on failure
    logQueue = [...entriesToSend, ...logQueue].slice(-MAX_QUEUE_SIZE);
    originalConsole.warn(`[RemoteLogger] Failed to send logs:`, error);
  } finally {
    isSending = false;
  }
}

function startBatchTimer(): void {
  if (batchTimer) return;
  batchTimer = setInterval(() => {
    flushLogs();
  }, BATCH_INTERVAL_MS);
}

function stopBatchTimer(): void {
  if (batchTimer) {
    clearInterval(batchTimer);
    batchTimer = null;
  }
}

export const remoteLogger = {
  /**
   * Initialize remote logging by intercepting console methods.
   * Call once at app startup after auth is ready.
   */
  init(): void {
    if (isInitialized) return;

    console.log = (...args: unknown[]) => {
      originalConsole.log(...args);
      queueLog('info', args);
    };

    console.info = (...args: unknown[]) => {
      originalConsole.info(...args);
      queueLog('info', args);
    };

    console.warn = (...args: unknown[]) => {
      originalConsole.warn(...args);
      queueLog('warn', args);
    };

    console.error = (...args: unknown[]) => {
      originalConsole.error(...args);
      queueLog('error', args);
    };

    console.debug = (...args: unknown[]) => {
      originalConsole.debug(...args);
      queueLog('debug', args);
    };

    startBatchTimer();
    isInitialized = true;
    originalConsole.log('[RemoteLogger] Initialized');
  },

  /**
   * Stop remote logging and restore original console methods.
   */
  destroy(): void {
    if (!isInitialized) return;

    stopBatchTimer();
    flushLogs(); // Send remaining logs

    console.log = originalConsole.log;
    console.info = originalConsole.info;
    console.warn = originalConsole.warn;
    console.error = originalConsole.error;
    console.debug = originalConsole.debug;

    isInitialized = false;
  },

  /**
   * Manually flush any pending logs.
   */
  flush(): Promise<void> {
    return flushLogs();
  },
};
