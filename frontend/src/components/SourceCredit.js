import React from 'react';

const CC_BY = 'https://creativecommons.org/licenses/by/3.0/';
const CC_BY_SA = 'https://creativecommons.org/licenses/by-sa/4.0/';

// Works out where a recipe/photo came from so we can credit it (required by TheMealDB and Foodista's CC BY licence).
export function sourceInfo(recipe) {
  const url = recipe?.source_url || '';
  let host = '';
  try { host = new URL(url).hostname.replace(/^www\./, ''); } catch (e) { /* not a URL */ }
  const img = recipe?.image || '';
  const info = { host, url, name: host, note: null, noteUrl: null, photo: null, photoUrl: null };
  if (host.includes('themealdb.com')) { info.name = 'TheMealDB'; info.url = 'https://www.themealdb.com'; }
  else if (host.includes('foodista.com')) { info.name = 'Foodista'; info.note = 'CC BY 3.0'; info.noteUrl = CC_BY; }
  else if (host.includes('wikibooks.org')) { info.name = 'Wikibooks Cookbook'; info.note = 'CC BY-SA 4.0'; info.noteUrl = CC_BY_SA; info.historyUrl = recipe?.source_history_url || null; }
  else if (host.includes('youtube') || host.includes('youtu.be')) { info.name = 'YouTube'; }

  if (recipe?.image_attribution) {
    info.photo = recipe.image_attribution;
  } else if (img.includes('themealdb.com')) {
    info.photo = 'TheMealDB'; info.photoUrl = 'https://www.themealdb.com';
  } else if (img.includes('spoonacular.com')) {
    info.photo = 'spoonacular'; info.photoUrl = 'https://spoonacular.com';
  } else if (recipe?.image_source === 'ai-generated') {
    info.photo = 'AI-generated illustration';
  }
  return info;
}

const SourceCredit = ({ recipe }) => {
  const s = sourceInfo(recipe);
  if (!s.name && !s.photo) return null;
  return (
    <div className="mt-8 pt-8 border-t border-zinc-800" data-testid="source-credit">
      <h3 className="font-semibold text-zinc-100 mb-3">Source</h3>
      {s.name && (
        <p className="text-sm text-zinc-400">
          Recipe from{' '}
          <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-orange-500 hover:text-orange-400 underline">{s.name}</a>
          {s.note && (
            <> · licensed <a href={s.noteUrl} target="_blank" rel="noopener noreferrer" className="text-orange-500 hover:text-orange-400 underline">{s.note}</a></>
          )}
          {s.historyUrl && (
            <> · <a href={s.historyUrl} target="_blank" rel="noopener noreferrer" className="text-orange-500 hover:text-orange-400 underline">Authors</a></>
          )}
          {s.url && s.url !== `https://www.${s.host}` && s.host && !['TheMealDB'].includes(s.name) && (
            <> · <a href={recipe.source_url} target="_blank" rel="noopener noreferrer" className="text-orange-500 hover:text-orange-400 underline">View original recipe</a></>
          )}
        </p>
      )}
      {s.photo && (
        <p className="text-xs text-zinc-500 mt-1">
          Photo: {s.photoUrl ? <a href={s.photoUrl} target="_blank" rel="noopener noreferrer" className="underline">{s.photo}</a> : s.photo}
        </p>
      )}
    </div>
  );
};

export default SourceCredit;
