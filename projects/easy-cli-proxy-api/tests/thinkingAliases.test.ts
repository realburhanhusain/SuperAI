import { describe, expect, test } from 'bun:test';
import {
  combineModelAliasEntries,
  combineModelAliasSources,
  defaultModelAlias,
  thinkingAliasSourceKindLabel,
  uniqueModelAlias,
} from '../src/pages/ThinkingAliasesPage';

describe('模型别名默认名称', () => {
  test('按思考强度和 Fast 选项生成可编辑的默认名称', () => {
    expect(defaultModelAlias('gpt-5.6-sol', 'XHigh', false)).toBe('gpt-5.6-sol-xhigh');
    expect(defaultModelAlias('gpt-5.6-sol', '', true)).toBe('gpt-5.6-sol-fast');
    expect(defaultModelAlias('gpt-5.6-sol', 'xhigh', true)).toBe('gpt-5.6-sol-xhigh-fast');
    expect(defaultModelAlias('gpt-5.6-sol', '', false)).toBe('');
  });

  test('默认别名与现有模型重名时递增数字后缀', () => {
    expect(uniqueModelAlias('gpt-5.6-sol-fast', ['gpt-5.6-sol-fast'])).toBe('gpt-5.6-sol-fast-2');
    expect(uniqueModelAlias('gpt-5.6-sol-fast', [
      'gpt-5.6-sol-fast',
      'gpt-5.6-sol-fast-2',
    ])).toBe('gpt-5.6-sol-fast-3');
    expect(uniqueModelAlias('gpt-5.6-sol-fast', ['GPT-5.6-SOL-FAST'])).toBe('gpt-5.6-sol-fast-2');
    expect(uniqueModelAlias('gpt-5.6-sol-fast', ['gpt-5.6-sol'])).toBe('gpt-5.6-sol-fast');
  });
});

describe('思考别名', () => {
  test('区分同名模型的接入来源', () => {
    expect(thinkingAliasSourceKindLabel('codex-oauth')).toBe('Codex OAuth');
    expect(thinkingAliasSourceKindLabel('codex-api')).toBe('Codex API');
    expect(thinkingAliasSourceKindLabel('openai-compatible')).toBe('OpenAI 兼容');
    expect(thinkingAliasSourceKindLabel('custom')).toBe('其他来源');
  });
});

describe('统一模型别名列表', () => {
  test('同时显示思考别名和 Fast 速度别名', () => {
    const entries = combineModelAliasEntries(
      [{
        sourceModel: 'gpt-thinking',
        alias: 'gpt-high',
        effort: 'high',
        provider: 'Provider B',
        kind: 'openai-compatible',
      }],
      [{
        sourceModel: 'gpt-fast-source',
        alias: 'gpt-fast',
        serviceTier: 'priority',
        provider: 'Provider A',
        kind: 'codex-api',
      }],
    );

    expect(entries.map((entry) => [entry.alias, entry.effort, entry.serviceTier])).toEqual([
      ['gpt-fast', null, 'priority'],
      ['gpt-high', 'high', null],
    ]);
  });

  test('同一个别名可同时设置思考强度和 Fast', () => {
    const identity = {
      sourceModel: 'gpt-5.6-sol',
      alias: 'gpt-5.6-sol-xhigh-fast',
      provider: 'Codex OAuth',
      kind: 'codex-oauth',
    };
    const entries = combineModelAliasEntries(
      [{ ...identity, effort: 'xhigh' }],
      [{ ...identity, serviceTier: 'priority' }],
    );

    expect(entries).toHaveLength(1);
    expect(entries[0]).toMatchObject({ effort: 'xhigh', serviceTier: 'priority' });
  });

  test('速度模型与思考模型合并后保留思考能力标记', () => {
    const baseSource = {
      model: 'gpt-5.6-sol',
      displayName: 'GPT-5.6 Sol',
      provider: 'Codex OAuth',
      kind: 'codex-oauth',
      protocol: 'codex',
    };
    const sources = combineModelAliasSources(
      [{ ...baseSource, id: 'reasoning-and-fast' }],
      [
        { ...baseSource, id: 'reasoning-and-fast' },
        { ...baseSource, id: 'fast-only', model: 'gpt-speed-only' },
      ],
    );

    expect(sources).toHaveLength(2);
    expect(sources.find((source) => source.id === 'reasoning-and-fast')?.supportsReasoning).toBe(true);
    expect(sources.find((source) => source.id === 'reasoning-and-fast')?.supportsFast).toBe(true);
    expect(sources.find((source) => source.id === 'fast-only')?.supportsReasoning).toBe(false);
    expect(sources.find((source) => source.id === 'fast-only')?.supportsFast).toBe(true);
  });
});
