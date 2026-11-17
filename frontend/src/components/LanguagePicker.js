import React, { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { Check, Search } from 'lucide-react';

/**
 * LanguagePicker
 * Shown once on first app startup (when no language is stored).
 * Also accessible from Profile settings.
 *
 * Props:
 *   onDismiss — called when user confirms their choice
 *   isModal   — true = shown as full-screen overlay, false = inline settings panel
 */
const LanguagePicker = ({ onDismiss, isModal = true }) => {
  const { language, languages, saveLanguage, loadingLanguages } = useLanguage();
  const [selected, setSelected] = useState(language);
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);

  const filtered = languages.filter(l =>
    l.name.toLowerCase().includes(search.toLowerCase()) ||
    l.native.toLowerCase().includes(search.toLowerCase())
  );

  const handleConfirm = async () => {
    setSaving(true);
    await saveLanguage(selected.code, selected.name);
    setSaving(false);
    if (onDismiss) onDismiss();
  };

  const content = (
    <div className={isModal ? 'w-full max-w-md' : 'w-full'}>
      {isModal && (
        <div className="text-center mb-4">
          <div className="text-4xl mb-2">🌍</div>
          <h2 className="text-xl font-bold text-zinc-100 mb-1">Choose your language</h2>
          <p className="text-zinc-400 text-sm">
            All recipes will be translated to your preferred language when imported.
            You can change this anytime in Profile settings.
          </p>
        </div>
      )}

      {!isModal && (
        <h3 className="text-lg font-semibold text-zinc-100 mb-4">Recipe Language</h3>
      )}

      {/* Search */}
      <div className="relative mb-3">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search languages..."
          className="w-full pl-10 pr-4 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-100 text-sm placeholder:text-zinc-600 outline-none focus:border-orange-500"
        />
      </div>

      {/* Language list — scrolls internally, never pushes button off screen */}
      <div className="overflow-y-auto space-y-1" style={{ maxHeight: '40vh' }}>
        {loadingLanguages ? (
          <div className="text-center py-8 text-zinc-500 text-sm">Loading languages...</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-8 text-zinc-500 text-sm">No languages found</div>
        ) : (
          filtered.map(lang => (
            <button
              key={lang.code}
              onClick={() => setSelected({ code: lang.code, name: lang.name })}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                selected.code === lang.code
                  ? 'bg-orange-600/20 border border-orange-600/50'
                  : 'hover:bg-zinc-800 border border-transparent'
              }`}
            >
              <span className="text-xl w-8 text-center">{lang.flag}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-zinc-100">{lang.name}</div>
                <div className="text-xs text-zinc-500">{lang.native}</div>
              </div>
              {selected.code === lang.code && (
                <Check className="w-4 h-4 text-orange-500 shrink-0" />
              )}
            </button>
          ))
        )}
      </div>

      {/* Confirm button — always visible, never scrolled away */}
      <button
        onClick={handleConfirm}
        disabled={saving}
        className="mt-4 w-full py-3 bg-orange-600 hover:bg-orange-700 disabled:bg-zinc-700 text-white font-semibold rounded-xl transition-colors text-sm"
      >
        {saving ? 'Saving...' : isModal ? `Continue in ${selected.name}` : 'Save Language'}
      </button>

      {isModal && selected.code !== 'en' && (
        <p className="mt-2 text-center text-xs text-zinc-600">
          Recipes imported in any language will be translated to {selected.name}
        </p>
      )}
    </div>
  );

  if (!isModal) return <div className="py-4">{content}</div>;

  return (
    <div className="fixed inset-0 bg-[#09090b] z-[9999] flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 w-full max-w-md max-h-[90vh] flex flex-col">
        {content}
      </div>
    </div>
  );
};

export default LanguagePicker;
