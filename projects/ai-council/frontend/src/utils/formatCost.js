export function formatUsd(value, unknown = false) {
  if (unknown || typeof value !== 'number' || Number.isNaN(value)) return 'Unknown';
  if (value === 0) return '$0.00';
  if (value < 0.000001) return '<$0.000001';
  if (value < 0.01) return `$${value.toFixed(6)}`;
  return `$${value.toFixed(4)}`;
}

export function formatSidebarCost(totalCost, costStatus) {
  const amount = formatUsd(totalCost);
  if (costStatus === 'estimated') return `~${amount}`;
  if (costStatus === 'partial') return `${amount}+`;
  return amount;
}

export function sidebarCostTooltip(totalCost, costStatus, totalCalls) {
  const parts = ['Conversation total'];
  if (typeof totalCalls === 'number' && totalCalls > 0) {
    parts.push(`${totalCalls} API call${totalCalls === 1 ? '' : 's'}`);
  }
  if (costStatus === 'partial') {
    parts.push('some pricing unavailable');
  } else if (costStatus === 'estimated') {
    parts.push('estimated pricing');
  } else if (costStatus === 'free') {
    parts.push('known free models');
  }
  if (typeof totalCost === 'number') {
    parts.push(formatUsd(totalCost));
  }
  return parts.join(' · ');
}
