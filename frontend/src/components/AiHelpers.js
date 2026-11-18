import React, { useState } from 'react';
import { ArrowLeftRight, Sparkles, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

const call = async (path, body) => {
  const res = await fetch(`${API_URL}/api/ai${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'Something went wrong. Please try again.');
  return data;
};

const Sheet = ({ title, onClose, children, testid }) => (
  <div
    className="fixed inset-0 z-[60] bg-black/70 flex items-end sm:items-center justify-center p-0 sm:p-4"
    role="dialog"
    aria-modal="true"
    data-testid={testid}
    onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
  >
    <div className="bg-zinc-900 border border-zinc-700 w-full sm:max-w-lg max-h-[88vh] overflow-y-auto rounded-t-2xl sm:rounded-2xl p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="text-lg font-semibold text-zinc-100">{title}</h3>
        <button onClick={onClose} aria-label="Close" className="p-1 text-zinc-400 hover:text-zinc-200"><X className="w-5 h-5" /></button>
      </div>
      {children}
    </div>
  </div>
);

// ── Swap one ingredient ──────────────────────────────────────────────────────
export const SwapButton = ({ ingredient, recipeTitle }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);

  const start = async () => {
    setOpen(true);
    if (data) return;
    setLoading(true);
    try {
      setData(await call('/substitutes', { ingredient, recipe_title: recipeTitle }));
    } catch (e) {
      toast.error(e.message);
      setOpen(false);
    } finally { setLoading(false); }
  };

  return (
    <>
      <button
        title="What can I use instead?"
        aria-label={`Substitutes for ${ingredient}`}
        data-testid="swap-btn"
        onClick={start}
        className="p-2 rounded-md border border-zinc-700 text-zinc-300 hover:border-purple-500 hover:text-purple-400"
      >
        <ArrowLeftRight className="w-4 h-4" />
      </button>
      {open && (
        <Sheet title={`Instead of ${ingredient}`} onClose={() => setOpen(false)} testid="swap-sheet">
          {loading && <p className="text-zinc-400 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Thinking...</p>}
          {data && (
            <div className="space-y-3">
              {data.substitutes.length === 0 && <p className="text-zinc-400">No good substitutes found.</p>}
              {data.substitutes.map((s, i) => (
                <div key={i} className="p-3 rounded-lg bg-zinc-800/60 border border-zinc-700">
                  <div className="flex justify-between gap-3">
                    <span className="font-medium text-zinc-100">{s.item}</span>
                    <span className="text-orange-400 text-sm shrink-0">{s.amount}</span>
                  </div>
                  {s.note && <p className="text-sm text-zinc-400 mt-1">{s.note}</p>}
                </div>
              ))}
              <p className="text-xs text-zinc-500">AI suggestions. Check allergies and taste before cooking.
                {typeof data.left_today === 'number' && ` ${data.left_today} swaps left today.`}</p>
            </div>
          )}
        </Sheet>
      )}
    </>
  );
};

// ── Convert the whole recipe to a diet ───────────────────────────────────────
const DIETS = [
  ['vegan', 'Vegan'], ['vegetarian', 'Vegetarian'], ['gluten-free', 'Gluten-free'],
  ['dairy-free', 'Dairy-free'], ['low-carb', 'Low-carb'], ['nut-free', 'Nut-free'],
];

// Vegan already covers vegetarian and dairy-free, so ticking it ticks (and locks) those.
const COVERED_BY_VEGAN = ['vegetarian', 'dairy-free'];

export const DietConvert = ({ recipeId }) => {
  const [show, setShow] = useState(false);
  const [picked, setPicked] = useState([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [saving, setSaving] = useState(false);

  const toggle = (key) => setPicked((p) => (p.includes(key) ? p.filter((k) => k !== key) : [...p, key]));
  const covered = (key) => picked.includes('vegan') && COVERED_BY_VEGAN.includes(key);

  const run = async () => {
    if (!picked.length) { toast.error('Tick at least one option'); return; }
    setBusy(true);
    try {
      setResult(await call('/convert-recipe', { recipe_id: recipeId, diets: picked.filter((k) => !covered(k)) }));
    } catch (e) { toast.error(e.message); }
    finally { setBusy(false); }
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/recipes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({
          title: result.title,
          description: `${(result.diets || [result.diet]).join(' + ')} version. ${(result.changes || []).slice(0, 2).join('; ')}`.slice(0, 300),
          prep_time: result.prep_time || '15 min',
          cook_time: result.cook_time || '30 min',
          servings: result.servings || 4,
          difficulty: 'Medium',
          image: result.image || '',
          ingredients: result.ingredients,
          steps: result.steps,
          tags: ['AI Converted', ...(result.diets || [result.diet])],
          ai_generated: true,
        }),
      });
      if (!res.ok) throw new Error();
      toast.success('Saved to your recipes');
      setResult(null);
    } catch { toast.error('Could not save the recipe'); }
    finally { setSaving(false); }
  };

  return (
    <div className="mb-1">
      <button
        onClick={() => setShow(!show)}
        data-testid="diet-convert-toggle"
        className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-300 text-sm font-medium hover:bg-purple-500/20"
      >
        <Sparkles className="w-4 h-4" /> Make it vegan, gluten-free and more
      </button>
      {show && (
        <div className="mt-2 p-3 rounded-lg bg-zinc-900/60 border border-zinc-800" data-testid="diet-options">
          <p className="text-xs text-zinc-500 mb-2">Tick everything you need. It is done in one go.</p>
          <div className="flex flex-wrap gap-2">
            {DIETS.map(([key, label]) => {
              const on = picked.includes(key) || covered(key);
              return (
                <button
                  key={key}
                  type="button"
                  aria-pressed={on}
                  disabled={busy || covered(key)}
                  onClick={() => toggle(key)}
                  className={`px-3 h-10 rounded-full border text-sm ${on ? 'border-purple-500 bg-purple-500/20 text-purple-200' : 'border-zinc-700 text-zinc-200 hover:border-purple-500'} disabled:opacity-80`}
                >
                  {on ? '✓ ' : ''}{label}
                </button>
              );
            })}
          </div>
          <button
            onClick={run}
            disabled={busy || !picked.length}
            data-testid="diet-run"
            className="mt-3 w-full h-11 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {busy && <Loader2 className="w-4 h-4 animate-spin" />}{busy ? 'Converting…' : 'Convert recipe'}
          </button>
        </div>
      )}
      {result && (
        <Sheet title={result.title} onClose={() => setResult(null)} testid="diet-result">
          {result.changes?.length > 0 && (
            <div className="mb-3 p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
              <p className="text-xs uppercase tracking-wide text-purple-300 mb-1">What changed</p>
              <ul className="text-sm text-zinc-200 list-disc list-inside space-y-0.5">
                {result.changes.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </div>
          )}
          <p className="text-sm font-medium text-zinc-300 mb-1">Ingredients</p>
          <ul className="text-sm text-zinc-300 space-y-1 mb-3">
            {result.ingredients.map((ing, i) => (
              <li key={i}><span className="text-orange-400">{ing.amount}</span> {ing.item}</li>
            ))}
          </ul>
          <p className="text-sm font-medium text-zinc-300 mb-1">Method</p>
          <ol className="text-sm text-zinc-300 space-y-2 list-decimal list-inside mb-4">
            {result.steps.map((st, i) => <li key={i} className="leading-relaxed">{typeof st === 'string' ? st : st.text}</li>)}
          </ol>
          <p className="text-xs text-zinc-500 mb-3">AI-made: check allergies and taste before cooking.
            {typeof result.left_today === 'number' && ` ${result.left_today} AI requests left today.`}</p>
          <button
            onClick={save}
            disabled={saving}
            data-testid="diet-save"
            className="w-full h-11 rounded-lg bg-orange-600 hover:bg-orange-700 font-semibold text-white disabled:opacity-60"
          >
            {saving ? 'Saving...' : 'Save as my recipe'}
          </button>
        </Sheet>
      )}
    </div>
  );
};
