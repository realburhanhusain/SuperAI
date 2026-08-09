import { describe, expect, it } from 'bun:test';
import {
  exclusionsForOpenOAuthModels,
  oauthExcludedRulesFromPayload,
  oauthModelsFromPayload,
  openOAuthModelNames,
} from '../src/services/oauthModels';

const models = [
  { id: 'gpt-5.4', displayName: 'GPT 5.4' },
  { id: 'gpt-image-1.5', displayName: 'GPT Image 1.5' },
  { id: 'gpt-image-2', displayName: 'GPT Image 2' },
];

describe('OAuth 开放模型', () => {
  it('解析模型定义和提供商排除规则', () => {
    expect(oauthModelsFromPayload({ models: [
      { id: 'gpt-5.4', display_name: 'GPT 5.4' },
      { id: 'GPT-5.4' },
    ] })).toEqual([{ id: 'gpt-5.4', displayName: 'GPT 5.4' }]);
    expect(oauthExcludedRulesFromPayload({
      'oauth-excluded-models': { codex: [' GPT-IMAGE-* ', 'gpt-image-*'] },
    }, 'codex')).toEqual(['gpt-image-*']);
  });

  it('排除规则会让图像模型默认不勾选', () => {
    expect(Array.from(openOAuthModelNames(models, ['gpt-image-*']))).toEqual(['gpt-5.4']);
  });

  it('OAuth 没有已保存排除规则时默认全选全部模型', () => {
    expect(Array.from(openOAuthModelNames(models, []))).toEqual([
      'gpt-5.4',
      'gpt-image-1.5',
      'gpt-image-2',
    ]);
  });

  it('保存时把未勾选模型转换成 OAuth 排除规则', () => {
    expect(exclusionsForOpenOAuthModels([], models, ['gpt-5.4'])).toEqual([
      'gpt-image-1.5',
      'gpt-image-2',
    ]);
  });

  it('显式开放模型时移除与其冲突的旧通配符', () => {
    expect(exclusionsForOpenOAuthModels(
      ['gpt-image-*', 'future-*'],
      models,
      ['gpt-5.4', 'gpt-image-2'],
    )).toEqual(['future-*', 'gpt-image-1.5']);
  });
});
