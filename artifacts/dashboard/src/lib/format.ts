export function formatPercent(val: number | undefined | null): string {
  if (val == null) return "-";
  return (val * 100).toFixed(1) + "%";
}

export function formatPct(val: number | undefined | null): string {
  if (val == null) return "-";
  return val.toFixed(2) + "%";
}

export function formatOdds(odds: number | undefined | null): string {
  if (odds == null) return "-";
  return odds > 0 ? `+${odds}` : `${odds}`;
}

export function formatMoney(val: number | undefined | null): string {
  if (val == null) return "-";
  return "$" + val.toFixed(2);
}

export function formatTimeAgo(dateString: string | undefined | null): string {
  if (!dateString) return "Unknown";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.round(diffMs / 60000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} min ago`;
  const diffHours = Math.floor(diffMins / 60);
  return `${diffHours}h ${diffMins % 60}m ago`;
}
