import { isRecord, readString } from './managementApi';

export type OAuthModelDefinition = {
  id: string;
  displayName?: string;
};

export const oauthModelsFromPayload = (payload: unknown): OAuthModelDefinition[] => {
  if (!isRecord(payload) || !Array.isArray(payload.models)) return [];
  const seen = new Set<string>();
  return payload.models.flatMap((item) => {
    if (!isRecord(item)) return [];
    const id = readString(item, 'id', 'name');
    const key = id.toLowerCase();
    if (!id || seen.has(key)) return [];
    seen.add(key);
    const displayName = readString(item, 'display_name', 'displayName');
    return [{ id, displayName: displayName && displayName !== id ? displayName : undefined }];
  });
};

export const oauthExcludedRulesFromPayload = (payload: unknown, provider: string): string[] => {
  if (!isRecord(payload)) return [];
  const source = isRecord(payload['oauth-excluded-models'])
    ? payload['oauth-excluded-models']
    : payload;
  const value = source[provider.trim().toLowerCase()];
  if (!Array.isArray(value)) return [];
  return value
    .map(String)
    .map((rule) => rule.trim().toLowerCase())
    .filter((rule, index, rules) => rule && rules.indexOf(rule) === index);
};

const wildcardPattern = (rule: string) => new RegExp(
  `^${rule.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*')}$`,
  'i',
);

export const modelMatchesRule = (modelId: string, rule: string) => {
  const normalizedRule = rule.trim();
  if (!normalizedRule) return false;
  return wildcardPattern(normalizedRule).test(modelId.trim());
};

export const openOAuthModelNames = (
  models: OAuthModelDefinition[],
  excludedRules: Iterable<string>,
) => {
  const rules = Array.from(excludedRules, (rule) => rule.trim()).filter(Boolean);
  return new Set(
    models
      .filter((model) => !rules.some((rule) => modelMatchesRule(model.id, rule)))
      .map((model) => model.id.toLowerCase()),
  );
};

export const exclusionsForOpenOAuthModels = (
  currentRules: Iterable<string>,
  models: OAuthModelDefinition[],
  openModelNames: Iterable<string>,
) => {
  const open = new Set(
    Array.from(openModelNames, (name) => name.trim().toLowerCase()).filter(Boolean),
  );
  const modelIds = new Set(models.map((model) => model.id.toLowerCase()));
  const openedModels = models.filter((model) => open.has(model.id.toLowerCase()));
  const preservedRules = Array.from(currentRules, (rule) => rule.trim().toLowerCase())
    .filter(Boolean)
    .filter((rule) => {
      if (modelIds.has(rule)) return false;
      return !openedModels.some((model) => modelMatchesRule(model.id, rule));
    });
  const closedModels = models
    .filter((model) => !open.has(model.id.toLowerCase()))
    .map((model) => model.id.toLowerCase());

  return [...preservedRules, ...closedModels]
    .filter((rule, index, rules) => rules.indexOf(rule) === index)
    .sort();
};
