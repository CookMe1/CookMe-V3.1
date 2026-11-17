import React, { useState, useEffect } from 'react';
import { Plus, Trash2, BookOpen, Loader2, ChefHat } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import RecipeCard from '../components/RecipeCard';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const COOKBOOK_COVERS = [
  'https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=400',
  'https://images.unsplash.com/photo-1543339308-43e59d6b73a6?w=400',
  'https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=400',
  'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=400',
  'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400',
  'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400',
];

const Cookbooks = () => {
  const [cookbooks, setCookbooks] = useState([]);
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);
  const [activeBook, setActiveBook] = useState(null); // null = list view
  const [showAssignModal, setShowAssignModal] = useState(null); // recipeId

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const token = getToken();
      const [cbRes, recRes] = await Promise.all([
        fetch(`${API_URL}/api/cookbooks`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_URL}/api/recipes`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      if (cbRes.ok) setCookbooks(await cbRes.json());
      if (recRes.ok) setRecipes(await recRes.json());
    } catch (e) {
      toast.error('Failed to load cookbooks');
    }
    setLoading(false);
  };

  const createCookbook = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/api/cookbooks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (res.ok) {
        const data = await res.json();
        setCookbooks(prev => [data, ...prev]);
        setNewName('');
        toast.success(`"${data.name}" created!`);
      }
    } catch { toast.error('Failed to create cookbook'); }
    setCreating(false);
  };

  const deleteCookbook = async (id, name) => {
    if (!window.confirm(`Delete "${name}"? Recipes won't be deleted.`)) return;
    try {
      const token = getToken();
      await fetch(`${API_URL}/api/cookbooks/${id}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      });
      setCookbooks(prev => prev.filter(c => c.cookbook_id !== id));
      if (activeBook?.cookbook_id === id) setActiveBook(null);
      toast.success('Cookbook deleted');
    } catch { toast.error('Failed to delete'); }
  };

  const assignRecipe = async (recipeId, cookbookId) => {
    try {
      const token = getToken();
      await fetch(`${API_URL}/api/cookbooks/${cookbookId}/recipes/${recipeId}`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}` }
      });
      // Update local cookbook recipe_ids
      setCookbooks(prev => prev.map(cb =>
        cb.cookbook_id === cookbookId
          ? { ...cb, recipe_ids: [...(cb.recipe_ids || []), recipeId] }
          : cb
      ));
      setShowAssignModal(null);
      toast.success('Added to cookbook!');
    } catch { toast.error('Failed to assign'); }
  };

  const removeFromCookbook = async (recipeId, cookbookId) => {
    try {
      const token = getToken();
      await fetch(`${API_URL}/api/cookbooks/${cookbookId}/recipes/${recipeId}`, {
        method: 'DELETE', headers: { Authorization: `Bearer ${token}` }
      });
      setCookbooks(prev => prev.map(cb =>
        cb.cookbook_id === cookbookId
          ? { ...cb, recipe_ids: (cb.recipe_ids || []).filter(id => id !== recipeId) }
          : cb
      ));
      toast.success('Removed from cookbook');
    } catch { toast.error('Failed to remove'); }
  };

  const bookRecipes = activeBook
    ? recipes.filter(r => (activeBook.recipe_ids || []).includes(r.recipe_id))
    : [];

  if (loading) return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
      <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24">
      {/* Header */}
      <div className="relative h-[25vh] min-h-[180px]">
        <img src="https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=1920" alt="Cookbooks" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#09090b] via-[#09090b]/60 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-8">
          <div className="max-w-5xl mx-auto flex items-center gap-3">
            {activeBook && (
              <button onClick={() => setActiveBook(null)} className="p-2 rounded-full bg-zinc-800/80 hover:bg-zinc-700 transition-colors">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
              </button>
            )}
            <div>
              <h1 className="font-display text-4xl font-bold">{activeBook ? activeBook.name : 'My Cookbooks'}</h1>
              <p className="text-zinc-400 mt-1">{activeBook ? `${bookRecipes.length} recipes` : `${cookbooks.length} cookbooks`}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">

        {/* Assign modal */}
        {showAssignModal && (
          <div className="fixed inset-0 bg-black/70 z-50 flex items-end sm:items-center justify-center p-4" onClick={() => setShowAssignModal(null)}>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 w-full max-w-sm" onClick={e => e.stopPropagation()}>
              <h3 className="font-semibold text-zinc-100 mb-4">Add to Cookbook</h3>
              <div className="space-y-2">
                {cookbooks.map(cb => (
                  <button key={cb.cookbook_id} onClick={() => assignRecipe(showAssignModal, cb.cookbook_id)}
                    className="w-full text-left p-3 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-sm text-zinc-200 flex items-center gap-3 transition-colors">
                    <BookOpen className="w-4 h-4 text-orange-500 shrink-0" />
                    <span>{cb.name}</span>
                    <span className="ml-auto text-xs text-zinc-500">{(cb.recipe_ids || []).length} recipes</span>
                  </button>
                ))}
                {cookbooks.length === 0 && <p className="text-zinc-500 text-sm text-center py-4">No cookbooks yet — create one below</p>}
              </div>
              <button onClick={() => setShowAssignModal(null)} className="mt-4 w-full py-2 text-sm text-zinc-500 hover:text-zinc-300">Cancel</button>
            </div>
          </div>
        )}

        {/* Create new cookbook */}
        {!activeBook && (
          <Card className="bg-zinc-900 border-zinc-800 mb-8">
            <CardContent className="pt-6">
              <div className="flex gap-3">
                <Input value={newName} onChange={e => setNewName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && createCookbook()}
                  placeholder="New cookbook name..."
                  className="flex-1 bg-zinc-950 border-zinc-800 text-zinc-100 placeholder:text-zinc-600" />
                <Button onClick={createCookbook} disabled={creating || !newName.trim()} className="bg-orange-600 hover:bg-orange-700">
                  {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Plus className="w-4 h-4 mr-2" />Create</>}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Cookbook grid */}
        {!activeBook && (
          <>
            {cookbooks.length === 0 ? (
              <div className="text-center py-16">
                <BookOpen className="w-16 h-16 text-zinc-700 mx-auto mb-4" />
                <p className="text-zinc-400 text-lg">No cookbooks yet</p>
                <p className="text-zinc-600 mt-2">Create your first cookbook above</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {cookbooks.map((cb, i) => (
                  <div key={cb.cookbook_id} className="group relative cursor-pointer" onClick={() => setActiveBook(cb)}>
                    <div className="relative h-40 rounded-xl overflow-hidden">
                      <img src={COOKBOOK_COVERS[i % COOKBOOK_COVERS.length]} alt={cb.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                      <div className="absolute inset-0 bg-gradient-to-t from-zinc-900/90 via-zinc-900/30 to-transparent" />
                      <div className="absolute bottom-0 left-0 right-0 p-3">
                        <p className="font-semibold text-white text-sm line-clamp-1">{cb.name}</p>
                        <p className="text-zinc-400 text-xs">{(cb.recipe_ids || []).length} recipes</p>
                      </div>
                      <button onClick={e => { e.stopPropagation(); deleteCookbook(cb.cookbook_id, cb.name); }}
                        className="absolute top-2 right-2 p-1.5 bg-zinc-900/80 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-900">
                        <Trash2 className="w-3.5 h-3.5 text-zinc-400 hover:text-red-400" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Cookbook detail — recipes inside */}
        {activeBook && (
          <div>
            {/* Add recipes to this cookbook */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-zinc-100">Recipes in this cookbook</h2>
              <Button onClick={() => {}} className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm"
                // Show all recipes not yet in this book
                onClickCapture={(e) => {
                  e.preventDefault();
                  // We reuse showAssignModal in reverse — pick recipe first
                }}>
                <Plus className="w-4 h-4 mr-2" />
                Add Recipes
              </Button>
            </div>

            {bookRecipes.length === 0 ? (
              <div className="text-center py-16">
                <ChefHat className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                <p className="text-zinc-400">No recipes in this cookbook yet</p>
                <p className="text-zinc-600 text-sm mt-2">Go to a recipe and tap 📚 to add it here</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {bookRecipes.map(recipe => (
                  <div key={recipe.recipe_id} className="relative">
                    <RecipeCard recipe={recipe} />
                    <button onClick={() => removeFromCookbook(recipe.recipe_id, activeBook.cookbook_id)}
                      className="absolute top-2 left-2 px-2 py-1 bg-red-600/80 hover:bg-red-600 rounded-full text-xs text-white transition-colors">
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Cookbooks;
