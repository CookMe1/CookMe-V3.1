import React, { useState, useEffect, useCallback } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { Input } from '../components/ui/input';
import RecipeCard from '../components/RecipeCard';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const LIMIT = 24;
const CUISINES = [
  'british', 'american', 'italian', 'spanish', 'french', 'greek', 'mediterranean', 'middle_eastern', 'indian',
  'chinese', 'japanese', 'korean', 'thai', 'vietnamese', 'mexican', 'caribbean', 'african', 'german',
  'south_asian', 'southeast_asian', 'asian', 'latin_american', 'european', 'turkish', 'moroccan', 'irish', 'polish', 'russian',
];
const label = (c) => c.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());

const Pill = ({ active, onClick, children, testid }) => (
  <button
    type="button"
    onClick={onClick}
    data-testid={testid}
    className={`px-3 h-9 rounded-full text-sm border transition-colors ${
      active ? 'bg-orange-600 border-orange-600 text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-300 hover:border-zinc-600'
    }`}
  >
    {children}
  </button>
);

const SearchRecipes = () => {
  const [q, setQ] = useState('');
  const [ingredientInput, setIngredientInput] = useState('');
  const [ingredients, setIngredients] = useState([]);
  const [diet, setDiet] = useState('');
  const [cuisine, setCuisine] = useState('');
  const [quick, setQuick] = useState(false);
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const run = useCallback(async (skip, append) => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token');
      const params = new URLSearchParams({ limit: LIMIT, skip });
      if (q.trim()) params.set('q', q.trim());
      if (ingredients.length) params.set('ingredients', ingredients.join(','));
      if (diet) params.set('diet', diet);
      if (cuisine) params.set('cuisine', cuisine);
      if (quick) params.set('quick', 'true');
      const res = await fetch(`${API_URL}/api/recipes/search?${params}`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error('Search failed');
      const data = await res.json();
      setResults((prev) => (append ? [...prev, ...(data.recipes || [])] : data.recipes || []));
      setTotal(data.total || 0);
    } catch (e) {
      setError('Could not load recipes. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [q, ingredients, diet, cuisine, quick]);

  // Re-run (debounced) whenever a filter changes
  useEffect(() => {
    const t = setTimeout(() => run(0, false), 300);
    return () => clearTimeout(t);
  }, [run]);

  const addIngredient = () => {
    const parts = ingredientInput.split(',').map((x) => x.trim().toLowerCase()).filter(Boolean);
    if (parts.length) setIngredients((prev) => Array.from(new Set([...prev, ...parts])).slice(0, 8));
    setIngredientInput('');
  };

  const anyFilter = q || ingredients.length || diet || cuisine || quick;
  const clear = () => { setQ(''); setIngredients([]); setDiet(''); setCuisine(''); setQuick(false); };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <h1 className="font-display text-3xl md:text-4xl font-bold mb-6">Find a recipe</h1>

        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search by name, e.g. curry, soup, pancakes"
            className="pl-10 bg-zinc-900 border-zinc-800 text-zinc-100"
            data-testid="search-input"
          />
        </div>

        <div className="mb-4">
          <div className="flex gap-2">
            <Input
              value={ingredientInput}
              onChange={(e) => setIngredientInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); addIngredient(); } }}
              placeholder="Add ingredients you want, e.g. chicken, rice"
              className="bg-zinc-900 border-zinc-800 text-zinc-100"
              data-testid="ingredient-input"
            />
            <button type="button" onClick={addIngredient} className="px-4 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-sm">Add</button>
          </div>
          {ingredients.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {ingredients.map((ing) => (
                <span key={ing} className="inline-flex items-center gap-1 pl-3 pr-1 h-8 rounded-full bg-orange-600/20 border border-orange-600/40 text-orange-300 text-sm">
                  {ing}
                  <button type="button" aria-label={`Remove ${ing}`} onClick={() => setIngredients((p) => p.filter((x) => x !== ing))} className="p-1 hover:text-white">
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-2 mb-3">
          <Pill active={quick} onClick={() => setQuick(!quick)} testid="filter-quick">Under 30 min</Pill>
          <Pill active={diet === 'vegetarian'} onClick={() => setDiet(diet === 'vegetarian' ? '' : 'vegetarian')} testid="filter-vegetarian">Vegetarian</Pill>
          <Pill active={diet === 'vegan'} onClick={() => setDiet(diet === 'vegan' ? '' : 'vegan')} testid="filter-vegan">Vegan</Pill>
          <select
            value={cuisine}
            onChange={(e) => setCuisine(e.target.value)}
            className="h-9 rounded-full bg-zinc-900 border border-zinc-800 text-sm text-zinc-300 px-3"
            data-testid="filter-cuisine"
          >
            <option value="">Any cuisine</option>
            {CUISINES.map((c) => <option key={c} value={c}>{label(c)}</option>)}
          </select>
          {anyFilter && (
            <button type="button" onClick={clear} className="text-sm text-zinc-400 hover:text-orange-400 px-2" data-testid="clear-filters">Clear all</button>
          )}
        </div>
        <p className="text-xs text-zinc-600 mb-6">Vegetarian and vegan are worked out from the ingredient list. Always check labels if you have allergies.</p>

        {error && <p className="text-red-400 mb-4">{error}</p>}

        {loading && results.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => <div key={i} className="h-64 bg-zinc-800 rounded-xl animate-pulse" />)}
          </div>
        ) : results.length > 0 ? (
          <>
            <p className="text-sm text-zinc-500 mb-4" data-testid="result-count">{total.toLocaleString()} recipe{total === 1 ? '' : 's'}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {results.map((r) => <RecipeCard key={r.recipe_id} recipe={r} />)}
            </div>
            {results.length < total && (
              <div className="text-center mt-8">
                <button
                  type="button"
                  onClick={() => run(results.length, true)}
                  disabled={loading}
                  className="px-6 h-11 rounded-lg bg-zinc-800 hover:bg-zinc-700 inline-flex items-center gap-2"
                  data-testid="load-more"
                >
                  {loading && <Loader2 className="w-4 h-4 animate-spin" />} Show more
                </button>
              </div>
            )}
          </>
        ) : (
          !loading && (
            <div className="text-center py-16" data-testid="no-results">
              <p className="text-zinc-300 text-lg">No recipes match</p>
              <p className="text-zinc-500 text-sm mt-1">Try removing a filter or an ingredient.</p>
              {anyFilter && <button type="button" onClick={clear} className="mt-4 text-orange-500 hover:text-orange-400 text-sm">Clear all filters</button>}
            </div>
          )
        )}
      </div>
    </div>
  );
};

export default SearchRecipes;
