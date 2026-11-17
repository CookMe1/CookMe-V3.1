import React, { useState, useEffect } from 'react';
import { Search, Leaf } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import RecipeCard from '../components/RecipeCard';
import { useLanguage } from '../context/LanguageContext';
import { Link } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BudgetRecipes = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const { currency, seasonalProduce, language } = useLanguage();

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  useEffect(() => {
    const fetchBudgetRecipes = async () => {
      setLoading(true);
      try {
        const token = getToken();
        // Fetch from community DB first (budget/cheap category), then user's own
        const [communityRes, userRes] = await Promise.all([
          fetch(`${API_URL}/api/recipes/type/budget?limit=60`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          fetch(`${API_URL}/api/recipes?limit=100`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);

        const communityData = communityRes.ok ? await communityRes.json() : { recipes: [] };
        const userData = userRes.ok ? await userRes.json() : { recipes: [] };

        // Combine: user's budget recipes first, then community
        const userBudget = (userData.recipes || []).filter(r =>
          r.category === 'budget' || r.tags?.some(t => t.toLowerCase().includes('budget') || t.toLowerCase().includes('cheap'))
        );
        const combined = [...userBudget, ...(communityData.recipes || [])];

        // Deduplicate by title
        const seen = new Set();
        const unique = combined.filter(r => {
          const key = (r.title || '').toLowerCase();
          if (seen.has(key)) return false;
          seen.add(key);
          return true;
        });

        setRecipes(unique);
      } catch (e) {
        console.error('Failed to fetch budget recipes', e);
      }
      setLoading(false);
    };
    fetchBudgetRecipes();
  }, []);

  const filteredRecipes = recipes.filter(recipe =>
    (recipe.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (recipe.description || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Get 4 in-season items for the tip
  const seasonalTip = seasonalProduce.slice(0, 4).join(', ');

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Hero Header */}
      <div className="relative h-[30vh] min-h-[250px]">
        <img
          src="https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=1920&h=600&fit=crop"
          alt="Budget Recipes"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-overlay" />
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-7xl mx-auto flex items-end gap-4">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <span className="text-2xl font-bold text-white">{currency.symbol}</span>
            </div>
            <div>
              <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">
                Budget Friendly
              </h1>
              <p className="text-zinc-400 mt-1">Delicious meals that won't break the bank</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 md:px-8 py-8">
        {/* Tips Card */}
        <Card className="mb-8 bg-emerald-600/10 border-emerald-600/30">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-emerald-400 mb-3">💡 Money-Saving Tips</h3>
            <ul className="grid md:grid-cols-2 gap-2 text-sm text-zinc-400">
              {seasonalTip ? (
                <li className="flex items-center gap-2">
                  <Leaf className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  In season now: <span className="text-emerald-400">{seasonalTip}</span>
                </li>
              ) : (
                <li>• Buy seasonal vegetables for better prices</li>
              )}
              <li>• Use pantry staples like rice, pasta, and beans</li>
              <li>• Cook in bulk and freeze portions</li>
              <li>• Check your pantry before shopping — use what you have first</li>
            </ul>
          </CardContent>
        </Card>

        {/* Search */}
        <div className="relative mb-8">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
          <Input
            type="text"
            placeholder="Search budget recipes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-zinc-900 border-zinc-800 text-zinc-100"
          />
        </div>

        {/* Recipes Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-64 bg-zinc-800 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : filteredRecipes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredRecipes.map((recipe, index) => (
              <div key={recipe.recipe_id || recipe.community_recipe_id || index}
                   className="animate-fade-in"
                   style={{ animationDelay: `${index * 0.05}s` }}>
                <RecipeCard recipe={recipe} />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-zinc-400 text-lg">No budget recipes found</p>
            <p className="text-zinc-600 mt-2">Try adjusting your search or</p>
            <Link to="/add-recipe" className="text-orange-500 hover:text-orange-400 text-sm mt-2 inline-block">
              add your own budget recipe
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default BudgetRecipes;
