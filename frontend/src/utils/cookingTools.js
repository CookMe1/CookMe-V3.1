// Cooking helpers: timers found in recipe steps, protein doneness choices, and air-fryer conversion.
// Pure functions (no React) so they are easy to test. Air-fryer numbers are rules of thumb, shown as "approx".

// ── Durations ────────────────────────────────────────────────────────────────
const WORDS = { a: 1, an: 1, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, fifteen: 15, twenty: 20, thirty: 30, forty: 40, 'forty-five': 45, fifty: 50, sixty: 60 };
const NUM = `\\d+(?:[.,]\\d+)?|${Object.keys(WORDS).sort((a, b) => b.length - a.length).join('|')}`;
const UNIT_SECONDS = (u) => (/^h/i.test(u) ? 3600 : /^m/i.test(u) ? 60 : 1);
const toNum = (s) => (WORDS[s.toLowerCase()] !== undefined ? WORDS[s.toLowerCase()] : parseFloat(s.replace(',', '.')));

export function fmtLabel(seconds) {
  if (seconds >= 3600 && seconds % 60 === 0) {
    const h = Math.floor(seconds / 3600), m = Math.round((seconds % 3600) / 60);
    return m ? `${h} h ${m} min` : `${h} h`;
  }
  if (seconds >= 60) { const m = Math.floor(seconds / 60), s = seconds % 60; return s ? `${m} min ${s} s` : `${m} min`; }
  return `${seconds} s`;
}
export function fmtClock(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return (h ? `${h}:` : '') + `${String(m).padStart(h ? 2 : 1, '0')}:${String(sec).padStart(2, '0')}`;
}

// All times in a step: "simmer 10-12 minutes" -> {seconds: 600, label: '10–12 min'}; "4 minutes per side" -> perSide.
export function findDurations(text) {
  const out = [];
  const t = String(text || '');
  if (/\bhalf an hour\b/i.test(t)) out.push({ seconds: 1800, label: '30 min', perSide: false });
  const re = new RegExp(`(${NUM})(?:\\s*(?:-|–|—|to)\\s*(${NUM}))?\\s*(hours?|hrs?|h|minutes?|mins?|seconds?|secs?)\\b(\\s*(?:per|each|a)\\s*side|\\s*on each side)?`, 'gi');
  let m;
  while ((m = re.exec(t))) {
    const lo = toNum(m[1]); const hi = m[2] ? toNum(m[2]) : null;
    if (!(lo > 0)) continue;
    if (/^(a|an)$/i.test(m[1]) && !/^(minutes?|mins?|hours?|hrs?|seconds?|secs?)$/i.test(m[3])) continue;
    const unit = UNIT_SECONDS(m[3]);
    const seconds = Math.round(lo * unit);
    const label = hi ? `${lo}–${hi} ${/^h/i.test(m[3]) ? 'h' : /^m/i.test(m[3]) ? 'min' : 's'}` : fmtLabel(seconds);
    if (seconds >= 5 && seconds <= 12 * 3600) out.push({ seconds, label, perSide: !!m[4] });
  }
  return out;
}

// ── Temperatures ─────────────────────────────────────────────────────────────
const GAS = { 1: 140, 2: 150, 3: 160, 4: 180, 5: 190, 6: 200, 7: 220, 8: 230, 9: 240 };
const toF = (c) => Math.round((c * 9) / 5 + 32);
const round5 = (n) => Math.round(n / 5) * 5;
export const showTemp = (c) => `${c}°C / ${toF(c)}°F`;

// First oven/air temperature in a step, in °C (or null).
export function findTempC(text) {
  const t = String(text || '');
  const c = t.match(/(\d{2,3})\s*°?\s*C\b(?![a-z])/);
  if (c) return parseInt(c[1], 10);
  const f = t.match(/(\d{3})\s*°?\s*F\b(?![a-z])/);
  if (f) return round5(((parseInt(f[1], 10) - 32) * 5) / 9);
  const g = t.match(/gas(?: mark)?\s*(\d)/i);
  if (g && GAS[g[1]]) return GAS[g[1]];
  return null;
}

