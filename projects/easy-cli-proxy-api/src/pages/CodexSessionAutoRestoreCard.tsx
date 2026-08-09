import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { LoaderCircle } from 'lucide-react';
import { useI18n } from '../i18n';

type RepairOnLaunchSetting = {
  enabled: boolean;
};

type StatusMessage = {
  text: string;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function CodexSessionAutoRestoreCard() {
  const { t } = useI18n();
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<StatusMessage | null>(null);

  useEffect(() => {
    let disposed = false;
    void invoke<RepairOnLaunchSetting>('get_codex_session_repair_on_launch')
      .then((result) => {
        if (!disposed) setEnabled(result.enabled);
      })
      .catch((error) => {
        if (!disposed) {
          setStatus({
            text: t('agents.sessions.settingLoadFailed', { error: errorMessage(error) }),
          });
        }
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [t]);

  const updateSetting = async (nextEnabled: boolean) => {
    setSaving(true);
    setStatus(null);
    try {
      const result = await invoke<RepairOnLaunchSetting>('set_codex_session_repair_on_launch', {
        request: { enabled: nextEnabled },
      });
      setEnabled(result.enabled);
    } catch (error) {
      setStatus({
        text: t('agents.sessions.settingFailed', { error: errorMessage(error) }),
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section
      className={`agent-core-setting-section codex-auto-restore-card ${enabled ? 'enabled' : ''}`}
      aria-busy={loading || saving}
    >
      <div className="agent-section-heading">
        <div>
          <strong>{t('agents.sessions.autoRepair')}</strong>
        </div>
        <label className="codex-auto-restore-toggle">
          {loading || saving ? <LoaderCircle size={14} className="spin" aria-hidden="true" /> : null}
          <strong>
            {loading
              ? t('agents.sessions.settingLoading')
              : enabled
                ? t('agents.sessions.settingOn')
                : t('agents.sessions.settingOff')}
          </strong>
          <span className="switch-control codex-auto-restore-switch">
            <input
              type="checkbox"
              role="switch"
              aria-label={t('agents.sessions.autoRepair')}
              checked={enabled}
              disabled={loading || saving}
              onChange={(event) => void updateSetting(event.currentTarget.checked)}
            />
            <span className="switch-track" />
          </span>
        </label>
      </div>
      {status ? (
        <small
          className="codex-auto-restore-message error"
          role="alert"
        >
          {status.text}
        </small>
      ) : null}
    </section>
  );
}
