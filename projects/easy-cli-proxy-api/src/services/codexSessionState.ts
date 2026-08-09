export type CodexSessionSummary = {
  id: string;
  title: string;
  cwd: string;
  modelProvider: string;
  archived: boolean;
  updatedAtMs: number | null;
  databasePath: string;
};

export type CodexSessionPage = {
  codexHome: string;
  databasePaths: string[];
  sessions: CodexSessionSummary[];
  offset: number;
  limit: number;
  hasMore: boolean;
  repairOnLaunch: boolean;
  warnings: string[];
};

export type CodexSessionDeleteResult = {
  sessionId: string;
  status: 'deleted' | 'partial' | 'notFound' | 'failed';
  message: string;
  backupPath: string | null;
};

export type CodexSessionDeleteBatchResult = {
  results: CodexSessionDeleteResult[];
  deletedCount: number;
  failedCount: number;
};

export type CodexSessionRepairProgress = {
  phase: 'scanning' | 'backingUp' | 'rewriting' | 'updatingDatabase' | 'complete';
  percent: number;
  processed: number;
  total: number;
};

export type CodexSessionRepairResult = {
  targetProvider: string;
  changedRolloutFiles: number;
  sqliteRowsUpdated: number;
  skippedLockedFiles: string[];
  backupPath: string | null;
  encryptedContentWarning: string | null;
  warnings: string[];
};

export type SessionIndexCleanupCandidate = {
  id: string;
  threadName: string;
  updatedAt: string;
};

export type SessionIndexCleanupPreview = {
  snapshotSha256: string;
  candidates: SessionIndexCleanupCandidate[];
};

export type SessionIndexCleanupResult = {
  prunedEntries: number;
  backupPath: string | null;
};

export type CodexSessionPageCounts = {
  active: number;
  archived: number;
};

export function codexSessionPageCounts(
  sessions: readonly Pick<CodexSessionSummary, 'archived'>[],
): CodexSessionPageCounts {
  const archived = sessions.reduce(
    (count, session) => count + Number(session.archived),
    0,
  );
  return { active: sessions.length - archived, archived };
}

export function retainVisibleCodexSessionIds(
  selectedIds: ReadonlySet<string>,
  sessions: readonly Pick<CodexSessionSummary, 'id'>[],
): Set<string> {
  const visibleIds = new Set(sessions.map((session) => session.id));
  return new Set(Array.from(selectedIds).filter((id) => visibleIds.has(id)));
}