// ── Proteins: what is it, how big, how do you like it, how are you cooking it ─────────────────────────
// Rules of thumb for timing (thickness/weight drive it; always check with a thermometer). Times assume the default heat for that method.
const min = (m) => Math.round(m * 60);
const SAFETY_RARE = 'Official food-safety guidance is 63°C / 145°F for whole cuts of beef, lamb and pork (then rest 3 minutes). Cooking rarer is your choice and isn’t recommended for pregnant women, young children, older people or anyone with a weakened immune system.';
const SAFETY_FISH = 'Cooking fish below 63°C / 145°F isn’t recommended for pregnant women, young children, older people or anyone with a weakened immune system.';

export const METHODS = {
  pan: { label: 'Pan / hob', icon: '🍳' },
  oven: { label: 'Oven', icon: '♨️' },
  grill: { label: 'Grill / BBQ', icon: '🔥' },
  airfryer: { label: 'Air fryer', icon: '🍟' },
};
const BEEF = [
  { id: 'rare', label: 'Rare', tempC: 52, factor: 0.6 },
  { id: 'medium-rare', label: 'Medium rare', tempC: 57, factor: 0.8 },
  { id: 'medium', label: 'Medium', tempC: 63, factor: 1 },
  { id: 'medium-well', label: 'Medium well', tempC: 68, factor: 1.2 },
  { id: 'well', label: 'Well done', tempC: 71, factor: 1.4 },
];
const LAMB = [
  { id: 'medium-rare', label: 'Pink', tempC: 57, factor: 0.8 },
  { id: 'medium', label: 'Medium', tempC: 63, factor: 1 },
  { id: 'well', label: 'Well done', tempC: 71, factor: 1.3 },
];
const PORK = [
  { id: 'medium', label: 'Medium (slightly blush)', tempC: 63, factor: 1 },
  { id: 'well', label: 'Well done', tempC: 71, factor: 1.25 },
];
const SALMON = [
  { id: 'medium-rare', label: 'Soft / medium rare', tempC: 50, factor: 0.8 },
  { id: 'medium', label: 'Medium', tempC: 54, factor: 1 },
  { id: 'well', label: 'Well done (flaky)', tempC: 63, factor: 1.25 },
];
const sizesCm = (list) => list.map(([cm, label]) => ({ id: String(cm), label, cm }));
const pick = (arr, i) => arr[Math.min(i, arr.length - 1)];

// A stage = one timed bit of cooking. perSide stages become "side 1 / side 2" timers.
const stage = (label, minutes, extra = {}) => ({ label, seconds: min(Math.max(0.5, minutes)), ...extra });

// Steak-like cuts (beef steak, lamb chops, pork chops): time follows thickness, doneness and method.
function chopPlan({ cm, f, method, pork }) {
  const m = pork ? 1.15 : 1;
  const side = (1 + cm) * f * m;
  if (method === 'pan' && cm >= 4) {
    return { tempC: null, heat: 'Hot pan, medium-high heat, then finish in the oven at 200°C / 400°F',
      stages: [stage('Sear side 1', 2, { perSide: true }), stage('Finish in the oven (200°C / 400°F)', Math.max(2, (cm - 2.5) * 5 * f * m))],
      notes: ['Thick cuts: sear both sides first, then finish in the oven so the middle cooks without burning the outside.'] };
  }
  if (method === 'pan') return { heat: 'Very hot pan, medium-high heat. Pat the meat dry, add a little oil.', stages: [stage('Cook side 1', side, { perSide: true })], notes: ['Add butter, garlic and herbs for the last minute if you like.'] };
  if (method === 'grill') return { tempC: 230, heat: 'Hot grill / BBQ (about 230°C / 450°F)', stages: [stage('Grill side 1', side, { perSide: true })], notes: ['Don’t press the meat down; flip once.'] };
  if (method === 'airfryer') return { tempC: 200, heat: 'Air fryer 200°C / 400°F (preheat 3 min)', stages: [stage('Air fry, turn halfway', side * 2 * 1.15, { halfway: true })], notes: ['Pat dry and lightly oil. Single layer only.'] };
  return { tempC: 200, heat: 'Oven 200°C / 400°F (preheat; a hot tray helps)', stages: [stage('Roast', side * 2 * 1.5)], notes: ['Sear in a hot pan for 1 minute per side first for a better crust.'] };
}

