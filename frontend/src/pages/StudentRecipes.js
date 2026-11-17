import React, { useState, useEffect } from 'react';
import { GraduationCap, Search } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import RecipeCard from '../components/RecipeCard';
import { Link } from 'react-router-dom';
import { useLanguage } from '../context/LanguageContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const StudentRecipes = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const { currency } = useLanguage();

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  useEffect(() => {
    const fetchRecipes = async () => {
      setLoading(true);
      try {
        const token = getToken();
        const [communityRes, userRes] = await Promise.all([
          fetch(`${API_URL}/api/recipes/type/student?limit=60`, {
            headers: { Authorization: `Bearer ${token}` }
          }),
          fetch(`${API_URL}/api/recipes?limit=100`, {
            headers: { Authorization: `Bearer ${token}` }
          })
        ]);
        const communityData = communityRes.ok ? await communityRes.json() : { recipes: [] };
        const userData = userRes.ok ? await userRes.json() : [];
        const userStudent = (Array.isArray(userData) ? userData : (userData.recipes || [])).filter(r =>
          r.category === 'student' ||
          r.tags?.some(t => ['student','easy','beginner','simple','budget'].includes(t.toLowerCase()))
        );
        const combined = [...userStudent, ...(communityData.recipes || [])];
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
        <img src="https://images.unsplash.com/photo-1543352634-a1c51d9f1fa7?w=1920&h=600&fit=crop"
          alt="Student Recipes" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 gradient-overlay" />
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-7xl mx-auto flex items-end gap-4">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <GraduationCap className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">Student Meals</h1>
              <p className="text-zinc-400 mt-1">Quick, easy, affordable recipes for busy students</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 md:px-8 py-8">
        <Card className="mb-8 bg-blue-600/10 border-blue-600/30">
          <CardContent className="pt-6">
            <h3 className="font-semibold text-blue-400 mb-3">🎓 Student Cooking Tips</h3>
            <ul className="grid md:grid-cols-2 gap-2 text-sm text-zinc-400">
              <li>• Keep basic spices on hand for flavour variety</li>
              <li>• Meal prep on weekends to save time</li>
              <li>• Learn to make versatile sauces — pasta, stir-fry, curry</li>
              <li>• Eggs are your best friend: cheap, fast, endlessly versatile</li>
            </ul>
          </CardContent>
        </Card>

        <div className="relative mb-8">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
          <Input type="text" placeholder="Search student recipes..." value={searchQuery}
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
            <p className="text-zinc-400 text-lg">No student recipes found</p>
            <Link to="/add-recipe" className="text-orange-500 hover:text-orange-400 text-sm mt-2 inline-block">
              Add a student recipe
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default StudentRecipes;
