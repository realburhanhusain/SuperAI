export type AgentConfigurationClientId =
  | 'claude-code'
  | 'claude-desktop'
  | 'codex'
  | 'opencode'
  | 'openclaw'
  | 'hermes'
  | 'pi';

export type AgentConfigurationModificationState = 'unconfigured' | 'applied' | 'invalid';

export type AgentConfigurationAction = 'apply' | 'update' | 'close';

export type AgentModelMappings = {
  opus: string;
  sonnet: string;
  haiku: string;
};

type ResolveAgentConfigurationActionOptions = {
  client: AgentConfigurationClientId;
  modificationState: AgentConfigurationModificationState;
  selectedModel: string;
  appliedModel: string;
  oauthConfiguration: boolean;
  appliedOauthConfiguration: boolean;
  modelMappings: AgentModelMappings;
  appliedModelMappings: AgentModelMappings;
};

const normalizedModel = (value: string) => value.trim().toLocaleLowerCase();

export const sameAgentModel = (left: string, right: string) => (
  normalizedModel(left) === normalizedModel(right)
);

export const sameAgentModelMappings = (
  left: AgentModelMappings,
  right: AgentModelMappings,
) => sameAgentModel(left.opus, right.opus)
  && sameAgentModel(left.sonnet, right.sonnet)
  && sameAgentModel(left.haiku, right.haiku);

export function resolveAgentConfigurationAction({
  client,
  modificationState,
  selectedModel,
  appliedModel,
  oauthConfiguration,
  appliedOauthConfiguration,
  modelMappings,
  appliedModelMappings,
}: ResolveAgentConfigurationActionOptions): AgentConfigurationAction {
  if (modificationState !== 'applied') return 'apply';
  if (client === 'pi') return 'close';

  const modelChanged = client === 'claude-code' || client === 'claude-desktop'
    ? !sameAgentModelMappings(modelMappings, appliedModelMappings)
    : Boolean(
      selectedModel.trim()
        && appliedModel.trim()
        && !sameAgentModel(selectedModel, appliedModel),
    );
  const oauthChanged = client === 'codex'
    && oauthConfiguration !== appliedOauthConfiguration;

  return modelChanged || oauthChanged ? 'update' : 'close';
}
