import { useMemo, useState, useCallback } from 'react';
import { detectProteinType, proteinTypeById, proteinPlan, guessMethod, airFryerPlan, airFryerSuitable, stepCooksProtein, AF_DEFAULTS } from '../utils/cookingTools';

const KEY = 'cookme_cook_prefs';
const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
const store = (p) => { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* private mode */ } };

// Everything the user chose about how to cook this recipe, and the plan worked out from it.
export default function useCookingSetup(recipe) {
  const steps = useMemo(() => recipe?.steps || [], [recipe]);
  const detected = useMemo(() => detectProteinType(recipe), [recipe]);
  const afSuitable = useMemo(() => airFryerSuitable(recipe), [recipe]);
  const [prefs, setPrefs] = useState(load);
  const [typeId, setTypeId] = useState(undefined);   // undefined = auto-detected, null = "something else / skip"
  const [own, setOwn] = useState({});                // this recipe's choices: sizeId, doneId, method

  const type = typeId === undefined ? detected : (typeId ? proteinTypeById(typeId) : null);
  const sizeId = type ? (own.sizeId || prefs.sizes?.[type.id] || type.defaultSize) : null;
  const doneId = type && type.doneness ? (own.doneId || prefs.done?.[type.id] || type.defaultDoneness) : null;
  const method = own.method || (type ? guessMethod(steps, type) : 'recipe');
  const af = { ...AF_DEFAULTS, ...(prefs.af || {}) };

  const plan = useMemo(() => (type ? proteinPlan(type, { sizeId, doneId, method }) : null), [type, sizeId, doneId, method]);
  const afOn = method === 'airfryer';
  const afSteps = useMemo(
    () => (afOn ? airFryerPlan(steps, af, (s) => !!(type && plan && stepCooksProtein(s, type))) : []),
    [afOn, steps, af.type, af.crisp, af.tempOffset, af.timePct, type, plan] // eslint-disable-line react-hooks/exhaustive-deps
  );

  const remember = useCallback((patch) => setPrefs((p) => { const n = { ...p, ...patch }; store(n); return n; }), []);
  return {
    type, plan, method, sizeId, doneId, af, afOn, afSteps, afSuitable, detected,
    available: !!type || afSuitable,
    setType: (id) => { setTypeId(id); setOwn({}); },
    setSize: (id) => { setOwn((o) => ({ ...o, sizeId: id })); if (type) remember({ sizes: { ...(prefs.sizes || {}), [type.id]: id } }); },
    setDone: (id) => { setOwn((o) => ({ ...o, doneId: id })); if (type) remember({ done: { ...(prefs.done || {}), [type.id]: id } }); },
    setMethod: (m) => setOwn((o) => ({ ...o, method: m })),
    setAf: (patch) => remember({ af: { ...af, ...patch } }),
  };
}
