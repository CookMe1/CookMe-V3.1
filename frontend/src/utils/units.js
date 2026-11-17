// Local unit conversion (no AI). convertAmount("2 cups", "metric") -> "480 ml"; convertAmount("200 g", "us") -> "7 oz"
const UNICODE = { '¼': 0.25, '½': 0.5, '¾': 0.75, '⅓': 1 / 3, '⅔': 2 / 3, '⅛': 0.125 };
const FRACS = [[0.125, '⅛'], [0.25, '¼'], [1 / 3, '⅓'], [0.5, '½'], [2 / 3, '⅔'], [0.75, '¾']];

const NUM = '(\\d+\\s+\\d+\\/\\d+|\\d+\\/\\d+|\\d+(?:\\.\\d+)?\\s*[¼½¾⅓⅔⅛]?|[¼½¾⅓⅔⅛])';
const RE = new RegExp('^\\s*' + NUM + '\\s*([a-zA-Z.]+(?:\\s+oz\\.?)?)(.*)$');

const TO_METRIC = {
  cup: ['ml', 240], cups: ['ml', 240], c: ['ml', 240],
  'fl oz': ['ml', 30], floz: ['ml', 30],
  pint: ['ml', 473], pints: ['ml', 473], pt: ['ml', 473],
  quart: ['ml', 946], quarts: ['ml', 946], qt: ['ml', 946],
  oz: ['g', 28.35], ounce: ['g', 28.35], ounces: ['g', 28.35],
  lb: ['g', 453.6], lbs: ['g', 453.6], pound: ['g', 453.6], pounds: ['g', 453.6],
};
const FROM_METRIC = {
  g: 'g', gram: 'g', grams: 'g', kg: 'kg', kilogram: 'kg', kilograms: 'kg',
  ml: 'ml', millilitre: 'ml', millilitres: 'ml', milliliter: 'ml', milliliters: 'ml',
  l: 'l', litre: 'l', litres: 'l', liter: 'l', liters: 'l', cl: 'cl', dl: 'dl',
};

export const parseNumber = (s) => {
  s = s.trim();
  let total = 0, rest = s;
  const u = rest.match(/[¼½¾⅓⅔⅛]$/);
  if (u) { total += UNICODE[u[0]]; rest = rest.slice(0, -1).trim(); }
  if (rest) {
    const mixed = rest.match(/^(\d+)\s+(\d+)\/(\d+)$/);
    const frac = rest.match(/^(\d+)\/(\d+)$/);
    if (mixed) total += +mixed[1] + +mixed[2] / +mixed[3];
    else if (frac) total += +frac[1] / +frac[2];
    else total += parseFloat(rest);
  }
  return total;
};

const nice = (n, unit) => {
  if (n >= 100) n = Math.round(n / 5) * 5;
  else if (n >= 10) n = Math.round(n);
  else n = Math.round(n * 10) / 10;
  return `${String(n).replace(/\.0$/, '')} ${unit}`;
};

const fraction = (n) => {
  const whole = Math.floor(n + 1e-9);
  const dec = n - whole;
  if (dec < 0.06) return `${whole || 0}`;
  if (dec > 0.94) return `${whole + 1}`;
  const f = FRACS.reduce((best, c) => (Math.abs(c[0] - dec) < Math.abs(best[0] - dec) ? c : best));
  return whole ? `${whole} ${f[1]}` : f[1];
};

export function convertAmount(amount, system) {
  if (!amount || !system || system === 'original') return amount;
  const text = String(amount);
  const m = text.match(RE);
  if (!m) return amount;
  const val = parseNumber(m[1]);
  let unit = m[2].toLowerCase().replace(/\.$/, '');
  let tail = m[3] || '';
  if (/^fl$/.test(unit) && /^\s+oz/i.test(tail)) { unit = 'fl oz'; tail = tail.replace(/^\s+oz\.?/i, ''); }
  if (isNaN(val) || val <= 0) return amount;

  if (system === 'metric' && TO_METRIC[unit]) {
    const [u, k] = TO_METRIC[unit];
    let out = val * k, outUnit = u;
    if (u === 'ml' && out >= 1000) { out /= 1000; outUnit = 'l'; }
    if (u === 'g' && out >= 1000) { out /= 1000; outUnit = 'kg'; }
    return nice(out, outUnit) + tail;
  }
  if (system === 'us' && FROM_METRIC[unit]) {
    const base = FROM_METRIC[unit];
    if (base === 'g' || base === 'kg') {
      const g = base === 'kg' ? val * 1000 : val;
      if (g >= 450) return `${nice(g / 453.6, 'lb')}${tail}`;
      return nice(g / 28.35, 'oz') + tail;
    }
    const ml = base === 'ml' ? val : base === 'cl' ? val * 10 : base === 'dl' ? val * 100 : val * 1000;
    if (ml < 15) return `${fraction(ml / 5)} tsp${tail}`;
    if (ml < 60) return `${fraction(ml / 15)} tbsp${tail}`;
    return `${fraction(ml / 240)} ${ml / 240 > 1.05 ? 'cups' : 'cup'}${tail}`;
  }
  return amount;
}
