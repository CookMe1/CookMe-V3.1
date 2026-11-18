// Cooking times are stored as text ("15 min", "1h 30m", "2 hrs"). Show prep + cook as one total, "~" when estimated.
export function toMinutes(text) {
  if (text === undefined || text === null || text === '') return 0;
  const s = String(text).toLowerCase();
  let total = 0;
  const h = s.match(/(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hour|hours)\b/);
  const m = s.match(/(\d+(?:\.\d+)?)\s*(?:m|min|mins|minute|minutes)\b/);
  if (h) total += parseFloat(h[1]) * 60;
  if (m) total += parseFloat(m[1]);
  if (!h && !m) { const n = parseFloat(s); if (!isNaN(n)) total = n; }
  return Math.round(total);
}

export function formatMinutes(mins) {
  if (!mins || mins <= 0) return '';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h && m) return `${h}h ${m}m`;
  return h ? `${h}h` : `${m} min`;
}

export function totalTimeLabel(recipe) {
  if (!recipe) return '—';
  const prep = toMinutes(recipe.prep_time ?? recipe.prepTime);
  const cook = toMinutes(recipe.cook_time ?? recipe.cookTime);
  const total = prep + cook;
  if (!total) return '—';
  return `${recipe.time_estimated ? '~' : ''}${formatMinutes(total)}`;
}
