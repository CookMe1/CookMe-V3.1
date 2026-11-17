import React, { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';

/**
 * DietaryDefaultsPrompt
 * Shown once after a user selects a non-default language that has
 * regional dietary suggestions (halal, vegetarian, kosher).
 * Saves the user's choice to localStorage.
 */
const DietaryDefaultsPrompt = ({ onDismiss }) => {
  const { language, dietaryDefaults } = useLanguage();
  const [saving, setSaving] = useState(false);

  // Build the list of suggestions to show
  const suggestions = [];
  if (dietaryDefaults.suggestHalal)      suggestions.push({ key: 'halal',       label: 'Halal',      emoji: '🥩', desc: 'Filter recipes to show halal-friendly meals only' });
  if (dietaryDefaults.suggestVegetarian) suggestions.push({ key: 'vegetarian',  label: 'Vegetarian', emoji: '🥗', desc: 'Filter recipes to show vegetarian meals only' });
  if (dietaryDefaults.suggestKosher)     suggestions.push({ key: 'kosher',      label: 'Kosher',     emoji: '✡️',  desc: 'Filter recipes to show kosher-friendly meals only' });

  // All hooks must be called before any return — React rule
  const [enabled, setEnabled] = useState(() =>
    Object.fromEntries(suggestions.map(s => [s.key, true]))
  );

  // Now safe to do early return
  if (suggestions.length === 0) {
    onDismiss?.();
    return null;
  }

  const handleSave = async () => {
    setSaving(true);
    const prefs = { ...enabled, dismissed: true, language: language.code };
    localStorage.setItem('cookme_dietary_prefs', JSON.stringify(prefs));
    setSaving(false);
    onDismiss?.();
  };

  const handleSkip = () => {
    localStorage.setItem('cookme_dietary_prefs', JSON.stringify({
      dismissed: true, language: language.code
    }));
    onDismiss?.();
  };

  return (
    <div className="fixed inset-0 bg-[#09090b] z-[9998] flex items-center justify-center p-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 w-full max-w-sm">
          <div className="text-center mb-6">
            <div className="text-4xl mb-3">🍽️</div>
            <h2 className="text-xl font-bold text-zinc-100 mb-2">Dietary Preferences</h2>
            <p className="text-zinc-400 text-sm">
              Based on your language preference, would you like to enable these filters?
              You can change these anytime in your profile.
            </p>
          </div>

          <div className="space-y-3 mb-6">
            {suggestions.map(s => (
              <button
                key={s.key}
                onClick={() => setEnabled(prev => ({ ...prev, [s.key]: !prev[s.key] }))}
                className={`w-full flex items-center gap-3 p-4 rounded-xl border transition-colors text-left ${
                  enabled[s.key]
                    ? 'bg-orange-600/20 border-orange-600/50'
                    : 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                }`}
              >
                <span className="text-2xl">{s.emoji}</span>
                <div className="flex-1">
                  <p className="font-medium text-zinc-100">{s.label}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">{s.desc}</p>
                </div>
                <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ${
                  enabled[s.key] ? 'border-orange-500 bg-orange-500' : 'border-zinc-600'
                }`}>
                  {enabled[s.key] && <span className="text-white text-xs">✓</span>}
                </div>
              </button>
            ))}
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full py-3 bg-orange-600 hover:bg-orange-700 disabled:bg-zinc-700 text-white font-semibold rounded-xl transition-colors text-sm mb-3"
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
          <button
            onClick={handleSkip}
            className="w-full py-2 text-zinc-500 hover:text-zinc-400 text-sm transition-colors"
          >
            Skip — show all recipes
          </button>
        </div>
    </div>
  );
};

export default DietaryDefaultsPrompt;
