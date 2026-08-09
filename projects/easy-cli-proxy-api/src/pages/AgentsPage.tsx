import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ComponentType,
  type KeyboardEvent,
} from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { open } from '@tauri-apps/plugin-dialog';
import {
  AlertTriangle,
  AppWindow,
  BadgeCheck,
  Bot,
  Check,
  ChevronDown,
  LoaderCircle,
  Play,
  Power,
  RefreshCw,
  Search,
  Terminal,
  Trash2,
  Wrench,
  X,
} from 'lucide-react';
import claudeIcon from '../assets/icons/claude.svg';
import codexIcon from '../assets/icons/codex.svg';
import hermesIcon from '../assets/icons/hermes.png';
import openclawIcon from '../assets/icons/openclaw.svg';
import opencodeIcon from '../assets/icons/opencode.svg';
import piIcon from '../assets/icons/pi-logo-on-light.svg';
import {
  agentModelAlias,
  filterAgentModels,
  filterAgentModelsByAlias,
  findAgentModel,
  resolveAgentModelForAliasMode,
  resolveAgentModelSelection,
} from '../services/agentModelPicker';
import {
  resolveAgentConfigurationAction,
  sameAgentModel,
  sameAgentModelMappings,
} from '../services/agentConfigurationDraft';
import type { ModelOption } from '../services/modelService';
import { getCurrentLocale, translate, useI18n } from '../i18n';
import { CodexSessionAutoRestoreCard } from './CodexSessionAutoRestoreCard';
import { CodexSessionsPanel } from './CodexSessionsPanel';

type AgentClientId =
  | 'claude-code'
  | 'claude-desktop'
  | 'codex'
  | 'opencode'
  | 'openclaw'
  | 'hermes'
  | 'pi';

type AgentModificationState = 'unconfigured' | 'applied' | 'invalid';

type AgentConfigStatus = {
  id: AgentClientId;
  name: string;
  supportedPlatform: boolean;
  installed: boolean;
  pluginInstalled: boolean;
  executablePath: string | null;
  launchTargets: AgentLaunchTarget[];
  version: string | null;
  cliVersion: string | null;
  appVersion: string | null;
  pluginVersion: string | null;
  configValid: boolean;
  configured: boolean;
  currentModel: string | null;
  oauthConfiguration: boolean;
  modificationEnabled: boolean;
  modificationState: AgentModificationState;
  backupAvailable: boolean;
  appliedModel: string | null;
  claudeCodeModelMappings: ClaudeModelMappings | null;
  claudeDesktopModelMappings: ClaudeModelMappings | null;
  claudeCodeWorkingDirectory: string | null;
  claudeCodeWorkingDirectoryPromptDisabled: boolean;
  warnings: string[];
  error: string | null;
};

type AgentLaunchTarget = {
  id: string;
  label: string;
  detail: string;
};

type AgentConfigActionResult = {
  outcome: 'applied' | 'default';
  enabled: boolean;
  model: string | null;
  changedFiles: string[];
  conflictFiles: string[];
};

type PiProviderUpdateStatus = {
  installedVersion: string | null;
  latestVersion: string | null;
  updateAvailable: boolean;
};

type ChatGptCloseResult = {
  wasRunning: boolean;
  closedProcesses: number;
};

type OAuthLoginRequiredAction = 'enable' | 'apply' | 'launch';

type ClaudeModelMappings = {
  opus: string;
  sonnet: string;
  haiku: string;
};

const CODEX_OAUTH_LOGIN_REQUIRED_ERROR = 'CODEX_OAUTH_LOGIN_REQUIRED';

const createClaudeModelMappings = (model: string): ClaudeModelMappings => ({
  opus: model,
  sonnet: model,
  haiku: model,
});

const claudeMappingRoles = [
  {
    key: 'opus',
    labelKey: 'agents.claudeDesktopMapping.opus',
  },
  {
    key: 'sonnet',
    labelKey: 'agents.claudeDesktopMapping.sonnet',
  },
  {
    key: 'haiku',
    labelKey: 'agents.claudeDesktopMapping.haiku',
  },
] as const;

type AgentDefinition = {
  id: AgentClientId;
  name: string;
  icon?: string;
  Icon?: ComponentType<{ size?: number; 'aria-hidden'?: boolean }>;
  descriptionKey: 'agents.description.claudeCode' | 'agents.description.claudeDesktop' | 'agents.description.codex' | 'agents.description.opencode' | 'agents.description.openclaw' | 'agents.description.hermes' | 'agents.description.pi';
};

type AgentSubpageId = 'core' | 'sessions';

type AgentSubpageDefinition = {
  id: AgentSubpageId;
  labelKey: 'agents.tabs.core' | 'agents.tabs.sessions';
  clients?: readonly AgentClientId[];
};

const agentDefinitions: AgentDefinition[] = [
  {
    id: 'claude-code',
    name: 'Claude Code',
    icon: claudeIcon,
    descriptionKey: 'agents.description.claudeCode',
  },
  {
    id: 'claude-desktop',
    name: 'Claude Desktop',
    icon: claudeIcon,
    descriptionKey: 'agents.description.claudeDesktop',
  },
  {
    id: 'codex',
    name: 'Codex',
    icon: codexIcon,
    descriptionKey: 'agents.description.codex',
  },
  {
    id: 'opencode',
    name: 'OpenCode',
    icon: opencodeIcon,
    descriptionKey: 'agents.description.opencode',
  },
  {
    id: 'openclaw',
    name: 'OpenClaw',
    icon: openclawIcon,
    descriptionKey: 'agents.description.openclaw',
  },
  {
    id: 'hermes',
    name: 'Hermes Agent',
    icon: hermesIcon,
    descriptionKey: 'agents.description.hermes',
  },
  {
    id: 'pi',
    name: 'Pi',
    icon: piIcon,
    descriptionKey: 'agents.description.pi',
  },
];

const agentSubpages: AgentSubpageDefinition[] = [
  {
    id: 'core',
    labelKey: 'agents.tabs.core',
  },
  {
    id: 'sessions',
    labelKey: 'agents.tabs.sessions',
    clients: ['codex'],
  },
];

const DEFAULT_AGENT_SUBPAGE: AgentSubpageId = 'core';

const AGENT_MODEL_SELECTIONS_KEY = 'cpa-gui.agent-model-selections.v1';
const AGENT_SELECTED_CLIENT_KEY = 'cpa-gui.agent-selected-client.v1';

const readSelectedAgentClient = (): AgentClientId => {
  const fallback = agentDefinitions[0].id;
  if (typeof window === 'undefined') return fallback;
  try {
    const saved = window.localStorage.getItem(AGENT_SELECTED_CLIENT_KEY);
    return agentDefinitions.some((agent) => agent.id === saved)
      ? (saved as AgentClientId)
      : fallback;
  } catch {
    return fallback;
  }
};

const writeSelectedAgentClient = (client: AgentClientId) => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(AGENT_SELECTED_CLIENT_KEY, client);
  } catch {
    // Keep the current in-memory selection when persistent storage is unavailable.
  }
};

const readAgentModelSelections = (): Partial<Record<AgentClientId, string>> => {
  if (typeof window === 'undefined') return {};
  try {
    const payload = window.localStorage.getItem(AGENT_MODEL_SELECTIONS_KEY);
    if (!payload) return {};
    const parsed = JSON.parse(payload) as Record<string, unknown>;
    return agentDefinitions.reduce<Partial<Record<AgentClientId, string>>>((result, agent) => {
      const value = parsed[agent.id];
      if (typeof value === 'string' && value.trim()) result[agent.id] = value.trim();
      return result;
    }, {});
  } catch {
    return {};
  }
};

const writeAgentModelSelections = (
  selections: Partial<Record<AgentClientId, string>>,
) => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(AGENT_MODEL_SELECTIONS_KEY, JSON.stringify(selections));
  } catch {
    // Local storage can be unavailable in hardened webviews; the in-memory selection still works.
  }
};