// Roasting joints: minutes per 450 g (1 lb) + extra, by doneness.
function jointPlan({ kg, doneness, method, kind }) {
  const tbl = {
    beef: { rare: [20, 20], medium: [25, 25], well: [30, 30], 'medium-rare': [20, 20], 'medium-well': [28, 28] },
    lamb: { 'medium-rare': [20, 20], medium: [25, 25], well: [30, 30] },
    pork: { medium: [35, 35], well: [35, 35] },
  }[kind];
  const [per, extra] = tbl[doneness.id] || [25, 25];
  const oven = (kg / 0.45) * per + extra;
  if (method === 'airfryer') {
    return { tempC: 180, heat: 'Air fryer 180°C / 355°F (only for joints that fit with room around them)', stages: [stage('Roast, turn halfway', oven * 0.8, { halfway: true })], rest: 15, notes: ['Check the temperature early; air fryers vary.'] };
  }
  return { tempC: kind === 'pork' ? 180 : 180, heat: 'Oven 180°C / 350°F (fan 160°C)', stages: [stage('Roast', oven)], rest: 20, notes: ['Start with a hot pan sear or 15 min at 220°C for colour, optional.'] };
}

export const PROTEIN_TYPES = [
  { id: 'burger', name: 'Burgers', icon: '🍔', words: /\b(burgers?|patty|patties)\b|\b(?:beef|pork|lamb|turkey) mince\b/i,
    sizes: sizesCm([[1.5, 'Thin (about 1.5 cm, ~115 g)'], [2, 'Thick (about 2 cm, ~170 g)']]), defaultSize: '2', methods: ['pan', 'grill', 'oven', 'airfryer'],
    fixedInternal: 71, rest: 3, note: 'Burgers must be cooked through (no pink): 71°C / 160°F in the centre.',
    plan: ({ size, method }) => { const i = size.cm <= 1.5 ? 0 : 1; return ({
      pan: { heat: 'Medium-high heat', stages: [stage('Cook side 1', pick([4, 5.5], i), { perSide: true })] },
      grill: { tempC: 220, heat: 'Medium-hot grill / BBQ', stages: [stage('Grill side 1', pick([4, 5.5], i), { perSide: true })] },
      oven: { tempC: 200, heat: 'Oven 200°C / 400°F', stages: [stage('Bake, turn halfway', pick([14, 18], i), { halfway: true })] },
      airfryer: { tempC: 180, heat: 'Air fryer 180°C / 355°F', stages: [stage('Air fry, turn halfway', pick([9, 12], i), { halfway: true })] } }[method]); } },
  { id: 'sausage', name: 'Sausages', icon: '🌭', words: /\bsausages?\b/i,
    sizes: [{ id: 'thin', label: 'Thin / chipolata' }, { id: 'thick', label: 'Standard / thick' }], defaultSize: 'thick', methods: ['pan', 'grill', 'oven', 'airfryer'],
    fixedInternal: 71, rest: 2, note: 'Sausages must be cooked through (no pink): 71°C / 160°F.',
    plan: ({ size, method }) => { const i = size.id === 'thin' ? 0 : 1; return ({
      pan: { heat: 'Medium-low heat, turn often', stages: [stage('Cook, turning often', pick([10, 15], i))] },
      grill: { tempC: 200, heat: 'Medium grill, turn often', stages: [stage('Grill, turning often', pick([10, 14], i))] },
      oven: { tempC: 200, heat: 'Oven 200°C / 400°F', stages: [stage('Bake, turn halfway', pick([20, 28], i), { halfway: true })] },
      airfryer: { tempC: 180, heat: 'Air fryer 180°C / 355°F', stages: [stage('Air fry, shake halfway', pick([10, 14], i), { halfway: true })] } }[method]); } },
  { id: 'joint-beef', name: 'Roast beef joint', icon: '🥩', words: /\b(roast beef|beef (?:joint|roast)|topside|silverside|rib of beef|sirloin joint)\b/i,
    sizes: sizesCm([[1, 'About 1 kg'], [1.5, 'About 1.5 kg'], [2, 'About 2 kg']]).map((x) => ({ ...x, kg: x.cm })), defaultSize: '1.5', methods: ['oven', 'airfryer'],
    doneness: [BEEF[0], BEEF[2], BEEF[4]], defaultDoneness: 'medium', safety: SAFETY_RARE, rest: 20,
    plan: ({ size, doneness, method }) => jointPlan({ kg: size.kg, doneness, method, kind: 'beef' }) },
  { id: 'joint-lamb', name: 'Roast lamb joint', icon: '🍖', words: /\b(leg of lamb|shoulder of lamb|rack of lamb|lamb (?:joint|roast))\b/i,
    sizes: sizesCm([[1, 'About 1 kg'], [1.5, 'About 1.5 kg'], [2, 'About 2 kg']]).map((x) => ({ ...x, kg: x.cm })), defaultSize: '1.5', methods: ['oven', 'airfryer'],
    doneness: LAMB, defaultDoneness: 'medium', safety: SAFETY_RARE, rest: 20,
    plan: ({ size, doneness, method }) => jointPlan({ kg: size.kg, doneness, method, kind: 'lamb' }) },
  { id: 'joint-pork', name: 'Roast pork joint', icon: '🍖', words: /\b(pork (?:joint|roast|loin roast)|roast pork|pork leg)\b/i,
    sizes: sizesCm([[1, 'About 1 kg'], [1.5, 'About 1.5 kg'], [2, 'About 2 kg']]).map((x) => ({ ...x, kg: x.cm })), defaultSize: '1.5', methods: ['oven', 'airfryer'],
    doneness: [{ id: 'well', label: 'Cooked through', tempC: 71, factor: 1 }], defaultDoneness: 'well', rest: 20,
    plan: ({ size, doneness, method }) => jointPlan({ kg: size.kg, doneness, method, kind: 'pork' }) },
  { id: 'steak', name: 'Beef steak', icon: '🥩', words: /\b(steaks?|sirloin|ribeye|rib-eye|fillet steak|filet|tenderloin|rump|flank|skirt|t-bone|porterhouse)\b/i,
    sizes: sizesCm([[2, 'Thin (about 2 cm / ¾")'], [3, 'Standard (about 3 cm / 1¼")'], [4, 'Thick (about 4 cm / 1½")'], [5, 'Very thick (5 cm / 2")']]), defaultSize: '3',
    methods: ['pan', 'grill', 'airfryer', 'oven'], doneness: BEEF, defaultDoneness: 'medium', safety: SAFETY_RARE, rest: 5,
    plan: ({ size, doneness, method }) => chopPlan({ cm: size.cm, f: doneness.factor, method }) },
  { id: 'lamb-chop', name: 'Lamb chops / steaks', icon: '🍖', words: /\blamb (?:chops?|cutlets?|steaks?|rump|loin)\b|\blamb\b/i,
    sizes: sizesCm([[2, 'Thin (about 2 cm)'], [3, 'Standard (about 3 cm)'], [4, 'Thick (about 4 cm)']]), defaultSize: '3', methods: ['pan', 'grill', 'airfryer', 'oven'],
    doneness: LAMB, defaultDoneness: 'medium', safety: SAFETY_RARE, rest: 5,
    plan: ({ size, doneness, method }) => chopPlan({ cm: size.cm, f: doneness.factor, method }) },
  { id: 'pork-chop', name: 'Pork chops / steaks', icon: '🥓', words: /\bpork (?:chops?|loin|tenderloin|fillet|steaks?|cutlets?)\b|\b(?:chops?|gammon)\b/i,
    sizes: sizesCm([[2, 'Thin (about 2 cm)'], [3, 'Standard (about 3 cm)'], [4, 'Thick (about 4 cm)']]), defaultSize: '3', methods: ['pan', 'grill', 'airfryer', 'oven'],
    doneness: PORK, defaultDoneness: 'medium', rest: 3,
    plan: ({ size, doneness, method }) => chopPlan({ cm: size.cm, f: doneness.factor, method, pork: true }) },
  { id: 'chicken-thigh', name: 'Chicken thighs / drumsticks', icon: '🍗', words: /\bchicken (?:thighs?|drumsticks?|legs?)\b|\b(?:thighs?|drumsticks?)\b/i,
    sizes: [{ id: 'boneless', label: 'Boneless thighs' }, { id: 'bone', label: 'Bone-in thighs / drumsticks' }], defaultSize: 'bone', methods: ['oven', 'pan', 'grill', 'airfryer'],
    fixedInternal: 74, rest: 5, note: 'Cook to at least 74°C / 165°F; thighs are nicest at 80°C+.',
    plan: ({ size, method }) => { const i = size.id === 'boneless' ? 0 : 1; return ({
      pan: { heat: i ? 'Medium heat: brown, then cover on low' : 'Medium heat', stages: i ? [stage('Brown side 1', 4, { perSide: true }), stage('Cover and cook on low', 15)] : [stage('Cook side 1', 6, { perSide: true })] },
      oven: { tempC: 200, heat: 'Oven 200°C / 400°F', stages: [stage('Roast', pick([25, 40], i))] },
      grill: { tempC: 190, heat: 'Medium grill / BBQ, lid down', stages: [stage('Grill side 1', pick([6, 12], i), { perSide: true })] },
      airfryer: { tempC: 190, heat: 'Air fryer 190°C / 375°F', stages: [stage('Air fry, turn halfway', pick([16, 25], i), { halfway: true })] } }[method]); } },
  { id: 'whole-chicken', name: 'Whole chicken', icon: '🍗', words: /\b(?:whole chicken|roast chicken|chicken roast)\b/i,
    sizes: sizesCm([[1.2, 'About 1.2 kg'], [1.5, 'About 1.5 kg'], [1.8, 'About 1.8 kg'], [2.2, 'About 2.2 kg']]).map((x) => ({ ...x, kg: x.cm })), defaultSize: '1.5', methods: ['oven', 'airfryer'],
    fixedInternal: 74, rest: 15, note: 'Cook until 74°C / 165°F in the thickest part of the thigh and the juices run clear.',
    plan: ({ size, method }) => method === 'airfryer'
      ? { tempC: 180, heat: 'Air fryer 180°C / 355°F (only fits a large air fryer)', stages: [stage('Roast breast-side down, turn after half', size.kg * 25 + 18, { halfway: true })] }
      : { tempC: 190, heat: 'Oven 190°C / 375°F (fan 170°C)', stages: [stage('Roast', (size.kg / 0.45) * 20 + 20)] } },
  { id: 'chicken-breast', name: 'Chicken breast', icon: '🍗', words: /\bchicken (?:breasts?|fillets?|cutlets?|schnitzel)\b|\bchicken\b/i,
    sizes: [{ id: 's', label: 'Small (about 150 g)' }, { id: 'm', label: 'Medium (about 200 g)' }, { id: 'l', label: 'Large / thick (300 g+)' }], defaultSize: 'm', methods: ['pan', 'oven', 'grill', 'airfryer'],
    fixedInternal: 74, rest: 5, note: 'Chicken must be cooked through: 74°C / 165°F in the thickest part, no pink, clear juices.',
    plan: ({ size, method }) => { const i = { s: 0, m: 1, l: 2 }[size.id]; return ({
      pan: { heat: 'Medium heat (not too hot, so the outside doesn’t burn)', stages: [stage('Cook side 1', pick([5, 6.5, 8], i), { perSide: true })], notes: ['Large breasts: butterfly them or cover for the last 3 minutes.'] },
      oven: { tempC: 200, heat: 'Oven 200°C / 400°F', stages: [stage('Roast', pick([18, 22, 28], i))] },
      grill: { tempC: 200, heat: 'Medium-hot grill / BBQ', stages: [stage('Grill side 1', pick([5, 6, 8], i), { perSide: true })] },
      airfryer: { tempC: 190, heat: 'Air fryer 190°C / 375°F (preheat 3 min)', stages: [stage('Air fry, turn halfway', pick([12, 15, 19], i), { halfway: true })] } }[method]); } },
  { id: 'salmon', name: 'Salmon fillet', icon: '🐟', words: /\b(salmon|trout|arctic char)\b/i,
    sizes: sizesCm([[1.5, 'Thin (about 1.5 cm)'], [2.5, 'Standard (about 2.5 cm)'], [3.5, 'Thick (about 3.5 cm)']]), defaultSize: '2.5', methods: ['pan', 'oven', 'airfryer', 'grill'],
    doneness: SALMON, defaultDoneness: 'medium', safety: SAFETY_FISH, rest: 2,
    plan: ({ size, doneness, method }) => { const i = size.cm <= 1.5 ? 0 : size.cm <= 2.5 ? 1 : 2; const f = doneness.factor; return ({
      pan: { heat: 'Medium-high heat, skin-side down first', stages: [stage('Skin side down', pick([3, 4, 5], i) * f), stage('Flip', pick([1, 2, 3], i) * f)] },
      oven: { tempC: 200, heat: 'Oven 200°C / 400°F', stages: [stage('Bake', pick([8, 12, 16], i) * f)] },
      airfryer: { tempC: 200, heat: 'Air fryer 200°C / 400°F', stages: [stage('Air fry (no turning needed)', pick([6, 9, 12], i) * f)] },
      grill: { tempC: 220, heat: 'Medium-hot grill, skin-side down', stages: [stage('Grill', pick([4, 6, 8], i) * f)] } }[method]); } },
  { id: 'white-fish', name: 'White fish fillet', icon: '🐟', words: /\b(cod|haddock|sea bass|seabass|bream|halibut|plaice|sole|snapper|tilapia|pollock|white fish)\b/i,
    sizes: [{ id: 'thin', label: 'Thin (under 2 cm)' }, { id: 'medium', label: 'Standard (2–3 cm)' }, { id: 'thick', label: 'Thick (3 cm+)' }], defaultSize: 'medium', methods: ['pan', 'oven', 'airfryer', 'grill'],
    fixedInternal: 63, rest: 0, note: 'Fish is done at 63°C / 145°F, when it turns opaque and flakes easily.',
    plan: ({ size, method }) => { const i = { thin: 0, medium: 1, thick: 2 }[size.id]; return ({
      pan: { heat: 'Medium-high heat', stages: [stage('Cook side 1', pick([2, 3, 4], i), { perSide: true })] },
      oven: { tempC: 200, heat: 'Oven 200°C / 400°F', stages: [stage('Bake', pick([8, 11, 15], i))] },
      airfryer: { tempC: 190, heat: 'Air fryer 190°C / 375°F', stages: [stage('Air fry (no turning needed)', pick([6, 8, 11], i))] },
      grill: { tempC: 220, heat: 'Medium-hot grill', stages: [stage('Grill side 1', pick([3, 4, 5], i), { perSide: true })] } }[method]); } },
];
export const proteinTypeById = (id) => PROTEIN_TYPES.find((t) => t.id === id) || null;

