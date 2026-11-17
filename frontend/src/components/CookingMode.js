import React, { useEffect, useRef, useState, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Timer, Pause, Play, List, SlidersHorizontal, Plus, Thermometer } from 'lucide-react';
import CookingOptions from './CookingOptions';
import { findDurations, fmtClock, fmtLabel, showTemp, stepCooksProtein } from '../utils/cookingTools';

// Kept for older callers: the first duration in a step, in seconds.
export function findStepSeconds(text) {
  const d = findDurations(text)[0];
  return d ? d.seconds : null;
}

const beep = (n = 3) => {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    for (let i = 0; i < n; i += 1) {
      const o = ctx.createOscillator(); const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination); o.frequency.value = 880; g.gain.value = 0.2;
      o.start(ctx.currentTime + i * 0.35); o.stop(ctx.currentTime + i * 0.35 + 0.2);
    }
  } catch (e) { /* sound not available */ }
  try { navigator.vibrate && navigator.vibrate([300, 150, 300]); } catch (e) { /* ignore */ }
};

const sideTwo = (label) => (/side 1/i.test(label) ? label.replace(/side 1/i, 'side 2') : `${label} (side 2)`);

// What timers (quick-start buttons) belong to this step.
export function stepChips(step, idx, setup) {
  const chips = [];
  const { type, plan, afOn, afSteps } = setup;
  const conv = afOn ? afSteps[idx] : null;

  if (plan && stepCooksProtein(step, type)) {
    plan.stages.forEach((s) => chips.push({
      label: s.perSide ? s.label : s.label, seconds: s.seconds, halfway: !!s.halfway,
      after: s.perSide ? { label: sideTwo(s.label), seconds: s.seconds } : null, perSide: s.perSide,
    }));
    return { chips, source: 'plan' };
  }
  if (conv) {
    chips.push(conv.kind === 'preheat'
      ? { label: 'Preheat air fryer', seconds: conv.seconds }
      : { label: 'Air fry', seconds: conv.seconds, halfway: !!conv.halfway });
    return { chips, source: 'airfryer', conv };
  }
  if (plan && plan.rest > 0 && /\brest\b/i.test(step)) {
    chips.push({ label: 'Rest', seconds: plan.rest * 60 });
    return { chips, source: 'rest' };
  }
  findDurations(step).forEach((d) => chips.push({
    label: d.label, timeInLabel: true, seconds: d.seconds, after: d.perSide ? { label: 'side 2', seconds: d.seconds } : null, perSide: d.perSide,
  }));
  return { chips, source: 'recipe' };
}

