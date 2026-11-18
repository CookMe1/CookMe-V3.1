import { findDurations, findTempC, detectProteinType, proteinTypeById, proteinPlan, stepCooksProtein, airFryerStep, airFryerPlan, airFryerSuitable, fmtClock } from './cookingTools';

test('finds timers, ranges, words and per-side', () => {
  expect(findDurations('Simmer for 10-12 minutes.')[0]).toMatchObject({ seconds: 600, label: '10–12 min' });
  expect(findDurations('Cook for five minutes')[0].seconds).toBe(300);
  expect(findDurations('Rest for an hour')[0].seconds).toBe(3600);
  expect(findDurations('Sear 4 minutes per side')[0]).toMatchObject({ seconds: 240, perSide: true });
  expect(findDurations('Bake 1 hour 30 minutes').map((d) => d.seconds)).toEqual([3600, 1800]);
  expect(findDurations('Add 200 g flour and 2 tbsp oil')).toEqual([]);
  expect(findDurations('Cook until golden')).toEqual([]);
});

test('finds temperatures', () => {
  expect(findTempC('Preheat the oven to 200°C')).toBe(200);
  expect(findTempC('Heat to 180C / 350F')).toBe(180);
  expect(findTempC('Oven at 400°F')).toBe(205);
  expect(findTempC('gas mark 6')).toBe(200);
  expect(findTempC('add 300 calories')).toBeNull();
});

test('detects what the protein is', () => {
  expect(detectProteinType({ title: 'Pan-Seared Ribeye Steak' }).id).toBe('steak');
  expect(detectProteinType({ title: 'Lemon chicken' }).id).toBe('chicken-breast');
  expect(detectProteinType({ title: 'Honey chicken drumsticks' }).id).toBe('chicken-thigh');
  expect(detectProteinType({ title: 'Roast chicken' }).id).toBe('whole-chicken');
  expect(detectProteinType({ title: 'Beef burgers' }).id).toBe('burger');
  expect(detectProteinType({ title: 'Pork chops with apples' }).id).toBe('pork-chop');
  expect(detectProteinType({ title: 'Pulled pork', ingredients: [{ item: 'pork shoulder' }] })).toBeNull();
  expect(detectProteinType({ title: 'Tomato soup', ingredients: [{ item: 'tomatoes' }] })).toBeNull();
  expect(detectProteinType({ title: 'Roast salmon' }).id).toBe('salmon');
  expect(detectProteinType({ title: 'Traybake', ingredients: [{ item: 'salmon fillets' }] }).id).toBe('salmon');
});

test('steak plan follows thickness, doneness and method', () => {
  const t = proteinTypeById('steak');
  const mr = proteinPlan(t, { sizeId: '3', doneId: 'medium-rare', method: 'pan' });
  const well = proteinPlan(t, { sizeId: '3', doneId: 'well', method: 'pan' });
  const thick = proteinPlan(t, { sizeId: '5', doneId: 'medium-rare', method: 'pan' });
  expect(mr.internalC).toBe(57); expect(well.internalC).toBe(71);
  expect(mr.stages[0].perSide).toBe(true);
  expect(mr.stages[0].seconds).toBe(195 + 0 || 195);           // (1+3)*0.8 = 3.2 min -> 195 s
  expect(well.stages[0].seconds).toBeGreaterThan(mr.stages[0].seconds);
  expect(thick.stages.length).toBe(2);                           // thick cuts: sear then finish in the oven
  expect(mr.safety).toMatch(/63°C/);                             // rarer than guidance: safety note
  expect(proteinPlan(t, { sizeId: '3', doneId: 'medium', method: 'pan' }).safety).toBeNull();
  const af = proteinPlan(t, { sizeId: '3', doneId: 'medium', method: 'airfryer' });
  expect(af.tempC).toBe(200); expect(af.stages[0].halfway).toBe(true);
});

test('chicken has no doneness choice but size and method change the plan', () => {
  const t = proteinTypeById('chicken-breast');
  expect(t.doneness).toBeUndefined();
  const small = proteinPlan(t, { sizeId: 's', method: 'oven' }); const large = proteinPlan(t, { sizeId: 'l', method: 'oven' });
  expect(small.internalC).toBe(74); expect(large.stages[0].seconds).toBeGreaterThan(small.stages[0].seconds);
  expect(proteinPlan(t, { sizeId: 'm', method: 'airfryer' }).tempC).toBe(190);
  expect(proteinPlan(t, { sizeId: 'm', method: 'nonsense' }).method).toBe('pan');   // unknown method -> first allowed
});