// Which protein a recipe is about (title first, then ingredients). Order matters: more specific kinds come first.
const NOT_WHOLE_CUT = /\b(pulled|belly|shoulder|stew|casserole|curry|soup|stock|broth|minced?|ground|sausage|burger)\b/i;
// Slow-cooked, minced, sauced or pastry dishes: the "how do you like it cooked" plan does not apply.
const NOT_A_SIMPLE_CUT = /\b(shanks?|braise[ds]?|braising|stews?|casseroles?|curr(?:y|ies)|tagines?|ragu|ragout|pies?|pasties|soups?|broth|stock|mince[d]?|meatballs?|kebabs?|koftas?|hotpot|goulash|stroganoff|bolognese|lasagn[ae]|pulled|slow[- ]cook(?:er|ed)?|stir[- ]fr(?:y|ied)|salad|sandwich(?:es)?|wraps?|tacos?|fried rice|noodles?|risotto|paella)\b/i;

export function detectProteinType(recipe) {
  const title = String(recipe?.title || '');
  if (NOT_A_SIMPLE_CUT.test(title)) return null;
  const ings = (recipe?.ingredients || []).map((i) => (typeof i === 'string' ? i : i.item || i.name || '')).join(' ; ');
  for (const [text, strict] of [[title, true], [ings, false]]) {
    for (const t of PROTEIN_TYPES) {
      if (!t.words.test(text)) continue;
      if (strict && /pork/.test(t.id) && NOT_WHOLE_CUT.test(title)) continue;
      return t;
    }
  }
  return null;
}

