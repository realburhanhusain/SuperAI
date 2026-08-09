import './CostReport.css';
import { formatUsd } from '../utils/formatCost';

const numberFormatter = new Intl.NumberFormat(undefined);

function formatTokens(value) {
  if (typeof value !== 'number') return '0';
  return numberFormatter.format(value);
}

function formatTokenBreakdown(item) {
  return `${formatTokens(item.input_tokens)} in / ${formatTokens(item.output_tokens)} out`;
}

function rowCostLabel(row) {
  return formatUsd(row.total_cost, row.known_cost_calls === 0 && row.unknown_cost_calls > 0);
}

function rowStatus(row) {
  if (row.free_calls === row.calls) return 'Free';
  if (row.unknown_cost_calls > 0 && row.known_cost_calls === 0) return 'Usage only';
  if (row.estimated_calls > 0) return 'Estimated';
  return 'Known';
}

export default function CostReport({ report, title = 'Run Cost' }) {
  if (!report || !Array.isArray(report.by_model) || report.by_model.length === 0) {
    return null;
  }

  const unknownTotal = report.known_cost_calls === 0 && report.unknown_cost_calls > 0;
  const statusText = report.has_unknown_costs
    ? 'Some pricing unavailable'
    : report.has_estimates
      ? 'Estimated'
      : 'Known';

  return (
    <section className="cost-report" aria-label={title}>
      <div className="cost-report__summary">
        <div>
          <div className="cost-report__eyebrow">{title}</div>
          <div className="cost-report__total">{formatUsd(report.total_cost, unknownTotal)}</div>
        </div>
        <div className="cost-report__metrics" aria-label="Cost metrics">
          <span title="Provider-reported total tokens when available, otherwise input plus output tokens.">
            {formatTokens(report.total_tokens)} total tokens
          </span>
          <span title="Input tokens">{formatTokens(report.input_tokens)} in</span>
          <span title="Output tokens">{formatTokens(report.output_tokens)} out</span>
          <span>{report.total_calls || 0} calls</span>
          <span className={`cost-report__status ${report.has_unknown_costs ? 'unknown' : report.has_estimates ? 'estimated' : 'known'}`}>
            {statusText}
          </span>
        </div>
      </div>

      <details className="cost-report__details">
        <summary>Model breakdown</summary>
        <div className="cost-report__table" role="table" aria-label="Cost by model">
          <div className="cost-report__row cost-report__row--head" role="row">
            <span role="columnheader">Model</span>
            <span role="columnheader">Calls</span>
            <span role="columnheader">Tokens</span>
            <span role="columnheader">Cost</span>
            <span role="columnheader">Status</span>
          </div>
          {report.by_model.map((row) => (
            <div className="cost-report__row" role="row" key={row.name}>
              <span className="cost-report__model" role="cell" title={row.name}>{row.name}</span>
              <span role="cell">{row.calls || 0}</span>
              <span className="cost-report__tokens" role="cell" title={formatTokenBreakdown(row)}>
                <span>{formatTokens(row.total_tokens)}</span>
                <small>{formatTokenBreakdown(row)}</small>
              </span>
              <span role="cell">{rowCostLabel(row)}</span>
              <span role="cell" className={`cost-report__source ${rowStatus(row).toLowerCase().replace(' ', '-')}`}>
                {rowStatus(row)}
              </span>
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}