test('roast joints scale with weight and doneness', () => {
  const t = proteinTypeById('joint-beef');
  const a = proteinPlan(t, { sizeId: '1', doneId: 'medium', method: 'oven' }); const b = proteinPlan(t, { sizeId: '2', doneId: 'medium', method: 'oven' });
  expect(b.stages[0].seconds).toBeGreaterThan(a.stages[0].seconds);
  expect(a.stages[0].seconds).toBe(Math.round(((1 / 0.45) * 25 + 25) * 60 / 60) * 60);
  expect(proteinTypeById('whole-chicken') && proteinPlan(proteinTypeById('whole-chicken'), { sizeId: '1.5', method: 'oven' }).stages[0].seconds).toBe(Math.round(((1.5 / 0.45) * 20 + 20)) * 60);
});

test('every protein type produces a plan for every size and method', () => {
  const { PROTEIN_TYPES } = require('./cookingTools');
  for (const t of PROTEIN_TYPES) for (const sz of t.sizes) for (const m of t.methods) for (const d of (t.doneness || [null])) {
    const p = proteinPlan(t, { sizeId: sz.id, doneId: d && d.id, method: m });
    expect(p.stages.length).toBeGreaterThan(0); expect(p.stages.every((s) => s.seconds >= 30)).toBe(true); expect(p.internalC).toBeGreaterThan(40);
  }
});

test('only protein-cooking steps get the protein timers', () => {
  const t = proteinTypeById('steak');
  expect(stepCooksProtein('Sear the steak for 4 minutes per side.', t)).toBe(true);
  expect(stepCooksProtein('Soften the onions for 5 minutes.', t)).toBe(false);
  expect(stepCooksProtein('Rest for 5 minutes.', t)).toBe(false);
});

test('air fryer conversions', () => {
  const o = airFryerStep('Roast in the oven at 200°C for 20 minutes.');
  expect(o.kind).toBe('cook'); expect(o.tempC).toBe(180); expect(o.seconds).toBe(900); expect(o.halfway).toBe(450);
  const crispy = airFryerStep('Roast in the oven at 200°C for 20 minutes.', { crisp: 'crispy', tempOffset: 5 });
  expect(crispy.tempC).toBe(195); expect(crispy.seconds).toBeGreaterThan(900);
  expect(airFryerStep('Simmer the sauce for 10 minutes.')).toBeNull();
  expect(airFryerStep('Preheat the oven to 220°C.').kind).toBe('preheat');
  expect(airFryerStep('Deep fry the wings for 10 minutes.').tempC).toBe(190);
  expect(airFryerStep('Roast for 25 minutes', {}, { ovenC: 180 }).tempC).toBe(160);
  expect(airFryerStep('Air fry at 190°C for 12 minutes.').seconds).toBe(720);
  expect(airFryerStep('Roast at 400°C for 10 minutes', { tempOffset: 20 }).tempC).toBe(200);   // capped at 200
});

test('which recipes get an air fryer option', () => {
  expect(airFryerSuitable({ title: 'Roast potatoes', steps: ['Preheat the oven to 220°C.', 'Roast for 40 minutes until crisp.'] })).toBe(true);
  expect(airFryerSuitable({ title: 'Tomato soup', steps: ['Simmer for 20 minutes.', 'Blend.'] })).toBe(false);
  expect(airFryerSuitable({ title: 'Salad', steps: ['Toss everything together.'] })).toBe(false);
});

test('clock format', () => { expect(fmtClock(65)).toBe('1:05'); expect(fmtClock(3725)).toBe('1:02:05'); });

describe('detectProteinType skips dishes the plan does not fit', () => {
  const { detectProteinType } = require('./cookingTools');
  test('braised lamb shanks, stews and curries get no steak-style plan', () => {
    expect(detectProteinType({ title: 'Vietnamese lamb shanks with sweet potatoes', ingredients: [{ item: 'Lamb' }] })).toBeNull();
    expect(detectProteinType({ title: 'Beef stew', ingredients: [{ item: 'beef' }] })).toBeNull();
    expect(detectProteinType({ title: 'Chicken curry', ingredients: [{ item: 'chicken breast' }] })).toBeNull();
  });
  test('a plain steak still gets one', () => {
    expect(detectProteinType({ title: 'Pan-seared ribeye steak', ingredients: [] })?.id).toBe('steak');
  });
});