function AgentMark({ definition, size = 26 }: { definition: AgentDefinition; size?: number }) {
  if (definition.icon) {
    return <img src={definition.icon} alt="" className="provider-logo" />;
  }
  const Icon = definition.Icon ?? Bot;
  return <Icon size={size} aria-hidden />;
}

const listStatusText = (status: AgentConfigStatus | undefined) => {
  const locale = getCurrentLocale();
  if (!status) return translate(locale, 'agents.list.detecting');
  if (!status.supportedPlatform) return translate(locale, 'agents.list.unsupported');
  if (!status.installed) return translate(locale, 'agents.list.notInstalled');
  if (status.id === 'pi') {
    return status.pluginInstalled
      ? translate(locale, 'agents.list.piInstalled')
      : translate(locale, 'agents.list.pluginNotInstalled');
  }
  if (status.modificationState === 'invalid') return translate(locale, 'agents.status.invalid');
  if (status.modificationState === 'applied') return translate(locale, 'agents.list.modified', { model: status.appliedModel ?? '—' });
  return status.version
    ? translate(locale, 'agents.list.installedVersion', { version: status.version })
    : translate(locale, 'agents.list.installed');
};

type AgentModelPickerProps = {
  models: ModelOption[];
  value: string;
  loading: boolean;
  error: string;
  disabled: boolean;
  onChange: (value: string) => void;
  onRefresh: () => void;
};

type AgentModelDropdownLayout = {
  top: number;
  left: number;
  width: number;
  height: number;
};