const CookingMode = ({ title, steps, ingredients, setup, onClose }) => {
  const [idx, setIdx] = useState(0);
  const [showIngredients, setShowIngredients] = useState(false);
  const [intro, setIntro] = useState(!!setup.available);
  const [timers, setTimers] = useState([]);
  const [now, setNow] = useState(Date.now());
  const [alertMsg, setAlertMsg] = useState('');
  const wakeLock = useRef(null);
  const nextId = useRef(1);

  // Keep the screen awake while cooking
  useEffect(() => {
    let active = true;
    const request = async () => {
      try { if ('wakeLock' in navigator && active) wakeLock.current = await navigator.wakeLock.request('screen'); } catch (e) { /* not supported or denied */ }
    };
    request();
    const onVisible = () => { if (document.visibilityState === 'visible') request(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      active = false; document.removeEventListener('visibilitychange', onVisible);
      try { wakeLock.current && wakeLock.current.release(); } catch (e) { /* ignore */ }
    };
  }, []);

  const leftOf = (t) => (t.running ? Math.max(0, Math.ceil((t.endsAt - now) / 1000)) : t.left);

  // One clock for every timer (uses real time, so it stays right if the phone sleeps)
  useEffect(() => {
    if (!timers.some((t) => t.running)) return undefined;
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [timers]);

  useEffect(() => {
    let changed = false; let msg = ''; let big = false;
    const next = timers.map((t) => {
      if (!t.running) return t;
      const left = Math.max(0, Math.ceil((t.endsAt - now) / 1000));
      if (left <= 0) { changed = true; big = true; msg = `${t.label}: time’s up!`; return { ...t, running: false, done: true, left: 0 }; }
      if (t.halfway && !t.halfDone && left <= t.total / 2) { changed = true; msg = `${t.label}: halfway. Turn or shake it now.`; return { ...t, halfDone: true }; }
      return t;
    });
    if (changed) { setTimers(next); setAlertMsg(msg); beep(big ? 3 : 1); }
  }, [now, timers]);

  const startTimer = useCallback((c) => {
    setNow(Date.now());
    setTimers((ts) => [...ts, { id: nextId.current++, label: c.label, total: c.seconds, left: c.seconds, endsAt: Date.now() + c.seconds * 1000, running: true, done: false, after: c.after || null, halfway: !!c.halfway, halfDone: false }]);
  }, []);
  const toggle = (id) => setTimers((ts) => ts.map((t) => {
    if (t.id !== id || t.done) return t;
    return t.running ? { ...t, running: false, left: Math.max(0, Math.ceil((t.endsAt - Date.now()) / 1000)) } : { ...t, running: true, endsAt: Date.now() + t.left * 1000 };
  }));
  const addMinute = (id) => setTimers((ts) => ts.map((t) => (t.id !== id ? t : t.running ? { ...t, endsAt: t.endsAt + 60000, total: t.total + 60 } : { ...t, left: t.left + 60, total: t.total + 60, done: false })));
  const clear = (id) => setTimers((ts) => ts.filter((t) => t.id !== id));

  const go = useCallback((d) => setIdx((i) => Math.min(steps.length - 1, Math.max(0, i + d))), [steps.length]);
  useEffect(() => {
    const onKey = (e) => {
      if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, onClose]);

  const step = steps[idx] || '';
  const { chips, source, conv } = stepChips(step, idx, setup);
  const proteinStep = setup.plan && (stepCooksProtein(step, setup.type) || setup.type.words.test(step));

  const header = (
    <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
      <div className="min-w-0">
        <p className="text-xs text-zinc-500 uppercase tracking-wider">Cooking mode</p>
        <h2 className="font-semibold truncate">{title}</h2>
      </div>
      <div className="flex gap-2">
        {setup.available && !intro && (
          <button onClick={() => setIntro(true)} className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700" aria-label="Cooking setup" data-testid="open-setup"><SlidersHorizontal className="w-5 h-5" /></button>
        )}
        <button onClick={() => setShowIngredients((v) => !v)} className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700" aria-label="Ingredients"><List className="w-5 h-5" /></button>
        <button onClick={onClose} className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700" aria-label="Close cooking mode" data-testid="cooking-close"><X className="w-5 h-5" /></button>
      </div>
    </div>
  );

  if (intro) {
    return (
      <div className="fixed inset-0 z-[100] bg-[#09090b] text-zinc-100 flex flex-col" data-testid="cooking-mode">
        {header}
        <div className="flex-1 overflow-y-auto p-4 max-w-2xl w-full mx-auto">
          <h3 className="text-xl font-semibold mb-3">Before you start</h3>
          <CookingOptions setup={setup} />
        </div>
        <div className="p-4 border-t border-zinc-800">
          <button onClick={() => setIntro(false)} className="w-full h-14 rounded-xl bg-orange-600 hover:bg-orange-700 text-lg font-semibold" data-testid="begin-cooking">Start cooking</button>
        </div>
      </div>
    );
  }

  const clock = (t) => (t.done ? "Time's up!" : fmtClock(leftOf(t)));

  return (
    <div className="fixed inset-0 z-[100] bg-[#09090b] text-zinc-100 flex flex-col" data-testid="cooking-mode">
      {header}
      <div className="h-1 bg-zinc-800"><div className="h-1 bg-orange-500 transition-all" style={{ width: `${((idx + 1) / steps.length) * 100}%` }} /></div>

      {showIngredients ? (
        <div className="flex-1 overflow-y-auto p-6 max-w-2xl w-full mx-auto">
          <h3 className="text-lg font-semibold mb-4">Ingredients</h3>
          <ul className="space-y-3 text-xl">
            {ingredients.map((ing, i) => (
              <li key={i} className="flex justify-between gap-4 border-b border-zinc-800 pb-2"><span>{ing.name}</span><span className="text-orange-500 shrink-0">{ing.amount}</span></li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto flex flex-col items-center justify-center p-6 text-center max-w-3xl w-full mx-auto">
          <p className="text-orange-500 font-semibold mb-4">Step {idx + 1} of {steps.length}</p>
          <p className="text-2xl sm:text-4xl leading-snug font-medium">{step}</p>

          {source === 'airfryer' && conv && (
            <div className="mt-5 w-full max-w-xl rounded-xl border border-orange-600/40 bg-orange-600/10 p-3 text-left text-sm" data-testid="airfryer-note">
              <p className="font-semibold text-orange-300">🍟 Air fryer: {showTemp(conv.tempC)}{conv.kind === 'cook' ? `, ${fmtLabel(conv.seconds)}` : ''}</p>
              {conv.kind === 'cook' && conv.from && <p className="text-zinc-400 text-xs">Instead of: {conv.from}{conv.approx ? ' (approximate)' : ''}</p>}
              {conv.kind === 'preheat' && <p className="text-zinc-300">{conv.text}</p>}
              {(conv.notes || []).map((n, i) => <p key={i} className="text-zinc-300 text-xs mt-1">{n}</p>)}
            </div>
          )}

          {source === 'plan' && (
            <div className="mt-5 w-full max-w-xl rounded-xl border border-orange-600/40 bg-orange-600/10 p-3 text-left text-sm" data-testid="plan-note">
              <p className="font-semibold text-orange-300">Adjusted for your {setup.type.name.toLowerCase()} ({setup.plan.size.label.split(' (')[0].toLowerCase()}{setup.plan.doneness ? `, ${setup.plan.doneness.label.toLowerCase()}` : ''})</p>
              <p className="text-zinc-300">{setup.plan.heat}{setup.plan.tempC && !setup.plan.heat.includes('°') ? ` (${showTemp(setup.plan.tempC)})` : ''}</p>
              <p className="text-zinc-500 text-xs mt-1">These timings replace the ones in the recipe.</p>
            </div>
          )}

          {proteinStep && (
            <p className="mt-3 inline-flex items-center gap-2 text-amber-300 text-sm" data-testid="core-temp">
              <Thermometer className="w-4 h-4" /> Aim for {showTemp(setup.plan.internalC)} in the centre{setup.plan.rest > 0 ? `, then rest ${setup.plan.rest} min` : ''}
            </p>
          )}

          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {chips.map((c, i) => (
              <button key={i} onClick={() => startTimer(c)} className="inline-flex items-center gap-2 px-5 h-12 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-lg" data-testid="start-timer">
                <Timer className="w-5 h-5" /> {c.label.replace(/ side 1/i, '')}{c.timeInLabel ? '' : ` · ${fmtLabel(c.seconds)}`}{c.perSide ? ' per side' : ''}
              </button>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-2 text-sm text-zinc-400" data-testid="custom-timer">
            <span>Your own timer:</span>
            {[1, 5, 10, 15].map((m) => (
              <button key={m} onClick={() => startTimer({ label: `${m} min timer`, seconds: m * 60 })} className="px-3 h-9 rounded-lg bg-zinc-900 border border-zinc-700 hover:bg-zinc-800 whitespace-nowrap">{m} min</button>
            ))}
          </div>
        </div>
      )}

      {alertMsg && (
        <div className="mx-4 mb-2 rounded-xl px-4 py-2 bg-green-600/20 border border-green-600/40 text-green-300 text-sm flex items-center justify-between" role="alert" data-testid="timer-alert">
          <span>{alertMsg}</span><button onClick={() => setAlertMsg('')} aria-label="Dismiss"><X className="w-4 h-4" /></button>
        </div>
      )}

      {timers.length > 0 && (
        <div className="mx-4 mb-3 space-y-2 max-h-40 overflow-y-auto" data-testid="timer-tray">
          {timers.map((t) => (
            <div key={t.id} className={`rounded-xl px-4 py-2 flex items-center justify-between gap-2 ${t.done ? 'bg-green-600/20 border border-green-600/40' : 'bg-zinc-900 border border-zinc-800'}`}>
              <div className="min-w-0">
                <p className="text-xs text-zinc-400 truncate">{t.label}</p>
                <span className="text-2xl font-mono tabular-nums" data-testid="timer-display">{clock(t)}</span>
              </div>
              <div className="flex gap-2 items-center shrink-0">
                {t.done && t.after && (
                  <button onClick={() => { startTimer(t.after); clear(t.id); }} className="px-3 h-9 rounded-lg bg-orange-600 text-sm font-semibold" data-testid="start-next-side">Flip! Start {t.after.label}</button>
                )}
                {!t.done && <button onClick={() => addMinute(t.id)} className="px-2 h-9 rounded-lg bg-zinc-800 text-xs inline-flex items-center" aria-label="Add one minute"><Plus className="w-3 h-3" />1m</button>}
                {!t.done && (
                  <button onClick={() => toggle(t.id)} className="p-2 rounded-lg bg-zinc-800" aria-label="Pause or resume timer">{t.running ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}</button>
                )}
                <button onClick={() => clear(t.id)} className="p-2 rounded-lg bg-zinc-800" aria-label="Clear timer"><X className="w-5 h-5" /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3 p-4 border-t border-zinc-800">
        <button onClick={() => go(-1)} disabled={idx === 0} className="flex-1 h-14 rounded-xl bg-zinc-800 disabled:opacity-30 flex items-center justify-center gap-2 text-lg"><ChevronLeft className="w-6 h-6" /> Back</button>
        {idx < steps.length - 1 ? (
          <button onClick={() => go(1)} className="flex-1 h-14 rounded-xl bg-orange-600 hover:bg-orange-700 flex items-center justify-center gap-2 text-lg font-semibold" data-testid="cooking-next">Next <ChevronRight className="w-6 h-6" /></button>
        ) : (
          <button onClick={onClose} className="flex-1 h-14 rounded-xl bg-green-600 hover:bg-green-700 text-lg font-semibold">Done 🎉</button>
        )}
      </div>
    </div>
  );
};

export default CookingMode;
