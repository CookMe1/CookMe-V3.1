import React, { useState } from 'react';
import { PROTEIN_TYPES, METHODS, AF_TYPES, AF_CRISP, showTemp, fmtLabel, describeStage } from '../utils/cookingTools';

const Chip = ({ active, onClick, children, testid }) => (
  <button type="button" onClick={onClick} data-testid={testid}
    className={`px-3 py-2 rounded-lg text-sm border transition-colors text-left ${active ? 'bg-orange-600 border-orange-500 text-white' : 'bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800'}`}>
    {children}
  </button>
);
const Q = ({ children }) => <p className="text-sm font-semibold text-zinc-200 mt-4 mb-2">{children}</p>;
const Stepper = ({ label, value, unit, onMinus, onPlus }) => (
  <div className="flex items-center justify-between bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2">
    <span className="text-sm text-zinc-300">{label}</span>
    <span className="flex items-center gap-3">
      <button type="button" onClick={onMinus} className="w-8 h-8 rounded-full bg-zinc-800 text-lg leading-none" aria-label={`Lower ${label}`}>−</button>
      <span className="w-16 text-center text-sm tabular-nums">{value > 0 ? '+' : ''}{value}{unit}</span>
      <button type="button" onClick={onPlus} className="w-8 h-8 rounded-full bg-zinc-800 text-lg leading-none" aria-label={`Raise ${label}`}>+</button>
    </span>
  </div>
);

// "What are you cooking, how big, how do you like it, how are you cooking it" + a live plan.
const CookingOptions = ({ setup }) => {
  const { type, plan, method, sizeId, doneId, af, afOn, afSuitable } = setup;
  const [choosing, setChoosing] = useState(false);
  const methods = type ? type.methods : ['recipe', 'airfryer'];

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4" data-testid="cooking-options">
      <h3 className="font-semibold text-zinc-100">Cooking setup</h3>
      <p className="text-xs text-zinc-500">Tell us how you’re cooking and we’ll adjust the times and temperatures.</p>

      {(type || choosing) ? (
        <>
          <Q>What are you cooking?</Q>
          <div className="flex flex-wrap gap-2">
            {PROTEIN_TYPES.map((t) => (
              <Chip key={t.id} active={type && type.id === t.id} onClick={() => setup.setType(t.id)} testid={`protein-${t.id}`}>{t.icon} {t.name}</Chip>
            ))}
            <Chip active={!type} onClick={() => { setup.setType(null); setChoosing(false); }} testid="protein-none">Something else</Chip>
          </div>
        </>
      ) : (
        <button type="button" onClick={() => setChoosing(true)} className="mt-3 text-sm text-orange-400 underline" data-testid="choose-protein">Cooking meat or fish? Choose it for exact timings</button>
      )}

      {type && (
        <>
          <Q>{type.id.startsWith('joint') || type.id === 'whole-chicken' ? 'How heavy is it?' : 'How big is it? (thickness matters most)'}</Q>
          <div className="flex flex-wrap gap-2">
            {type.sizes.map((s) => <Chip key={s.id} active={sizeId === s.id} onClick={() => setup.setSize(s.id)} testid={`size-${s.id}`}>{s.label}</Chip>)}
          </div>
          {type.doneness && (
            <>
              <Q>How do you like it cooked?</Q>
              <div className="flex flex-wrap gap-2">
                {type.doneness.map((d) => <Chip key={d.id} active={doneId === d.id} onClick={() => setup.setDone(d.id)} testid={`done-${d.id}`}>{d.label} <span className="opacity-70">· {showTemp(d.tempC)}</span></Chip>)}
              </div>
            </>
          )}
        </>
      )}

      {(type || afSuitable) && (
        <>
          <Q>How are you cooking it?</Q>
          <div className="flex flex-wrap gap-2">
            {methods.map((m) => (
              <Chip key={m} active={method === m} onClick={() => setup.setMethod(m)} testid={`method-${m}`}>
                {m === 'recipe' ? '📖 As the recipe says' : `${METHODS[m].icon} ${METHODS[m].label}`}
              </Chip>
            ))}
          </div>
        </>
      )}

      {afOn && (
        <div className="mt-4 space-y-3" data-testid="airfryer-settings">
          <p className="text-sm font-semibold text-zinc-200">Air fryer settings</p>
          <select value={af.type} onChange={(e) => setup.setAf({ type: e.target.value })} className="w-full h-10 rounded-md bg-zinc-900 border border-zinc-700 px-3 text-sm" data-testid="af-type">
            {Object.entries(AF_TYPES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <div className="flex flex-wrap gap-2">
            {Object.entries(AF_CRISP).map(([k, v]) => <Chip key={k} active={af.crisp === k} onClick={() => setup.setAf({ crisp: k })} testid={`af-crisp-${k}`}>{v.label}</Chip>)}
          </div>
          <Stepper label="Fine-tune temperature" value={af.tempOffset} unit="°C" onMinus={() => setup.setAf({ tempOffset: Math.max(-20, af.tempOffset - 5) })} onPlus={() => setup.setAf({ tempOffset: Math.min(20, af.tempOffset + 5) })} />
          <Stepper label="Fine-tune time" value={af.timePct} unit="%" onMinus={() => setup.setAf({ timePct: Math.max(-30, af.timePct - 10) })} onPlus={() => setup.setAf({ timePct: Math.min(30, af.timePct + 10) })} />
          <p className="text-xs text-zinc-500">Air fryers differ, so these are a starting point. Check the food a few minutes early the first time, and save your tweaks: we remember them.</p>
        </div>
      )}

      {plan && (
        <div className="mt-5 rounded-lg border border-orange-600/40 bg-orange-600/10 p-3 text-sm" data-testid="protein-plan">
          <p className="font-semibold text-orange-300 mb-1">Your plan</p>
          <p className="text-zinc-200">{plan.heat}{plan.tempC && !plan.heat.includes('°') ? ` (${showTemp(plan.tempC)})` : ''}</p>
          <ul className="list-disc pl-5 text-zinc-300 mt-1 space-y-0.5">
            {plan.stages.map((s, i) => <li key={i}>{describeStage(s)}</li>)}
            {plan.rest > 0 && <li>Rest: {plan.rest} min</li>}
          </ul>
          <p className="text-zinc-200 mt-2">Target core temperature: <span className="font-semibold">{showTemp(plan.internalC)}</span> <span className="text-zinc-500">(a meat thermometer is the only sure way)</span></p>
          {plan.notes.map((n, i) => <p key={i} className="text-xs text-zinc-400 mt-1">{n}</p>)}
          {plan.safety && <p className="text-xs text-amber-300 mt-2" data-testid="plan-safety">{plan.safety}</p>}
        </div>
      )}
      {!plan && afOn && <p className="text-xs text-zinc-400 mt-3">Steps that use the oven or frying get air fryer settings. Boiling, simmering and sauces stay the same.</p>}
    </div>
  );
};

export { fmtLabel };
export default CookingOptions;
