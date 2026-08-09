import { useState, useMemo } from 'react';
import AdvisorGrid from './AdvisorGrid';
import MarkdownContent from './MarkdownContent';
import { getShortModelName } from '../utils/modelHelpers';
import CostReport from './CostReport';
import { copyToClipboard } from '../utils/clipboard';
import './DebateView.css';

const toStr = (v) => (typeof v === 'string' ? v : String(v || ''));

function findPersona(personas, id) {
  return personas.find((p) => p.id === id) || null;
}

function RoundSection({ roundIndex, roundData, personas, isLast, isRunning }) {
  const responses = roundData.responses || [];

  return (
    <div className="debate-view__round">
      <div className="debate-view__round-header">
        <span className="debate-view__round-label">Round {roundIndex + 1}</span>
        <div className="debate-view__round-divider" />
      </div>

      <div className="debate-view__round-cards">
        {responses.map((resp, idx) => {
          const persona = findPersona(personas, resp.persona_id);
          const hasError = !!resp.error;
          const hasWarning = !hasError && !!(resp.warning || resp.word_limit_exceeded);
          const displayName = persona?.name || resp.persona_name || resp.persona_id || 'Unknown';
          const displayEmoji = persona?.avatar_emoji || '🤖';
          const displayRole = persona?.role || '';
          const displayColor = persona?.color || '#64748b';

          return (
            <div
              key={resp.persona_id || idx}
              className="debate-view__response-card"
              style={{ '--persona-color': displayColor }}
            >
              <div className="debate-view__response-header">
                <span className="debate-view__response-emoji">
                  {displayEmoji}
                </span>
                <div className="debate-view__response-meta">
                  <span className="debate-view__response-name">
                    {displayName}
                  </span>
                  <span className="debate-view__response-role">
                    {displayRole}
                  </span>
                  {resp.model && (
                    <span className="debate-view__response-model">
                      {getShortModelName(resp.model)}
                    </span>
                  )}
                </div>
                {hasError && (
                  <span className="debate-view__response-error-badge">Error</span>
                )}
                {hasWarning && (
                  <span className="debate-view__response-warning-badge">Long</span>
                )}
              </div>
              <div className="debate-view__response-body">
                {hasError ? (
                  <div className="debate-view__response-error">
                    <span>⚠️</span>
                    <div className="debate-view__response-error-detail">
                      <span>{resp.error || 'This advisor failed to respond.'}</span>
                      {resp.model && (
                        <span className="debate-view__response-error-model">Model: {resp.model}</span>
                      )}
                    </div>
                  </div>
                ) : (
                  <>
                    {hasWarning && (
                      <div className="debate-view__response-warning">
                        <span>Word guidance exceeded; response kept.</span>
                        {resp.word_count && resp.word_limit && (
                          <span>{resp.word_count} / {resp.word_limit} words</span>
                        )}
                      </div>
                    )}
                    <MarkdownContent>{toStr(resp.content)}</MarkdownContent>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Consensus / round transition banner */}
      {isLast && isRunning ? (
        <div className="debate-view__next-round-banner">
          <span className="debate-view__next-round-dot" />
          Next round starting...
        </div>
      ) : responses.length > 0 && !isRunning ? (
        <div className="debate-view__consensus-banner">
          {responses.every((r) => !r.error)
            ? '✅ All advisors completed this round'
            : '⚠️ Some advisors encountered errors'}
        </div>
      ) : null}
    </div>
  );
}

export default function DebateView({
  personas = [],
  rounds = [],
  verdict = null,
  tiebreaker = null,
  currentRound = 1,
  maxRounds = 3,
  isRunning = false,
  phase = null,
  question = '',
  webSearch = null,
  error = null,
  costReport = null,
}) {
  const [verdictCopied, setVerdictCopied] = useState(false);

  const activePersonaId = useMemo(() => {
    if (!isRunning) return null;
    const currentRoundData = rounds[currentRound - 1];
    const responded = new Set((currentRoundData?.responses || []).map((resp) => resp.persona_id));
    const order = currentRoundData?.order?.length
      ? currentRoundData.order
      : personas.map((persona) => persona.id);
    return order.find((personaId) => !responded.has(personaId)) || null;
  }, [isRunning, rounds, currentRound, personas]);

  const handleCopyVerdict = async () => {
    if (!verdict?.content) return;
    const copied = await copyToClipboard(toStr(verdict.content));
    if (copied) {
      setVerdictCopied(true);
      setTimeout(() => setVerdictCopied(false), 2000);
    }
  };

  const hasResponses = rounds.some((r) => (r.responses || []).length > 0);
  const showDebateStarting = isRunning && !hasResponses;
  const currentRoundData = rounds[currentRound - 1] || rounds[rounds.length - 1] || null;
  const currentResponseCount = currentRoundData?.responses?.length || 0;
  const expectedResponseCount = currentRoundData?.order?.length || personas.length || 0;
  const livePhase = phase || (isRunning ? 'round' : 'complete');
  const liveTitle = (() => {
    if (livePhase === 'search') return 'Searching the web';
    if (livePhase === 'tiebreaker') return 'Running tiebreaker';
    if (livePhase === 'verdict') return 'Building verdict';
    if (livePhase === 'round_complete') return 'Preparing next step';
    if (livePhase === 'initializing') return 'Starting advisor debate';
    return `Round ${currentRound} in progress`;
  })();
  const liveDetail = expectedResponseCount > 0
    ? `${currentResponseCount}/${expectedResponseCount} advisors responded`
    : 'Preparing advisor panel';

  return (
    <div className="debate-view">
      {isRunning && (
        <div className="debate-view__live-status" role="status" aria-live="polite">
          <span className="debate-view__live-dot" aria-hidden="true" />
          <div className="debate-view__live-copy">
            <strong>{liveTitle}</strong>
            <span>{liveDetail}</span>
          </div>
        </div>
      )}

      {/* Advisor Grid — always shown at top */}
      <AdvisorGrid
        personas={personas}
        activePersonaId={activePersonaId}
        round={currentRound}
        maxRounds={maxRounds}
        isRunning={isRunning}
      />

      {/* Question echo */}
      {question && (
        <div className="debate-view__question">
          <div className="debate-view__question-top">
            <span className="debate-view__question-label">Debating</span>
            {webSearch && (
              <span className={`debate-view__search-badge ${showDebateStarting ? 'debate-view__search-badge--searching' : ''}`}>
                {showDebateStarting ? '🌐 Searching the web...' : '🌐 Web search included'}
              </span>
            )}
          </div>
          <p className="debate-view__question-text">{question}</p>
        </div>
      )}

      {/* Live indicator — before any responses arrive */}
      {showDebateStarting && (
        <div className="debate-view__starting">
          <span className="debate-view__starting-spinner" aria-hidden="true" />
          Debate starting...
        </div>
      )}

      <CostReport report={costReport} title="Advisor Debate Cost" />

      {/* Error banner — shown when the debate fails */}
      {error && (
        <div className="debate-view__error">
          <span className="debate-view__error-icon">⚠️</span>
          <div className="debate-view__error-content">
            <strong>Debate failed</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Round sections */}
      {rounds.map((roundData, idx) => {
        const hasContent = (roundData.responses || []).length > 0;
        if (!hasContent) return null;
        return (
          <RoundSection
            key={idx}
            roundIndex={idx}
            roundData={roundData}
            personas={personas}
            isLast={idx === rounds.length - 1}
            isRunning={isRunning}
          />
        );
      })}

      {/* Tiebreaker section */}
      {tiebreaker && tiebreaker.content && (
        <div className="debate-view__tiebreaker">
          <div className="debate-view__tiebreaker-header">
            <span className="debate-view__tiebreaker-icon">🔀</span>
            <span className="debate-view__tiebreaker-title">Tiebreaker</span>
            {tiebreaker.model && (
              <span className="debate-view__tiebreaker-model">{tiebreaker.model}</span>
            )}
          </div>
          <MarkdownContent>{toStr(tiebreaker.content)}</MarkdownContent>
        </div>
      )}

      {/* Verdict section */}
      {verdict && verdict.content && (
        <div className={`debate-view__verdict ${verdict.error ? 'debate-view__verdict--error' : ''}`}>
          <div className="debate-view__verdict-header">
            <div className="debate-view__verdict-title-row">
              <span className="debate-view__verdict-icon">
                {verdict.error ? '⚠️' : '📋'}
              </span>
              <span className="debate-view__verdict-title">
                {verdict.error ? 'Verdict Error' : 'Verdict'}
              </span>
              {verdict.model && (
                <span className="debate-view__verdict-model">{verdict.model}</span>
              )}
            </div>
            {!verdict.error && (
              <button
                className={`debate-view__copy-btn ${verdictCopied ? 'debate-view__copy-btn--copied' : ''}`}
                onClick={handleCopyVerdict}
                type="button"
                title="Copy verdict to clipboard"
              >
                {verdictCopied ? (
                  <>
                    <span>✓</span>
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <span>📋</span>
                    <span>Copy</span>
                  </>
                )}
              </button>
            )}
          </div>
          <MarkdownContent className="debate-view__verdict-body">
            {toStr(verdict.content)}
          </MarkdownContent>
        </div>
      )}
    </div>
  );
}