// The full plan for the user's answers. Returns {tempC, heat, stages, internalC, rest, notes, safety, summary}.
export function proteinPlan(type, { sizeId, doneId, method }) {
  if (!type) return null;
  const size = type.sizes.find((x) => x.id === sizeId) || type.sizes.find((x) => x.id === type.defaultSize) || type.sizes[0];
  const doneness = type.doneness ? type.doneness.find((d) => d.id === doneId) || type.doneness.find((d) => d.id === type.defaultDoneness) : null;
  const m = type.methods.includes(method) ? method : type.methods[0];
  const p = type.plan({ size, doneness, method: m });
  const internalC = doneness ? doneness.tempC : type.fixedInternal;
  const rest = p.rest !== undefined ? p.rest : type.rest;
  const notes = [...(p.notes || []), ...(type.note ? [type.note] : [])];
  const safety = doneness && doneness.tempC < 63 && type.safety ? type.safety : (doneness && type.id === 'salmon' && doneness.tempC < 63 ? type.safety : null);
  const stages = p.stages.map((s) => ({ ...s, seconds: s.seconds < 600 ? Math.max(30, Math.round(s.seconds / 15) * 15) : Math.round(s.seconds / 60) * 60 }));
  return { method: m, size, doneness, tempC: p.tempC || null, heat: p.heat, stages, internalC, rest, notes, safety };
}
export const describeStage = (s) => `${s.perSide ? s.label.replace(/ side 1/i, '') : s.label}: ${fmtLabel(s.seconds)}${s.perSide ? ' per side' : ''}`;