function AgentModelPicker({
  models,
  value,
  loading,
  error,
  disabled,
  onChange,
  onRefresh,
}: AgentModelPickerProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [dropdownLayout, setDropdownLayout] = useState<AgentModelDropdownLayout | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const visibleModels = useMemo(() => filterAgentModels(models, search), [models, search]);
  const choices = useMemo(
    () => visibleModels.map((model) => ({ name: model.name, alias: model.alias ?? '' })),
    [visibleModels],
  );
  const selectedModel = findAgentModel(models, value);
  const selectedName = selectedModel?.name ?? '';
  const selectedAlias = selectedName ? agentModelAlias(models, selectedName) : '';

  const updateDropdownLayout = useCallback(() => {
    const root = rootRef.current;
    if (!root) return;

    const rect = root.getBoundingClientRect();
    const edgeGap = 12;
    const triggerGap = 6;
    const preferredHeight = 282;
    const minimumHeight = 150;
    const spaceBelow = Math.max(0, window.innerHeight - rect.bottom - triggerGap - edgeGap);
    const spaceAbove = Math.max(0, rect.top - triggerGap - edgeGap);
    const placeAbove = spaceBelow < preferredHeight && spaceAbove > spaceBelow;
    const availableHeight = placeAbove ? spaceAbove : spaceBelow;
    const height = Math.min(preferredHeight, Math.max(minimumHeight, availableHeight));
    const width = Math.min(rect.width, window.innerWidth - edgeGap * 2);
    const left = Math.min(
      Math.max(edgeGap, rect.left),
      Math.max(edgeGap, window.innerWidth - edgeGap - width),
    );
    const desiredTop = placeAbove
      ? rect.top - triggerGap - height
      : rect.bottom + triggerGap;
    const top = Math.min(
      Math.max(edgeGap, desiredTop),
      Math.max(edgeGap, window.innerHeight - edgeGap - height),
    );

    setDropdownLayout({ top, left, width, height });
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      setDropdownLayout(null);
      return undefined;
    }

    updateDropdownLayout();
    window.addEventListener('resize', updateDropdownLayout);
    window.addEventListener('scroll', updateDropdownLayout);
    return () => {
      window.removeEventListener('resize', updateDropdownLayout);
      window.removeEventListener('scroll', updateDropdownLayout);
    };
  }, [open, updateDropdownLayout]);

  useEffect(() => {
    if (!open) return undefined;
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setSearch('');
    const selectedIndex = filterAgentModels(models, '').findIndex(
      (model) => model.name.toLocaleLowerCase() === value.trim().toLocaleLowerCase(),
    );
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
    requestAnimationFrame(() => searchRef.current?.focus());
  }, [open]);

  useEffect(() => {
    setActiveIndex((current) => Math.min(current, Math.max(choices.length - 1, 0)));
  }, [choices.length]);

  const choose = (name: string) => {
    onChange(name);
    setOpen(false);
  };

  const moveActive = (offset: number) => {
    if (choices.length === 0) return;
    setActiveIndex((current) => (current + offset + choices.length) % choices.length);
  };

  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      moveActive(1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      moveActive(-1);
    } else if (event.key === 'Enter' && choices[activeIndex]) {
      event.preventDefault();
      choose(choices[activeIndex].name);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false);
    }
  };

  return (
    <div className={`agent-model-picker ${open ? 'open' : ''}`} ref={rootRef}>
      <button
        type="button"
        className="agent-model-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (!open && ['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        <span>
          <strong title={selectedName || undefined}>
            {selectedName || (loading ? t('agents.model.loading') : error ? t('agents.model.loadFailed') : models.length ? t('agents.model.select') : t('agents.model.none'))}
          </strong>
          {selectedAlias ? <small title={selectedAlias}>{selectedAlias}</small> : null}
        </span>
        <ChevronDown size={17} aria-hidden />
      </button>

      {open ? (
        <div
          className="agent-model-dropdown"
          style={dropdownLayout
            ? dropdownLayout
            : { top: 0, left: 0, width: 0, height: 0, visibility: 'hidden' }}
        >
          <div className="agent-model-search">
            <Search size={15} aria-hidden />
            <input
              ref={searchRef}
              value={search}
              onChange={(event) => {
                setSearch(event.currentTarget.value);
                setActiveIndex(0);
              }}
              onKeyDown={handleSearchKeyDown}
              placeholder={t('agents.model.search')}
              role="combobox"
              aria-controls="agent-model-listbox"
              aria-expanded="true"
            />
            {search ? (
              <button
                type="button"
                className="icon-button quiet"
                onClick={() => {
                  setSearch('');
                  setActiveIndex(0);
                  searchRef.current?.focus();
                }}
                title={t('agents.model.clearSearch')}
              >
                <X size={14} />
              </button>
            ) : null}
            <button type="button" className="icon-button quiet" onClick={onRefresh} disabled={loading} title={t('agents.model.refresh')}>
              <RefreshCw size={14} className={loading ? 'spin' : ''} />
            </button>
          </div>

          <div className="agent-model-list" id="agent-model-listbox" role="listbox">
            {loading && models.length === 0 ? (
              <div className="agent-model-empty"><LoaderCircle size={18} className="spin" />{t('agents.model.fetching')}</div>
            ) : error && models.length === 0 ? (
              <div className="agent-model-empty error"><strong>{t('agents.model.loadFailed')}</strong><span>{error}</span></div>
            ) : choices.length === 0 ? (
              <div className="agent-model-empty">
                <strong>{search.trim() ? t('agents.model.noMatch') : t('agents.model.unavailable')}</strong>
                <span>{search.trim() ? t('agents.model.tryKeywords') : t('agents.model.connectFirst')}</span>
              </div>
            ) : choices.map((choice, index) => {
              const selected = choice.name.toLocaleLowerCase() === value.trim().toLocaleLowerCase();
              return (
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  className={`agent-model-option ${selected ? 'selected' : ''} ${index === activeIndex ? 'active' : ''}`}
                  key={choice.name}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => choose(choice.name)}
                >
                  <span>
                    <strong title={choice.name}>{choice.name}</strong>
                    <small>{choice.alias || t('agents.model.available')}</small>
                  </span>
                  {selected ? <Check size={16} aria-hidden /> : null}
                </button>
              );
            })}
          </div>
          <div className="agent-model-dropdown-footer">
            <span>{t('agents.model.count', { count: models.length })}</span>
            {error && models.length > 0 ? <span className="error">{t('agents.model.stale')}</span> : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function AgentsPage() {
  const { t } = useI18n();
  const [selected, setSelected] = useState<AgentClientId>(readSelectedAgentClient);
  const [activeSubpage, setActiveSubpage] = useState<AgentSubpageId>(DEFAULT_AGENT_SUBPAGE);
  const [statuses, setStatuses] = useState<AgentConfigStatus[]>([]);
  const [models, setModels] = useState<ModelOption[]>([]);
  const [modelByClient, setModelByClient] = useState<Partial<Record<AgentClientId, string>>>(
    readAgentModelSelections,
  );
  const [claudeModelMappingsDraft, setClaudeModelMappingsDraft] = useState<ClaudeModelMappings>(
    createClaudeModelMappings(''),
  );
  const [claudeCustomMapping, setClaudeCustomMapping] = useState(false);
  const [claudeCodeLaunchDialogOpen, setClaudeCodeLaunchDialogOpen] = useState(false);
  const [claudeCodeLaunchDirectory, setClaudeCodeLaunchDirectory] = useState('');
  const [claudeCodeSuppressDirectoryPrompt, setClaudeCodeSuppressDirectoryPrompt] = useState(false);
  const [claudeCodeDirectoryError, setClaudeCodeDirectoryError] = useState('');
  const [loading, setLoading] = useState(true);
  const [modelLoading, setModelLoading] = useState(false);
  const [busyAction, setBusyAction] = useState<
    'apply' | 'close-config' | 'default' | 'clear' | 'install-pi' | 'update-pi' | 'repair-pi' | 'uninstall-pi' | 'launch' | 'launch-cli' | 'launch-app' | 'close-app' | 'oauth-check' | 'directory' | null
  >(null);
  const busy = busyAction !== null;
  const [detectionError, setDetectionError] = useState('');
  const [modelError, setModelError] = useState('');
  const [modelSelectionError, setModelSelectionError] = useState('');
  const [configurationError, setConfigurationError] = useState('');
  const [launchError, setLaunchError] = useState('');
  const [defaultError, setDefaultError] = useState('');
  const [defaultConfirmOpen, setDefaultConfirmOpen] = useState(false);
  const [clearError, setClearError] = useState('');
  const [clearNotice, setClearNotice] = useState('');
  const [clearConfirmOpen, setClearConfirmOpen] = useState(false);
  const [closeAppError, setCloseAppError] = useState('');
  const [closeAppNotice, setCloseAppNotice] = useState('');
  const [closeAppConfirmOpen, setCloseAppConfirmOpen] = useState(false);
  const [oauthLoginRequiredAction, setOauthLoginRequiredAction] = useState<OAuthLoginRequiredAction | null>(null);
  const [oauthConfigurationDraft, setOauthConfigurationDraft] = useState<boolean | null>(null);
  const [piProviderUpdateStatus, setPiProviderUpdateStatus] = useState<PiProviderUpdateStatus | null>(null);
  const modelRequestRef = useRef(0);
  const piUpdateRequestRef = useRef(0);
  const claudeModelMappingsDirtyRef = useRef(false);

  const loadStatuses = useCallback(async (forceRefresh = false) => {
    const command = forceRefresh
      ? 'refresh_agent_config_statuses'
      : 'get_agent_config_statuses';
    const nextStatuses = await invoke<AgentConfigStatus[]>(command);
    setStatuses(nextStatuses);
  }, []);

  const loadModels = useCallback(async (client: AgentClientId, preferredModel = '') => {
    const requestId = modelRequestRef.current + 1;
    modelRequestRef.current = requestId;
    setModelLoading(true);
    setModelError('');
    setModels([]);
    try {
      const nextModels = await invoke<ModelOption[]>('get_agent_models', { client });
      if (modelRequestRef.current !== requestId) return;
      setModels(nextModels);
      setModelSelectionError('');
      setModelByClient((current) => {
        const next = {
          ...current,
          [client]: resolveAgentModelSelection(nextModels, current[client] ?? preferredModel),
        };
        writeAgentModelSelections(next);
        return next;
      });
    } catch (requestError) {
      if (modelRequestRef.current === requestId) setModelError(String(requestError));
    } finally {
      if (modelRequestRef.current === requestId) setModelLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setDetectionError('');
    try {
      await loadStatuses(true);
    } catch (requestError) {
      setDetectionError(String(requestError));
    } finally {
      setLoading(false);
    }
  }, [loadStatuses]);

  useEffect(() => {
    setLoading(true);
    setDetectionError('');
    void loadStatuses()
      .catch((requestError) => setDetectionError(String(requestError)))
      .finally(() => setLoading(false));
  }, [loadStatuses]);

  useEffect(() => {
    if (loading) return;
    const preferredModel = statuses.find((status) => status.id === selected)?.currentModel ?? '';
    void loadModels(selected, preferredModel);
  }, [loadModels, loading, selected]);

  useEffect(() => {
    let disposed = false;
    let stop: (() => void) | null = null;
    void listen('config-files-changed', () => {
      if (disposed) return;
      setDetectionError('');
      void loadStatuses().catch((requestError) => {
        if (!disposed) setDetectionError(String(requestError));
      });
    }).then((unlisten) => {
      if (disposed) unlisten();
      else stop = unlisten;
    });
    return () => {
      disposed = true;
      stop?.();
    };
  }, [loadStatuses]);

  useEffect(() => {
    writeSelectedAgentClient(selected);
  }, [selected]);

  useEffect(() => {
    setActiveSubpage(DEFAULT_AGENT_SUBPAGE);
    setModelSelectionError('');
    setConfigurationError('');
    setLaunchError('');
    setDefaultError('');
    setDefaultConfirmOpen(false);
    setClearError('');
    setClearNotice('');
    setClearConfirmOpen(false);
    setCloseAppError('');
    setCloseAppNotice('');
    setCloseAppConfirmOpen(false);
    setOauthLoginRequiredAction(null);
    setOauthConfigurationDraft(null);
    setClaudeCodeLaunchDialogOpen(false);
    setClaudeCodeDirectoryError('');
    claudeModelMappingsDirtyRef.current = false;
  }, [selected]);

  const activeDefinition = agentDefinitions.find((agent) => agent.id === selected)
    ?? agentDefinitions[0];
  const activeStatus = statuses.find((status) => status.id === selected) ?? null;
  const oauthConfiguration = oauthConfigurationDraft
    ?? activeStatus?.oauthConfiguration
    ?? false;
  const savedSelectedModel = modelByClient[selected] ?? '';
  const selectedModelOption = findAgentModel(models, savedSelectedModel);
  const selectedModel = selectedModelOption?.name ?? '';
  const isPiClient = selected === 'pi';
  const isClaudeModelMappingClient = selected === 'claude-code' || selected === 'claude-desktop';
  const claudeMappingModels = useMemo(
    () => filterAgentModelsByAlias(models, claudeCustomMapping),
    [claudeCustomMapping, models],
  );

  const loadPiProviderUpdateStatus = useCallback(async () => {
    const requestId = piUpdateRequestRef.current + 1;
    piUpdateRequestRef.current = requestId;
    try {
      const nextStatus = await invoke<PiProviderUpdateStatus>('check_pi_provider_update');
      if (piUpdateRequestRef.current === requestId) setPiProviderUpdateStatus(nextStatus);
    } catch {
      if (piUpdateRequestRef.current === requestId) setPiProviderUpdateStatus(null);
    }
  }, []);

  useEffect(() => {
    if (!isPiClient || !activeStatus?.pluginInstalled || !activeStatus.pluginVersion) {
      piUpdateRequestRef.current += 1;
      setPiProviderUpdateStatus(null);
      return;
    }
    void loadPiProviderUpdateStatus();
  }, [activeStatus?.pluginInstalled, activeStatus?.pluginVersion, isPiClient, loadPiProviderUpdateStatus]);

  const piPluginUpdateAvailable = Boolean(
    piProviderUpdateStatus?.updateAvailable
      && piProviderUpdateStatus.installedVersion === activeStatus?.pluginVersion
      && piProviderUpdateStatus.latestVersion,
  );
  const piPluginUpdateTitle = piPluginUpdateAvailable
    ? t('agents.pi.updateAvailable', { version: piProviderUpdateStatus?.latestVersion ?? '' })
    : activeStatus?.pluginVersion ?? undefined;

  useEffect(() => {
    if (!isClaudeModelMappingClient || !selectedModel) return;
    const appliedMappings = selected === 'claude-code'
      ? activeStatus?.claudeCodeModelMappings
      : activeStatus?.claudeDesktopModelMappings;
    if (!claudeModelMappingsDirtyRef.current && appliedMappings) {
      const appliedModels = claudeMappingRoles
        .map((role) => findAgentModel(models, appliedMappings[role.key]))
        .filter((model): model is ModelOption => model !== null);
      if (appliedModels.length === claudeMappingRoles.length) {
        setClaudeCustomMapping(appliedModels.every((model) => Boolean(model.isAlias)));
      }
    }
    setClaudeModelMappingsDraft((current) => {
      const source = claudeModelMappingsDirtyRef.current
        ? current
        : appliedMappings ?? current;
      const next: ClaudeModelMappings = {
        opus: findAgentModel(models, source.opus)?.name ?? selectedModel,
        sonnet: findAgentModel(models, source.sonnet)?.name ?? selectedModel,
        haiku: findAgentModel(models, source.haiku)?.name ?? selectedModel,
      };
      return sameAgentModelMappings(current, next) ? current : next;
    });
  }, [
    activeStatus?.claudeCodeModelMappings,
    activeStatus?.claudeDesktopModelMappings,
    isClaudeModelMappingClient,
    models,
    selected,
    selectedModel,
  ]);

  const activeLaunchTargets = activeStatus?.launchTargets ?? [];
  const defaultLaunchTarget = activeLaunchTargets[0] ?? null;
  const cliLaunchTarget = activeLaunchTargets.find((target) => target.id === 'cli') ?? null;
  const appLaunchTarget = activeLaunchTargets.find((target) => target.id === 'app') ?? null;
  const appliedModel = activeStatus?.appliedModel ?? activeStatus?.currentModel ?? '';
  const modelDraftChanged = !isClaudeModelMappingClient && Boolean(
    selectedModel.trim()
      && appliedModel.trim()
      && !sameAgentModel(selectedModel, appliedModel),
  );
  const appliedClaudeModelMappings = (selected === 'claude-code'
    ? activeStatus?.claudeCodeModelMappings
    : activeStatus?.claudeDesktopModelMappings)
    ?? createClaudeModelMappings(appliedModel);
  const claudeMappingsReady = !isClaudeModelMappingClient
    || claudeMappingRoles.every((role) =>
      Boolean(findAgentModel(models, claudeModelMappingsDraft[role.key])),
    );
  const claudeMappingDraftChanged = isClaudeModelMappingClient
    && activeStatus?.modificationState === 'applied'
    && !sameAgentModelMappings(
      claudeModelMappingsDraft,
      appliedClaudeModelMappings,
    );
  const oauthConfigurationChanged = selected === 'codex'
    && oauthConfiguration !== Boolean(activeStatus?.oauthConfiguration);
  const draftChanged = modelDraftChanged || claudeMappingDraftChanged || oauthConfigurationChanged;
  const configurationAction = resolveAgentConfigurationAction({
    client: selected,
    modificationState: activeStatus?.modificationState ?? 'unconfigured',
    selectedModel,
    appliedModel,
    oauthConfiguration,
    appliedOauthConfiguration: Boolean(activeStatus?.oauthConfiguration),
    modelMappings: claudeModelMappingsDraft,
    appliedModelMappings: appliedClaudeModelMappings,
  });
  const canEnable = Boolean(
    activeStatus?.supportedPlatform
      && activeStatus.installed
      && !modelLoading
      && (isClaudeModelMappingClient
        ? claudeMappingsReady
        : selectedModelOption),
  );
  const launchEnabled = Boolean(
    activeStatus?.supportedPlatform
      && activeStatus.installed
      && (selected === 'codex'
        || (activeStatus.modificationEnabled && activeStatus.modificationState === 'applied')),
  );
  const canLaunchTarget = (target: AgentLaunchTarget | null) => launchEnabled && Boolean(target);
  const modelHint = modelSelectionError
    || modelError
    || (modelLoading
      ? t('agents.model.readingAvailable')
      : models.length === 0
        ? ''
        : activeStatus?.modificationState === 'applied'
          ? t('agents.model.current', { model: appliedModel || '—' })
          : t('agents.model.firstSelection', { count: models.length }));
  const modificationDescription = activeStatus?.modificationState === 'invalid'
    ? t('agents.modify.invalid')
    : '';
  const refreshModels = () => {
    void loadModels(selected);
  };

  const reloadStatusesAfterAction = async () => {
    setDetectionError('');
    try {
      await loadStatuses(true);
    } catch (requestError) {
      setDetectionError(String(requestError));
    }
  };

  const selectModel = (value: string) => {
    const model = findAgentModel(models, value);
    if (!model) return;
    setModelSelectionError('');
    setModelByClient((current) => {
      const next = { ...current, [selected]: model.name };
      writeAgentModelSelections(next);
      return next;
    });
  };

  const selectClaudeModelMapping = (
    role: keyof ClaudeModelMappings,
    value: string,
  ) => {
    const model = findAgentModel(models, value);
    if (!model) return;
    claudeModelMappingsDirtyRef.current = true;
    setModelSelectionError('');
    setClaudeModelMappingsDraft((current) => ({ ...current, [role]: model.name }));
  };

  const changeClaudeCustomMapping = (enabled: boolean) => {
    setClaudeCustomMapping(enabled);
    setModelSelectionError('');
    setClaudeModelMappingsDraft((current) => {
      const next: ClaudeModelMappings = {
        opus: resolveAgentModelForAliasMode(models, current.opus, enabled),
        sonnet: resolveAgentModelForAliasMode(models, current.sonnet, enabled),
        haiku: resolveAgentModelForAliasMode(models, current.haiku, enabled),
      };
      if (!sameAgentModelMappings(current, next)) {
        claudeModelMappingsDirtyRef.current = true;
      }
      return next;
    });
  };

  const requireSelectedModel = () => {
    if (modelLoading) {
      setModelSelectionError(t('agents.error.modelsLoading'));
      return null;
    }
    if (models.length === 0) {
      setModelSelectionError(modelError || t('agents.error.noModels'));
      return null;
    }
    const model = findAgentModel(models, selectedModel);
    if (!model) {
      setModelSelectionError(t('agents.error.selectionGone'));
      return null;
    }
    setModelSelectionError('');
    return model.name;
  };

  const requireClaudeModelMappings = (): ClaudeModelMappings | null => {
    if (!isClaudeModelMappingClient) return null;
    const resolved = {} as ClaudeModelMappings;
    for (const role of claudeMappingRoles) {
      const model = findAgentModel(models, claudeModelMappingsDraft[role.key]);
      if (!model) {
        setModelSelectionError(t('agents.error.mappingSelectionGone'));
        return null;
      }
      resolved[role.key] = model.name;
    }
    return resolved;
  };

  const handleOAuthLoginError = (requestError: unknown, action: OAuthLoginRequiredAction) => {
    const message = String(requestError);
    if (message.includes(CODEX_OAUTH_LOGIN_REQUIRED_ERROR)) {
      setOauthLoginRequiredAction(action);
      return true;
    }
    return false;
  };

  const changeOauthConfiguration = async (enabled: boolean) => {
    if (!enabled) {
      setOauthConfigurationDraft(false);
      return;
    }

    setBusyAction('oauth-check');
    try {
      await invoke('check_codex_oauth_login');
      setOauthConfigurationDraft(true);
    } catch (requestError) {
      if (!handleOAuthLoginError(requestError, 'enable')) {
        setConfigurationError(String(requestError));
      }
    } finally {
      setBusyAction(null);
    }
  };

  const applyConfigurationChanges = async () => {
    setConfigurationError('');
    const claudeModelMappings = requireClaudeModelMappings();
    if (isClaudeModelMappingClient && !claudeModelMappings) return;
    const model = isClaudeModelMappingClient
      ? claudeModelMappings?.sonnet ?? null
      : requireSelectedModel();
    if (!model) return;
    setBusyAction('apply');
    try {
      await invoke<AgentConfigActionResult>('apply_agent_config', {
        client: selected,
        model,
        oauthConfiguration,
        claudeCodeModelMappings: selected === 'claude-code' ? claudeModelMappings : null,
        claudeDesktopModelMappings: selected === 'claude-desktop' ? claudeModelMappings : null,
      });
      await reloadStatusesAfterAction();
      setOauthConfigurationDraft(null);
      claudeModelMappingsDirtyRef.current = false;
    } catch (requestError) {
      if (!handleOAuthLoginError(requestError, 'apply')) {
        setConfigurationError(String(requestError));
      }
    } finally {
      setBusyAction(null);
    }
  };

  const installPiProvider = async () => {
    const model = requireSelectedModel();
    if (!model) return;
    setBusyAction('install-pi');
    setConfigurationError('');
    try {
      await invoke<AgentConfigActionResult>('install_pi_provider', { model });
      await reloadStatusesAfterAction();
    } catch (requestError) {
      setConfigurationError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const updatePiProvider = async () => {
    const model = requireSelectedModel();
    if (!model) return;
    setBusyAction('update-pi');
    setConfigurationError('');
    setPiProviderUpdateStatus(null);
    try {
      await invoke<AgentConfigActionResult>('update_pi_provider', { model });
      await reloadStatusesAfterAction();
      await loadPiProviderUpdateStatus();
    } catch (requestError) {
      setConfigurationError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const repairPiProvider = async () => {
    const model = requireSelectedModel();
    if (!model) return;
    setBusyAction('repair-pi');
    setConfigurationError('');
    try {
      await invoke<AgentConfigActionResult>('repair_pi_provider', { model });
      await reloadStatusesAfterAction();
    } catch (requestError) {
      setConfigurationError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const uninstallPiProvider = async () => {
    setBusyAction('uninstall-pi');
    setConfigurationError('');
    setPiProviderUpdateStatus(null);
    try {
      await invoke<AgentConfigActionResult>('uninstall_pi_provider');
      await reloadStatusesAfterAction();
    } catch (requestError) {
      setConfigurationError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const closeConfigurationChanges = async () => {
    setConfigurationError('');
    setBusyAction('close-config');
    try {
      await invoke<AgentConfigActionResult>('close_agent_config_modification', { client: selected });
      await reloadStatusesAfterAction();
      setOauthConfigurationDraft(null);
    } catch (requestError) {
      setConfigurationError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const resetConfigurationToDefault = async () => {
    const claudeModelMappings = requireClaudeModelMappings();
    if (isClaudeModelMappingClient && !claudeModelMappings) return;
    const model = isClaudeModelMappingClient
      ? claudeModelMappings?.sonnet ?? null
      : requireSelectedModel();
    if (!model) return;
    setBusyAction('default');
    setDefaultError('');
    try {
      await invoke<AgentConfigActionResult>('reset_agent_config_to_default', {
        client: selected,
        model,
        oauthConfiguration,
        claudeCodeModelMappings: selected === 'claude-code' ? claudeModelMappings : null,
        claudeDesktopModelMappings: selected === 'claude-desktop' ? claudeModelMappings : null,
      });
      setDefaultConfirmOpen(false);
      await reloadStatusesAfterAction();
      setOauthConfigurationDraft(null);
      claudeModelMappingsDirtyRef.current = false;
    } catch (requestError) {
      if (!handleOAuthLoginError(requestError, 'apply')) {
        setDefaultError(String(requestError));
      }
    } finally {
      setBusyAction(null);
    }
  };

  const clearCodexConfiguration = async () => {
    setBusyAction('clear');
    setClearError('');
    setClearNotice('');
    try {
      await invoke<string[]>('clear_codex_config');
      setClearConfirmOpen(false);
      setClearNotice(t('agents.clear.success'));
      await reloadStatusesAfterAction();
      setOauthConfigurationDraft(null);
    } catch (requestError) {
      setClearError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const openClaudeCodeLaunchDialog = () => {
    setClaudeCodeLaunchDirectory(activeStatus?.claudeCodeWorkingDirectory ?? '');
    setClaudeCodeSuppressDirectoryPrompt(false);
    setClaudeCodeDirectoryError('');
    setClaudeCodeLaunchDialogOpen(true);
  };

  const chooseClaudeCodeWorkingDirectory = async () => {
    setBusyAction('directory');
    setClaudeCodeDirectoryError('');
    try {
      const selectedDirectory = await open({
        directory: true,
        multiple: false,
        defaultPath: claudeCodeLaunchDirectory || activeStatus?.claudeCodeWorkingDirectory || undefined,
        title: t('agents.claudeCodeLaunch.dialogTitle'),
      });
      if (typeof selectedDirectory === 'string') {
        setClaudeCodeLaunchDirectory(selectedDirectory);
      }
    } catch (requestError) {
      setClaudeCodeDirectoryError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const invokeAgentLaunch = async (
    target: AgentLaunchTarget,
    workingDirectory: string | null = null,
    suppressWorkingDirectoryPrompt: boolean | null = null,
  ) => {
    if (!target) return;
    const launchAction = selected === 'codex'
      ? target.id === 'cli' ? 'launch-cli' : 'launch-app'
      : 'launch';
    setBusyAction(launchAction);
    setLaunchError('');
    try {
      if (draftChanged) {
        throw new Error(t('agents.error.applyFirst'));
      }
      await invoke('launch_agent', {
        client: selected,
        target: target.id,
        workingDirectory,
        suppressWorkingDirectoryPrompt,
      });
      if (selected === 'claude-code' && workingDirectory) {
        setClaudeCodeLaunchDialogOpen(false);
        await reloadStatusesAfterAction();
      }
    } catch (requestError) {
      const message = String(requestError);
      if (
        selected === 'claude-code'
        && (message.includes('CLAUDE_CODE_WORKING_DIRECTORY_REQUIRED')
          || message.includes('CLAUDE_CODE_WORKING_DIRECTORY_INVALID'))
      ) {
        openClaudeCodeLaunchDialog();
        setClaudeCodeDirectoryError(
          message.includes('CLAUDE_CODE_WORKING_DIRECTORY_INVALID') ? message : '',
        );
      } else if (selected === 'claude-code' && workingDirectory) {
        setClaudeCodeDirectoryError(message);
      } else if (!handleOAuthLoginError(requestError, 'launch')) {
        setLaunchError(message);
      }
    } finally {
      setBusyAction(null);
    }
  };

  const launchAgent = async (target: AgentLaunchTarget | null) => {
    if (!target) return;
    if (selected === 'claude-code' && !activeStatus?.claudeCodeWorkingDirectoryPromptDisabled) {
      openClaudeCodeLaunchDialog();
      return;
    }
    await invokeAgentLaunch(target);
  };

  const launchClaudeCodeFromDialog = async () => {
    const target = defaultLaunchTarget;
    if (!target) return;
    const workingDirectory = claudeCodeLaunchDirectory.trim();
    if (!workingDirectory) {
      setClaudeCodeDirectoryError(t('agents.claudeCodeLaunch.directoryRequired'));
      return;
    }
    setClaudeCodeDirectoryError('');
    await invokeAgentLaunch(
      target,
      workingDirectory,
      claudeCodeSuppressDirectoryPrompt,
    );
  };

  const closeChatGptApp = async () => {
    setBusyAction('close-app');
    setCloseAppError('');
    setCloseAppNotice('');
    try {
      const result = await invoke<ChatGptCloseResult>('close_chatgpt_app');
      setCloseAppConfirmOpen(false);
      setCloseAppNotice(result.wasRunning
        ? t('agents.closeApp.success', { count: result.closedProcesses })
        : t('agents.closeApp.notRunning'));
    } catch (requestError) {
      setCloseAppError(String(requestError));
    } finally {
      setBusyAction(null);
    }
  };

  const openDefaultConfirmation = () => {
    setDefaultError('');
    setDefaultConfirmOpen(true);
  };

  const closeDefaultConfirmation = () => {
    setDefaultError('');
    setDefaultConfirmOpen(false);
  };

  const openClearConfirmation = () => {
    setClearError('');
    setClearConfirmOpen(true);
  };

  const closeClearConfirmation = () => {
    setClearError('');
    setClearConfirmOpen(false);
  };

  const openCloseAppConfirmation = () => {
    setCloseAppError('');
    setCloseAppConfirmOpen(true);
  };

  const closeCloseAppConfirmation = () => {
    setCloseAppError('');
    setCloseAppConfirmOpen(false);
  };

  const availableSubpages = agentSubpages.filter(
    (subpage) => !subpage.clients || subpage.clients.includes(selected),
  );
  const oauthLoginRequiredDescription = oauthLoginRequiredAction === 'enable' ? (
    <>
      {t('agents.oauthLoginRequired.enableDescription')}
      <strong>{t('agents.oauthLoginRequired.enableClearConfiguration')}</strong>
      {t('agents.oauthLoginRequired.enableDescriptionSuffix')}
    </>
  ) : oauthLoginRequiredAction ? t(`agents.oauthLoginRequired.${oauthLoginRequiredAction}Description`) : '';

  return (
    <section className="page management-page agents-page">
      <header className="management-header">
        <div>
          <span>Agent Clients</span>
          <h1>{t('agents.title')}</h1>
        </div>
        <div className="agent-header-actions">
          {detectionError ? (
            <span className="agent-inline-message error" role="alert" aria-live="polite">
              {detectionError}
            </span>
          ) : null}
          <button type="button" className="secondary-button compact-button" onClick={() => void refresh()} disabled={loading || busy}>
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            {t('agents.redetect')}
          </button>
        </div>
      </header>

      <div className="agent-workbench">
        <aside className="panel agent-client-list">
          <div className="agent-list-heading">
            <Bot size={18} />
            <div><strong>{t('agents.localClients')}</strong><span>{t('agents.selectClient')}</span></div>
          </div>
          <div className="agent-list-items">
            {agentDefinitions.map((agent) => {
              const status = statuses.find((item) => item.id === agent.id);
              return (
                <button
                  type="button"
                  className={selected === agent.id ? 'active' : ''}
                  key={agent.id}
                  onClick={() => {
                    setActiveSubpage(DEFAULT_AGENT_SUBPAGE);
                    setSelected(agent.id);
                  }}
                  disabled={busy}
                >
                  <span className="agent-client-icon"><AgentMark definition={agent} /></span>
                  <span><strong>{agent.name}</strong><small>{listStatusText(status)}</small></span>
                  <i
                    className={status?.id === 'pi'
                      ? status?.installed ? 'installed' : ''
                      : status?.modificationEnabled ? 'configured' : status?.installed ? 'installed' : ''}
                    aria-hidden="true"
                  />
                </button>
              );
            })}
          </div>
        </aside>

        <section className="panel agent-config-panel">
          <div className="agent-subpage-tabs" role="tablist" aria-label={t('agents.tabs.label')}>
            {availableSubpages.map((subpage) => (
              <button
                type="button"
                id={`agent-subpage-tab-${subpage.id}`}
                role="tab"
                className={activeSubpage === subpage.id ? 'active' : ''}
                aria-selected={activeSubpage === subpage.id}
                aria-controls={`agent-subpage-panel-${subpage.id}`}
                tabIndex={activeSubpage === subpage.id ? 0 : -1}
                key={subpage.id}
                onClick={() => setActiveSubpage(subpage.id)}
              >
                {t(subpage.labelKey)}
              </button>
            ))}
          </div>

          {activeSubpage === 'core' ? (
            <div
              className="agent-core-config"
              id="agent-subpage-panel-core"
              role="tabpanel"
              aria-labelledby="agent-subpage-tab-core"
            >
              <div className={`agent-status-grid ${selected === 'codex' ? 'codex-status-grid' : isPiClient ? 'pi-status-grid' : ''}`}>
                <div>
                  <span><BadgeCheck size={14} />{t('agents.installStatus')}</span>
                  <strong>{activeStatus?.installed ? t('agents.clientDetected') : t('agents.clientNotDetected')}</strong>
                </div>
                {selected === 'codex' ? (
                  <>
                    <div>
                      <span>{t('agents.cliVersion')}</span>
                      <strong title={activeStatus?.cliVersion ?? undefined}>{activeStatus?.cliVersion ?? t('agents.notFetched')}</strong>
                    </div>
                    <div>
                      <span>{t('agents.appVersion')}</span>
                      <strong title={activeStatus?.appVersion ?? undefined}>{activeStatus?.appVersion ?? t('agents.notFetched')}</strong>
                    </div>
                  </>
                ) : isPiClient ? (
                  <>
                    <div>
                      <span>{t('agents.clientVersion')}</span>
                      <strong title={activeStatus?.version ?? undefined}>{activeStatus?.version ?? t('agents.notFetched')}</strong>
                    </div>
                    <div>
                      <span>
                        {t('agents.pluginVersion')}
                        {piPluginUpdateAvailable ? (
                          <span
                            className="agent-version-update-dot"
                            role="status"
                            aria-label={piPluginUpdateTitle}
                            title={piPluginUpdateTitle}
                          />
                        ) : null}
                      </span>
                      <strong title={piPluginUpdateTitle}>{activeStatus?.pluginVersion ?? t('agents.notFetched')}</strong>
                    </div>
                  </>
                ) : (
                  <div>
                    <span>{t('agents.clientVersion')}</span>
                    <strong title={activeStatus?.version ?? undefined}>{activeStatus?.version ?? t('agents.notFetched')}</strong>
                  </div>
                )}
              </div>

              {activeStatus?.error || activeStatus?.warnings.length ? (
                <div className="agent-status-messages" aria-live="polite">
                  {activeStatus.error ? (
                    <span className="agent-inline-message error" role="alert">{activeStatus.error}</span>
                  ) : (
                    <span className="agent-inline-message warning">{activeStatus.warnings.join('；')}</span>
                  )}
                </div>
              ) : null}

              {!isClaudeModelMappingClient ? (
                <section className="agent-core-setting-section agent-model-section">
                  <div className="agent-section-heading">
                    <div><strong>{t('agents.useModel')}</strong></div>
                  </div>
                  <AgentModelPicker
                    models={models}
                    value={selectedModel}
                    loading={modelLoading}
                    error={modelError}
                    disabled={busy || !activeStatus?.installed || !activeStatus.supportedPlatform}
                    onChange={selectModel}
                    onRefresh={refreshModels}
                  />
                  {modelHint ? (
                    <span
                      className={`agent-model-hint ${modelSelectionError || modelError ? 'error' : ''}`}
                      role={modelSelectionError || modelError ? 'alert' : undefined}
                      aria-live="polite"
                    >
                      {modelHint}
                    </span>
                  ) : null}
                </section>
              ) : null}

              {isClaudeModelMappingClient ? (
                <section className="agent-core-setting-section agent-claude-desktop-mapping">
                  <div className="agent-section-heading">
                    <div>
                      <strong>{t(selected === 'claude-code'
                        ? 'agents.claudeCodeMapping.title'
                        : 'agents.claudeDesktopMapping.title')}</strong>
                      <span>{t(selected === 'claude-code'
                        ? 'agents.claudeCodeMapping.description'
                        : 'agents.claudeDesktopMapping.description')}</span>
                    </div>
                    <div className="agent-section-heading-actions">
                      <label
                        className="agent-claude-desktop-mapping-filter"
                        title={t('agents.claudeDesktopMapping.customMappingHint')}
                      >
                        <span>{t('agents.claudeDesktopMapping.customMapping')}</span>
                        <span className="switch-control">
                          <input
                            type="checkbox"
                            checked={claudeCustomMapping}
                            onChange={(event) => changeClaudeCustomMapping(event.currentTarget.checked)}
                            disabled={busy || modelLoading}
                          />
                          <span className="switch-track" />
                        </span>
                      </label>
                    </div>
                  </div>
                  <div className="agent-claude-desktop-mapping-grid">
                    {claudeMappingRoles.map((role) => (
                      <div className="agent-claude-desktop-mapping-row" key={role.key}>
                        <strong>{t(role.labelKey)}</strong>
                        <AgentModelPicker
                          models={claudeMappingModels}
                          value={claudeModelMappingsDraft[role.key]}
                          loading={modelLoading}
                          error={modelError}
                          disabled={busy || !activeStatus?.installed || !activeStatus.supportedPlatform}
                          onChange={(value) => selectClaudeModelMapping(role.key, value)}
                          onRefresh={refreshModels}
                        />
                      </div>
                    ))}
                  </div>
                </section>
              ) : null}

              {isPiClient ? (
                <section className="agent-core-setting-section agent-modification-actions">
                  <div className="agent-section-heading">
                    <div>
                      <strong>{t('agents.pi.installTitle')}</strong>
                      <span>{t('agents.pi.installDescription')}</span>
                    </div>
                  </div>
                  <div className="agent-modification-control">
                    <div className="agent-modification-buttons">
                      <button
                        type="button"
                        className={activeStatus?.pluginInstalled ? 'danger-button' : 'primary-button'}
                        onClick={() => void (activeStatus?.pluginInstalled ? uninstallPiProvider() : installPiProvider())}
                        disabled={busy || !activeStatus?.installed || !activeStatus.supportedPlatform || (!activeStatus.pluginInstalled && !selectedModelOption)}
                      >
                        {busyAction === 'install-pi' || busyAction === 'uninstall-pi'
                          ? <LoaderCircle size={16} className="spin" />
                          : null}
                        {activeStatus?.pluginInstalled
                          ? busyAction === 'uninstall-pi' ? t('agents.pi.uninstalling') : t('agents.pi.uninstall')
                          : busyAction === 'install-pi' ? t('agents.pi.installing') : t('agents.pi.install')}
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => void repairPiProvider()}
                        disabled={busy || !activeStatus?.installed || !activeStatus.supportedPlatform || !activeStatus.pluginInstalled || !selectedModelOption}
                      >
                        {busyAction === 'repair-pi' ? <LoaderCircle size={16} className="spin" /> : <Wrench size={16} />}
                        {busyAction === 'repair-pi' ? t('agents.pi.repairing') : t('agents.pi.repair')}
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => void updatePiProvider()}
                        disabled={busy || !activeStatus?.installed || !activeStatus.supportedPlatform || !activeStatus.pluginInstalled || !selectedModelOption}
                      >
                        {busyAction === 'update-pi' ? <LoaderCircle size={16} className="spin" /> : <RefreshCw size={16} />}
                        {busyAction === 'update-pi' ? t('agents.pi.updating') : t('agents.pi.update')}
                      </button>
                    </div>
                    {configurationError ? (
                      <span className="agent-inline-message error" role="alert" aria-live="polite">
                        {configurationError}
                      </span>
                    ) : null}
                  </div>
                </section>
              ) : (
              <section className={`agent-core-setting-section agent-modification-actions ${activeStatus?.modificationState === 'applied' ? 'enabled' : ''}`}>
                <div className="agent-section-heading">
                  <div>
                    <strong>{t('agents.modify.title')}</strong>
                    {modificationDescription ? <span>{modificationDescription}</span> : null}
                  </div>
                </div>
                <div className="agent-modification-control">
                  {selected === 'codex' ? (
                    <div className="agent-codex-options">
                      <CodexSessionAutoRestoreCard />
                      <label
                        className="agent-oauth-configuration"
                        title={t('agents.modify.oauthConfiguration')}
                      >
                        <span>{t('agents.modify.oauthConfiguration')}</span>
                        <span className="switch-control">
                          <input
                            type="checkbox"
                            role="switch"
                            checked={oauthConfiguration}
                            onChange={(event) => void changeOauthConfiguration(event.currentTarget.checked)}
                            disabled={busy}
                            aria-label={t('agents.modify.oauthConfiguration')}
                          />
                          <span className="switch-track" />
                        </span>
                      </label>
                    </div>
                  ) : null}
                  <div className={`agent-modification-buttons ${selected === 'codex' ? 'codex' : ''}`}>
                    <button
                      type="button"
                      className="primary-button"
                      onClick={() => void (configurationAction === 'close'
                        ? closeConfigurationChanges()
                        : applyConfigurationChanges())}
                      disabled={
                        busy
                        || (configurationAction === 'close' ? false : !canEnable)
                      }
                    >
                      {busyAction === 'apply' || busyAction === 'close-config'
                        ? <LoaderCircle size={16} className="spin" />
                        : null}
                      {configurationAction === 'update'
                        ? t('agents.modify.update')
                        : configurationAction === 'close'
                          ? t('agents.modify.close')
                          : t('agents.modify.apply')}
                    </button>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={openDefaultConfirmation}
                      disabled={busy || !canEnable}
                    >
                      {busyAction === 'default'
                        ? <LoaderCircle size={16} className="spin" />
                        : <RefreshCw size={16} />}
                      {t('agents.modify.default')}
                    </button>
                    {selected === 'codex' ? (
                      <button
                        type="button"
                        className="danger-button"
                        onClick={openClearConfirmation}
                        disabled={busy}
                      >
                        {busyAction === 'clear' ? <LoaderCircle size={16} className="spin" /> : <Trash2 size={16} />}
                        {t('agents.modify.clear')}
                      </button>
                    ) : null}
                  </div>
                  {configurationError ? (
                    <span className="agent-inline-message error" role="alert" aria-live="polite">
                      {configurationError}
                    </span>
                  ) : null}
                  {clearNotice ? (
                    <span className="agent-inline-message" role="status" aria-live="polite">
                      {clearNotice}
                    </span>
                  ) : null}
                </div>
              </section>
              )}

              <div className="agent-config-footer">
                <div className="agent-launch-control">
                  <div className="agent-launch-actions">
                    {selected === 'codex' ? (
                      <>
                        <button
                          type="button"
                          className="secondary-button agent-launch-button"
                          onClick={() => void launchAgent(cliLaunchTarget)}
                          disabled={busy || !canLaunchTarget(cliLaunchTarget) || draftChanged}
                          title={draftChanged
                            ? t('agents.launch.applyFirst')
                            : cliLaunchTarget?.detail ?? t('agents.launch.unavailable')}
                        >
                          {busyAction === 'launch-cli' ? <LoaderCircle size={16} className="spin" /> : <Terminal size={16} />}
                          {busyAction === 'launch-cli' ? t('agents.launch.starting') : t('agents.launch.startCli')}
                        </button>
                        <button
                          type="button"
                          className="primary-button agent-launch-button"
                          onClick={() => void launchAgent(appLaunchTarget)}
                          disabled={busy || !canLaunchTarget(appLaunchTarget) || draftChanged}
                          title={draftChanged
                            ? t('agents.launch.applyFirst')
                            : appLaunchTarget?.detail ?? t('agents.launch.unavailable')}
                        >
                          {busyAction === 'launch-app' ? <LoaderCircle size={16} className="spin" /> : <AppWindow size={16} />}
                          {busyAction === 'launch-app' ? t('agents.launch.starting') : t('agents.launch.startApp')}
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className="primary-button agent-launch-button"
                        onClick={() => void launchAgent(defaultLaunchTarget)}
                        disabled={busy || !canLaunchTarget(defaultLaunchTarget) || draftChanged}
                        title={draftChanged
                          ? t('agents.launch.applyFirst')
                          : activeStatus?.modificationState === 'applied'
                            ? defaultLaunchTarget?.detail
                            : t('agents.launch.enableFirst')}
                      >
                        {busyAction === 'launch'
                          ? <LoaderCircle size={16} className="spin" />
                          : <Play size={16} />}
                        {busyAction === 'launch' ? t('agents.launch.starting') : defaultLaunchTarget ? t('agents.launch.start', { target: defaultLaunchTarget.label }) : t('agents.launch.unavailable')}
                      </button>
                    )}
                    {selected === 'codex' ? (
                      <button
                        type="button"
                        className="danger-button agent-close-app-button"
                        onClick={openCloseAppConfirmation}
                        disabled={busy}
                      >
                        {busyAction === 'close-app' ? <LoaderCircle size={16} className="spin" /> : <Power size={16} />}
                        {busyAction === 'close-app' ? t('agents.launch.closingChatgpt') : t('agents.launch.closeChatgpt')}
                      </button>
                    ) : null}
                  </div>
                  {launchError ? (
                    <span className="agent-inline-message error" role="alert" aria-live="polite">
                      {launchError}
                    </span>
                  ) : null}
                  {closeAppNotice ? (
                    <span className="agent-inline-message" role="status" aria-live="polite">
                      {closeAppNotice}
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}

          {selected === 'codex' && activeSubpage === 'sessions' ? (
            <div
              className="agent-sessions-page"
              id="agent-subpage-panel-sessions"
              role="tabpanel"
              aria-labelledby="agent-subpage-tab-sessions"
            >
              <CodexSessionsPanel />
            </div>
          ) : null}
        </section>
      </div>

      {claudeCodeLaunchDialogOpen ? (
        <div className="config-dialog-backdrop" onMouseDown={(event) => {
          if (event.currentTarget === event.target && !busy) {
            setClaudeCodeLaunchDialogOpen(false);
          }
        }}>
          <section
            className="config-dialog agent-claude-code-launch-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="agent-claude-code-launch-title"
          >
            <div className="config-dialog-heading">
              <div>
                <h2 id="agent-claude-code-launch-title">
                  {t('agents.claudeCodeLaunch.dialogTitle')}
                </h2>
              </div>
            </div>
            <p>{t('agents.claudeCodeLaunch.dialogDescription')}</p>
            <div className="config-dialog-field">
              <span>{t('agents.claudeCodeLaunch.workingDirectory')}</span>
              <button
                type="button"
                className="agent-claude-code-directory-picker"
                onClick={() => void chooseClaudeCodeWorkingDirectory()}
                disabled={busy}
                autoFocus
              >
                <span>
                  <small>{claudeCodeLaunchDirectory
                    ? t('agents.claudeCodeLaunch.selectedDirectory')
                    : t('agents.claudeCodeLaunch.noDirectory')}</small>
                  <strong title={claudeCodeLaunchDirectory || undefined}>
                    {claudeCodeLaunchDirectory || t('agents.claudeCodeLaunch.chooseDirectory')}
                  </strong>
                </span>
                <b>{busyAction === 'directory'
                  ? t('agents.claudeCodeLaunch.choosing')
                  : t('agents.claudeCodeLaunch.browse')}</b>
              </button>
            </div>
            <label className="agent-claude-code-suppress-prompt">
              <input
                type="checkbox"
                checked={claudeCodeSuppressDirectoryPrompt}
                onChange={(event) => setClaudeCodeSuppressDirectoryPrompt(event.currentTarget.checked)}
                disabled={busy}
              />
              <span>{t('agents.claudeCodeLaunch.neverAskAgain')}</span>
            </label>
            {claudeCodeDirectoryError ? (
              <span className="agent-inline-message error" role="alert" aria-live="polite">
                {claudeCodeDirectoryError}
              </span>
            ) : null}
            <div className="config-dialog-actions two-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setClaudeCodeLaunchDialogOpen(false)}
                disabled={busy}
              >
                {t('common.cancel')}
              </button>
              <button
                type="button"
                className="primary-button"
                onClick={() => void launchClaudeCodeFromDialog()}
                disabled={busy || !claudeCodeLaunchDirectory.trim()}
              >
                {busyAction === 'launch' ? <LoaderCircle size={16} className="spin" /> : null}
                {t('agents.claudeCodeLaunch.launch')}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {defaultConfirmOpen ? (
        <div className="config-dialog-backdrop">
          <section className="config-dialog agent-restore-dialog" role="alertdialog" aria-modal="true" aria-labelledby="agent-default-title">
            <div className="config-dialog-heading">
              <div><AlertTriangle size={19} /><h2 id="agent-default-title">{t('agents.default.title')}</h2></div>
            </div>
            <p>
              {t('agents.default.description', { name: activeDefinition.name })}
            </p>
            {defaultError ? (
              <span className="agent-inline-message error" role="alert" aria-live="polite">
                {defaultError}
              </span>
            ) : null}
            <div className="config-dialog-actions two-actions">
              <button type="button" className="secondary-button" onClick={closeDefaultConfirmation} disabled={busy}>{t('common.cancel')}</button>
              <button type="button" className="danger-button" onClick={() => void resetConfigurationToDefault()} disabled={busy}>
                {busyAction === 'default' ? <LoaderCircle size={16} className="spin" /> : null}
                {t('agents.default.confirm')}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {clearConfirmOpen ? (
        <div className="config-dialog-backdrop">
          <section className="config-dialog agent-restore-dialog" role="alertdialog" aria-modal="true" aria-labelledby="agent-clear-title">
            <div className="config-dialog-heading">
              <div><AlertTriangle size={19} /><h2 id="agent-clear-title">{t('agents.clear.title')}</h2></div>
            </div>
            <p>{t('agents.clear.description')}</p>
            {clearError ? (
              <span className="agent-inline-message error" role="alert" aria-live="polite">
                {clearError}
              </span>
            ) : null}
            <div className="config-dialog-actions two-actions">
              <button type="button" className="secondary-button" onClick={closeClearConfirmation} disabled={busy}>{t('common.cancel')}</button>
              <button type="button" className="danger-button" onClick={() => void clearCodexConfiguration()} disabled={busy}>
                {busyAction === 'clear' ? <LoaderCircle size={16} className="spin" /> : <Trash2 size={16} />}
                {t('agents.clear.confirm')}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {closeAppConfirmOpen ? (
        <div className="config-dialog-backdrop">
          <section className="config-dialog agent-restore-dialog" role="alertdialog" aria-modal="true" aria-labelledby="agent-close-app-title">
            <div className="config-dialog-heading">
              <div><AlertTriangle size={19} /><h2 id="agent-close-app-title">{t('agents.closeApp.title')}</h2></div>
            </div>
            <p>{t('agents.closeApp.description')}</p>
            {closeAppError ? (
              <span className="agent-inline-message error" role="alert" aria-live="polite">
                {closeAppError}
              </span>
            ) : null}
            <div className="config-dialog-actions two-actions">
              <button type="button" className="secondary-button" onClick={closeCloseAppConfirmation} disabled={busy}>{t('common.cancel')}</button>
              <button type="button" className="danger-button" onClick={() => void closeChatGptApp()} disabled={busy}>
                {busyAction === 'close-app' ? <LoaderCircle size={16} className="spin" /> : <Power size={16} />}
                {t('agents.closeApp.confirm')}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {oauthLoginRequiredAction ? (
        <div className="config-dialog-backdrop">
          <section className="config-dialog agent-restore-dialog" role="alertdialog" aria-modal="true" aria-labelledby="agent-oauth-login-required-title">
            <div className="config-dialog-heading">
              <div><AlertTriangle size={19} /><h2 id="agent-oauth-login-required-title">{t('agents.oauthLoginRequired.title')}</h2></div>
            </div>
            <p>{oauthLoginRequiredDescription}</p>
            <div className="config-dialog-actions single-action">
              <button type="button" className="primary-button" onClick={() => setOauthLoginRequiredAction(null)}>{t('agents.oauthLoginRequired.confirm')}</button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
