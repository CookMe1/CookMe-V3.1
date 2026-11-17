import React, { useState, useEffect } from 'react';
import { Zap, Search } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import RecipeCard from '../components/RecipeCard';
import { Link } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const InstapotRecipes = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  useEffect(() => {
    const fetchRecipes = async () => {
      setLoading(true);
      try {
        const token = getToken();
        const [communityRes, userRes] = await Promise.all([
          fetch(`${API_URL}/api/recipes/type/instapot?limit=60`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          fetch(`${API_URL}/api/recipes?limit=100`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);
        const communityData = communityRes.ok ? await communityRes.json() : { recipes: [] };
        const userData = userRes.ok ? await userRes.json() : { recipes: [] };
        const userInstapot = (userData.recipes || []).filter(r =>
          r.category === 'instapot' ||
          r.tags?.some(t => ['instant pot','instapot','one pot','pressure cooker','slow cooker','crockpot'].includes(t.toLowerCase()))
        );
        const combined = [...userInstapot, ...(communityData.recipes || [])];
        const seen = new Set();
        setRecipes(combined.filter(r => {
          const k = (r.title || '').toLowerCase();
          if (seen.has(k)) return false;
          seen.add(k); return true;
        }));
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    fetchRecipes();
  }, []);

  const filtered = recipes.filter(r =>
    (r.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
    (r.description || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      <div className="relative h-[30vh] min-h-[250px]">
        <img src="https://images.unsplash.com/photo-1547592180-85f173990554?w=1920&h=600&fit=crop"
          alt="Instapot Recipes" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 gradient-overlay" />
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-7xl mx-auto flex items-end gap-4">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">Instapot / One Pot</h1>
              <p className="text-zinc-400 mt-1">Easy cleanup with delicious one-pot wonders</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 md:px-8 py-8">
        <Card className="mb-8 bg-purple-600/10 border-purple-600/30">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-purple-400 mb-3">🍲 One-Pot Cooking Tips</h3>
            <ul className="grid md:grid-cols-2 gap-2 text-sm text-zinc-400">
              <li>• Layer ingredients properly for even cooking</li>
              <li>• Use the sauté function to build flavour first</li>
              <li>• Don't overfill — respect the max line</li>
              <li>• Let pressure release naturally for tender meats</li>
            </ul>
          </CardContent>
        </Card>

        <div className="relative mb-8">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
          <Input type="text" placeholder="Search one-pot recipes..." value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="pl-10 bg-zinc-900 border-zinc-800 text-zinc-100" />
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => <div key={i} className="h-64 bg-zinc-800 rounded-xl animate-pulse" />)}
          </div>
        ) : filtered.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filtered.map((recipe, i) => (
              <div key={recipe.recipe_id || recipe.community_recipe_id || i}
                className="animate-fade-in" style={{ animationDelay: `${i * 0.05}s` }}>
                <RecipeCard recipe={recipe} />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-zinc-400 text-lg">No one-pot recipes found</p>
            <Link to="/add-recipe" className="text-orange-500 hover:text-orange-400 text-sm mt-2 inline-block">
              Add a one-pot recipe
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default InstapotRecipes;