// Does this recipe step cook the protein (so the plan's timers belong to it)?
const PROTEIN_COOK = /\b(sear|seared|grill|grilled|griddle|roast|roasted|broil|barbecue|bbq|pan[- ]?fry|fry|fried|bake|baked|cook|cooked)\b|\b(per|each|a) side\b/i;
const NOT_PROTEIN_STEP = /\b(simmer|boil|stock|sauce|onions?|garlic|vegetables?|potato(?:es)?|rice|pasta|soften|mushrooms?)\b/i;
export function stepCooksProtein(step, type) {
  if (!type) return false;
  const t = String(step || '');
  if (!findDurations(t).length) return false;
  if (type.words.test(t)) return PROTEIN_COOK.test(t);
  return /\b(per|each|a) side\b|\bsear|\bgrill|\bgriddle|\broast|\bbroil/i.test(t) && !NOT_PROTEIN_STEP.test(t);
}

// ── Air fryer ────────────────────────────────────────────────────────────────
export const AF_TYPES = {
  basket: { label: 'Basket / drawer', temp: 0, time: 1 },
  large: { label: 'Large or oven-style', temp: 0, time: 1.15 },
  mini: { label: 'Small (under 3 L)', temp: 0, time: 0.9 },
};
export const AF_CRISP = {
  soft: { label: 'Softer', temp: -10, time: 1 },
  standard: { label: 'Standard', temp: 0, time: 1 },
  crispy: { label: 'Extra crispy', temp: 10, time: 1.1 },
};
export const AF_DEFAULTS = { type: 'basket', crisp: 'standard', tempOffset: 0, timePct: 0 };

