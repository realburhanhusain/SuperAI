import { describe, expect, it } from 'bun:test';
import {
  codexSessionPageCounts,
  retainVisibleCodexSessionIds,
} from '../src/services/codexSessionState';

describe('Codex session page state', () => {
  it('counts active and archived sessions on the current page', () => {
    expect(codexSessionPageCounts([
      { archived: false },
      { archived: true },
      { archived: false },
    ])).toEqual({ active: 2, archived: 1 });
  });

  it('drops selections that are no longer on the visible page', () => {
    expect(Array.from(retainVisibleCodexSessionIds(
      new Set(['thread-a', 'thread-c']),
      [{ id: 'thread-a' }, { id: 'thread-b' }],
    ))).toEqual(['thread-a']);
  });
});
