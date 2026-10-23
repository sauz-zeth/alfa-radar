export function formatMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  if (value >= 1_000_000_000) {
    const billions = value / 1_000_000_000;
    return `${billions >= 10 ? Math.round(billions) : billions.toFixed(1).replace(".", ",")} млрд ₽`;
  }
  if (value >= 1_000_000) return `${Math.round(value / 1_000_000)} млн ₽`;
  if (value >= 1_000) return `${Math.round(value / 1_000)} тыс ₽`;
  return `${Math.round(value)} ₽`;
}

export function formatShare(share: number): string {
  return `${Math.round(share * 100)}%`;
}

export function formatWeight(weight: number): string {
  return `${Math.round(weight * 100)}%`;
}