const OVEN = /\b(oven|bake|baked|baking|roast|roasted|roasting|preheat)\b/i;
const DEEP = /\bdeep[- ]?fr/i;
const GRILL = /\b(grill|grilled|broil|griddle)\b/i;
const PAN = /\b(pan[- ]?fr|shallow[- ]?fr|sear|seared|fry|fried|frying)\b/i;
const WET = /\b(simmer|boil|boiling|stew|sauce|soup|stock|steam|poach|braise|bring to)\b/i;
const NOT_AIRFRYABLE = /\b(soups?|stews?|curry|curries|chowder|risotto|porridge|smoothies?|pasta|spaghetti|noodles?|casserole|stir[- ]?fry|jam|sauce|dips?|pie)\b/i;

const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));
const roundTime = (s) => (s < 600 ? Math.max(60, Math.round(s / 30) * 30) : Math.round(s / 60) * 60);

// Convert one step. `ovenC` = oven temperature mentioned earlier in the recipe (for "roast for 25 minutes").
// Returns null when the step isn't something an air fryer does (boiling, sauces, chopping...).
export function airFryerStep(step, settings = AF_DEFAULTS, { ovenC = null } = {}) {
  const s = { ...AF_DEFAULTS, ...settings };
  const t = String(step || '');
  const dur = findDurations(t)[0];
  const temp = findTempC(t);
  const explicit = /air[- ]?fr/i.test(t);
  let base = null; let how = '';

  if (explicit && (temp || dur)) {
    base = { c: temp || ovenC || 180, sec: dur ? dur.seconds : 0 }; how = 'air fryer';
  } else if (WET.test(t) && !OVEN.test(t)) {
    return null;
  } else if (OVEN.test(t) && /preheat/i.test(t) && !dur) {
    const c = temp || ovenC; if (!c) return null;
    return { kind: 'preheat', tempC: adjustTemp(clamp(c - 20, 120, 200), s), seconds: 180, text: 'Preheat the air fryer for 3 minutes.' };
  } else if (OVEN.test(t) && dur) {
    const c = temp || ovenC; if (!c) return null;
    base = { c: clamp(c - 20, 120, 200), sec: dur.seconds * 0.75 }; how = `oven ${showTemp(c)}, ${dur.label}`;
  } else if (DEEP.test(t) && dur) {
    base = { c: 190, sec: dur.seconds * 2 }; how = `deep fry, ${dur.label}`;
  } else if (GRILL.test(t) && dur) {
    base = { c: 200, sec: dur.seconds }; how = `grill, ${dur.label}`;
  } else if (PAN.test(t) && dur) {
    base = { c: 190, sec: dur.seconds * 1.5 }; how = `pan-fry, ${dur.label}`;
  }
  if (!base || !base.sec) return null;

  const type = AF_TYPES[s.type] || AF_TYPES.basket; const crisp = AF_CRISP[s.crisp] || AF_CRISP.standard;
  const tempC = adjustTemp(base.c + type.temp + crisp.temp, s);
  const seconds = roundTime(base.sec * type.time * crisp.time * (1 + s.timePct / 100) );
  const notes = [];
  if (!explicit && (DEEP.test(t) || PAN.test(t))) notes.push('Lightly spray or toss with 1–2 tsp oil. No need for a pan of oil.');
  if (seconds >= 600) notes.push('Shake or turn halfway.');
  notes.push('Don’t overcrowd: cook in a single layer, in batches if needed.');
  return { kind: 'cook', tempC, seconds, from: how, notes, halfway: seconds >= 600 ? Math.round(seconds / 2) : null, approx: !explicit };
}
const adjustTemp = (c, s) => clamp(round5(c + (s.tempOffset || 0)), 80, 200);

