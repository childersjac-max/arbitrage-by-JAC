/** Local calendar date key (YYYY-MM-DD) — never use toISOString() for "today". */
export function localDateKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function getTodayTomorrowKeys(): { todayKey: string; tomorrowKey: string } {
  const now = new Date();
  const todayKey = localDateKey(now);
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return { todayKey, tomorrowKey: localDateKey(tomorrow) };
}

export function isCommenceTodayOrTomorrow(commenceTime: string): boolean {
  const { todayKey, tomorrowKey } = getTodayTomorrowKeys();
  const key = localDateKey(new Date(commenceTime));
  return key === todayKey || key === tomorrowKey;
}
