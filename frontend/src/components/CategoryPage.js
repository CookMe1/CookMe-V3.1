import React, { useState, useEffect, useCallback } from 'react';
import { Search, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Input } from './ui/input';
import { Card, CardContent } from './ui/card';
import RecipeCard from './RecipeCard';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const PAGE = 24;
const tagsOf = (r) => (r.tags || []).map((t) => String(t).toLowerCase());

/**
 * One layout for the Quick / Student / Budget / One Pot / Air Fryer pages.
 * config: { type, title, subtitle, Icon, gradient (tailwind classes), accent ('orange'|...), tipsTitle, tips[],
 *           searchLabel, emptyLabel, userMatch(recipe), chips: [{label, test(recipe)}] }
 */
const CategoryPage = ({ config }) => {
  const { type, title, subtitle, Icon, gradient, tipsTitle, tips, searchLabel, emptyLabel, userMatch, chips = [], endpoint, hideMine } = config;
  const base = endpoint || `/api/recipes/type/${type}`;
  const [searchQuery, setSearchQuery] = useState('');
  const [chip, setChip] = useState(0);
  const [mine, setMine] = useState([]);
  const [shared, setShared] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const token = () => localStorage.getItem('token') || sessionStorage.getItem('token');
  const headers = useCallback(() => ({ Authorization: `Bearer ${token()}` }), []);

  useEffect(() => {
    let live = true;
    (async () => {
      setLoading(true);
      try {
        const [typeRes, userRes] = await Promise.all([
          fetch(`${API_URL}${base}?limit=${PAGE}&skip=0`, { headers: headers() }),
          hideMine ? Promise.resolve({ ok: false }) : fetch(`${API_URL}/api/recipes?limit=100`, { headers: headers() }),
        ]);
        const t = typeRes.ok ? await typeRes.json() : { recipes: [], total: 0 };
        const u = userRes.ok ? await userRes.json() : [];
        if (!live) return;
        setShared(t.recipes || []);
        setTotal(t.total || (t.recipes || []).length);
        setMine((Array.isArray(u) ? u : u.recipes || []).filter(userMatch));
      } catch (e) { console.error(e); }
      if (live) setLoading(false);
    })();
    return () => { live = false; };
  }, [type, base, hideMine, headers, userMatch]);

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const res = await fetch(`${API_URL}${base}?limit=${PAGE}&skip=${shared.length}`, { headers: headers() });
      if (res.ok) {
        const t = await res.json();
        setShared((prev) => [...prev, ...(t.recipes || [])]);
        setTotal(t.total || total);
      }
    } catch (e) { console.error(e); }
    setLoadingMore(false);
  };

  const seen = new Set();
  const all = [...mine, ...shared].filter((r) => {
    const k = (r.title || '').toLowerCase();
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
  const q = searchQuery.trim().toLowerCase();
  const filtered = all.filter((r) =>
    (!q || (r.title || '').toLowerCase().includes(q) || (r.description || '').toLowerCase().includes(q) || tagsOf(r).some((t) => t.includes(q))) &&
    (chips[chip] ? chips[chip].test(r) : true));
  const more = shared.length < total;

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0" data-testid={`category-${type}`}>
      <div className={`bg-gradient-to-br ${gradient}`}>
        <div className="max-w-7xl mx-auto px-6 md:px-8 py-8 md:py-12 flex items-center gap-4">
          <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-black/25 flex items-center justify-center shrink-0">
            <Icon className="w-7 h-7 md:w-8 md:h-8 text-white" />
          </div>
          <div>
            <h1 className="font-display text-3xl md:text-5xl font-bold text-white">{title}</h1>
            <p className="text-white/80 mt-1 text-sm md:text-base">{subtitle}</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 md:px-8 py-6">
        <Card className="mb-6 bg-zinc-900 border-zinc-800">
          <CardContent className="pt-5">
            <h3 className="font-semibold text-orange-400 mb-3">{tipsTitle}</h3>
            <ul className="grid md:grid-cols-2 gap-2 text-sm text-zinc-400">
              {tips.map((t) => <li key={t}>• {t}</li>)}
            </ul>
          </CardContent>
        </Card>

        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
          <Input type="text" placeholder={searchLabel} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-zinc-900 border-zinc-800 text-zinc-100" />
        </div>

        {chips.length > 1 && (
          <div className="flex gap-2 overflow-x-auto pb-2 mb-4" data-testid="category-chips">
            {chips.map((c, i) => (
              <button key={c.label} onClick={() => setChip(i)}
                className={`shrink-0 px-3 py-1.5 rounded-full text-sm border transition-colors ${i === chip ? 'bg-orange-600 border-orange-600 text-white' : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'}`}>
                {c.label}
              </button>
            ))}
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => <div key={i} className="h-64 bg-zinc-800 rounded-xl animate-pulse" />)}
          </div>
        ) : filtered.length > 0 ? (
          <>
            <p className="text-xs text-zinc-500 mb-3">{q || chip ? `${filtered.length} shown` : `Showing ${all.length}${more ? ` of ${total + mine.length}` : ''}`}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filtered.map((recipe, i) => (
                <div key={recipe.recipe_id || recipe.community_recipe_id || i}>
                  <RecipeCard recipe={recipe} />
                </div>
              ))}
            </div>
            {more && (
              <div className="flex justify-center mt-8">
                <button onClick={loadMore} disabled={loadingMore} data-testid="load-more"
                  className="px-6 py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-sm font-medium flex items-center gap-2 disabled:opacity-60">
                  {loadingMore && <Loader2 className="w-4 h-4 animate-spin" />} Show more recipes
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-16">
            <p className="text-zinc-400 text-lg">{emptyLabel}</p>
            {more && (q || chip) ? (
              <button onClick={loadMore} className="text-orange-500 hover:text-orange-400 text-sm mt-2">Load more recipes to search</button>
            ) : (
              <Link to="/add-recipe" className="text-orange-500 hover:text-orange-400 text-sm mt-2 inline-block">Add your own</Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CategoryPage;