// Plan for the whole recipe: one conversion (or null) per step.
export function airFryerPlan(steps, settings = AF_DEFAULTS, skip = () => false) {
  let ovenC = null;
  return (steps || []).map((step, i) => {
    const c = findTempC(step);
    if (c && OVEN.test(step)) ovenC = c;
    if (skip(step, i)) return null;      // protein steps are handled by the protein plan
    return airFryerStep(step, settings, { ovenC });
  });
}

// Is an air-fryer version worth offering for this recipe?
export function airFryerSuitable(recipe) {
  const steps = recipe?.steps || [];
  if (!steps.length) return false;
  if (steps.some((s) => /air[- ]?fr/i.test(s))) return true;
  const tags = (recipe.tags || []).join(' ');
  if (NOT_AIRFRYABLE.test(`${recipe.title || ''} ${tags}`)) return false;
  return airFryerPlan(steps).some((p) => p && p.kind === 'cook');
}

// Best guess at how the recipe itself cooks the protein, so the setup starts on the right method.
export function guessMethod(steps, type) {
  const t = (steps || []).join(' ').toLowerCase();
  let m = 'pan';
  if (/air[- ]?fr/.test(t)) m = 'airfryer';
  else if (/\b(grill|bbq|barbecue|griddle)\b/.test(t)) m = 'grill';
  else if (/\b(oven|bake|roast)\b/.test(t) && !/\b(pan|skillet|fry|sear)\b/.test(t)) m = 'oven';
  return type && !type.methods.includes(m) ? type.methods[0] : m;
}
