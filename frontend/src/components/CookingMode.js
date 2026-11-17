import React, { useEffect, useRef, useState, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Timer, Pause, Play, List } from 'lucide-react';

// Finds the first duration in a step, e.g. "simmer for 10-15 minutes" -> 15 min (upper end of a range).
export function findStepSeconds(text) {
  const m = String(text || '').match(/(\d+)(?:\s*(?:-|–|to)\s*(\d+))?\s*(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b/i);
  if (!m) return null;
  const n = parseInt(m[2] || m[1], 10);
  const unit = m[3].toLowerCase();
  if (unit.startsWith('h')) return n * 3600;
  if (unit.startsWith('m')) return n * 60;
  return n;
}

const fmt = (s) => {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return (h ? `${h}:` : '') + `${String(m).padStart(h ? 2 : 1, '0')}:${String(sec).padStart(2, '0')}`;
};

const beep = () => {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    [0, 0.35, 0.7].forEach((t) => {
      const o = ctx.createOscillator(); const g = ctx.createGain();
      o.connect(g); g.connect(ctx.destination); o.frequency.value = 880; g.gain.value = 0.2;
      o.start(ctx.currentTime + t); o.stop(ctx.currentTime + t + 0.2);
    });
  } catch (e) { /* sound not available */ }
  try { navigator.vibrate && navigator.vibrate([300, 150, 300]); } catch (e) { /* ignore */ }
};

const CookingMode = ({ title, steps, ingredients, onClose }) => {
  const [idx, setIdx] = useState(0);
  const [showIngredients, setShowIngredients] = useState(false);
  const [timer, setTimer] = useState(null); // { left, total, running, step }
  const wakeLock = useRef(null);

  // Keep the screen awake while cooking
  useEffect(() => {
    let active = true;
    const request = async () => {
      try {
        if ('wakeLock' in navigator && active) wakeLock.current = await navigator.wakeLock.request('screen');
      } catch (e) { /* not supported or denied */ }
    };
    request();
    const onVisible = () => { if (document.visibilityState === 'visible') request(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      active = false;
      document.removeEventListener('visibilitychange', onVisible);
      try { wakeLock.current && wakeLock.current.release(); } catch (e) { /* ignore */ }
    };
  }, []);

  // Countdown
  useEffect(() => {
    if (!timer || !timer.running) return undefined;
    const id = setInterval(() => {
      setTimer((t) => {
        if (!t || !t.running) return t;
        if (t.left <= 1) { beep(); return { ...t, left: 0, running: false, done: true }; }
        return { ...t, left: t.left - 1 };
      });
    }, 1000);
    return () => clearInterval(id);
  }, [timer]);

  const go = useCallback((d) => setIdx((i) => Math.min(steps.length - 1, Math.max(0, i + d))), [steps.length]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); go(1); }
      if (e.key === 'ArrowLeft') go(-1);
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, onClose]);

  const step = steps[idx] || '';
  const seconds = findStepSeconds(step);

  return (
    <div className="fixed inset-0 z-[100] bg-[#09090b] text-zinc-100 flex flex-col" data-testid="cooking-mode">
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <div className="min-w-0">
          <p className="text-xs text-zinc-500 uppercase tracking-wider">Cooking mode</p>
          <h2 className="font-semibold truncate">{title}</h2>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowIngredients((v) => !v)} className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700" aria-label="Ingredients">
            <List className="w-5 h-5" />
          </button>
          <button onClick={onClose} className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700" aria-label="Close cooking mode" data-testid="cooking-close">
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      <div className="h-1 bg-zinc-800"><div className="h-1 bg-orange-500 transition-all" style={{ width: `${((idx + 1) / steps.length) * 100}%` }} /></div>

      {showIngredients ? (
        <div className="flex-1 overflow-y-auto p-6 max-w-2xl w-full mx-auto">
          <h3 className="text-lg font-semibold mb-4">Ingredients</h3>
          <ul className="space-y-3 text-xl">
            {ingredients.map((ing, i) => (
              <li key={i} className="flex justify-between gap-4 border-b border-zinc-800 pb-2">
                <span>{ing.name}</span><span className="text-orange-500 shrink-0">{ing.amount}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto flex flex-col items-center justify-center p-6 text-center max-w-3xl w-full mx-auto">
          <p className="text-orange-500 font-semibold mb-4">Step {idx + 1} of {steps.length}</p>
          <p className="text-2xl sm:text-4xl leading-snug font-medium">{step}</p>

          {seconds && (!timer || timer.step !== idx) && (
            <button
              onClick={() => setTimer({ left: seconds, total: seconds, running: true, step: idx })}
              className="mt-8 inline-flex items-center gap-2 px-5 h-12 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-lg"
              data-testid="start-timer"
            >
              <Timer className="w-5 h-5" /> Start {fmt(seconds)} timer
            </button>
          )}
        </div>
      )}

      {timer && (
        <div className={`mx-4 mb-3 rounded-xl px-4 py-3 flex items-center justify-between ${timer.done ? 'bg-green-600/20 border border-green-600/40' : 'bg-zinc-900 border border-zinc-800'}`}>
          <span className="text-3xl font-mono tabular-nums" data-testid="timer-display">{timer.done ? "Time's up!" : fmt(timer.left)}</span>
          <div className="flex gap-2 items-center">
            <span className="text-xs text-zinc-500">step {timer.step + 1}</span>
            {!timer.done && (
              <button onClick={() => setTimer((t) => ({ ...t, running: !t.running }))} className="p-2 rounded-lg bg-zinc-800" aria-label="Pause or resume timer">
                {timer.running ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
              </button>
            )}
            <button onClick={() => setTimer(null)} className="p-2 rounded-lg bg-zinc-800" aria-label="Clear timer"><X className="w-5 h-5" /></button>
          </div>
        </div>
      )}

      <div className="flex gap-3 p-4 border-t border-zinc-800">
        <button onClick={() => go(-1)} disabled={idx === 0} className="flex-1 h-14 rounded-xl bg-zinc-800 disabled:opacity-30 flex items-center justify-center gap-2 text-lg">
          <ChevronLeft className="w-6 h-6" /> Back
        </button>
        {idx < steps.length - 1 ? (
          <button onClick={() => go(1)} className="flex-1 h-14 rounded-xl bg-orange-600 hover:bg-orange-700 flex items-center justify-center gap-2 text-lg font-semibold" data-testid="cooking-next">
            Next <ChevronRight className="w-6 h-6" />
          </button>
        ) : (
          <button onClick={onClose} className="flex-1 h-14 rounded-xl bg-green-600 hover:bg-green-700 text-lg font-semibold">Done 🎉</button>
        )}
      </div>
    </div>
  );
};

export default CookingMode;
