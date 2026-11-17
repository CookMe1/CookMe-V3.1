import React, { useState, useEffect, useCallback } from 'react';
import {
  ChevronLeft, ChevronRight, Plus, Trash2, Sparkles,
  Calendar, Loader2, X, Search, ShoppingCart
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Link, useNavigate } from 'react-router-dom';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const MEAL_TYPES = ['breakfast', 'lunch', 'dinner'];

// ── Helpers ───────────────────────────────────────────────────────────────────

function getMondayOfWeek(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

function formatWeekLabel(mondayDate) {
  const end = new Date(mondayDate);
  end.setDate(end.getDate() + 6);
  const opts = { month: 'short', day: 'numeric' };
  return `${mondayDate.toLocaleDateString('en-GB', opts)} – ${end.toLocaleDateString('en-GB', opts)}, ${mondayDate.getFullYear()}`;
}

function toISODate(date) {
  return date.toISOString().split('T')[0];
}

function buildEmptyWeek(monday) {
  const names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  return names.map((day_name, i) => {
    const d = new Date(monday);
    d.setDate(d.getDate() + i);
    return { date: toISODate(d), day_name, breakfast: null, lunch: null, dinner: null };
  });
}

// ── Recipe picker modal ───────────────────────────────────────────────────────

const RecipePicker = ({ onSelect, onClose }) => {
  const [search, setSearch] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const res = await fetch(`${API_URL}/api/recipes?limit=100`, {
          headers: { Authorization: `Bearer ${getToken()}` }
        });
        if (res.ok) {
          const data = await res.json();
          setRecipes(data.recipes || data || []);
        }
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    fetch_();
  }, []);

  const filtered = recipes.filter(r =>
    (r.title || '').toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <h3 className="font-semibold text-zinc-100">Choose a Recipe</h3>
          <button onClick={onClose} className="p-1 hover:bg-zinc-800 rounded-lg transition-colors">
            <X className="w-5 h-5 text-zinc-400" />
          </button>
        </div>
        <div className="p-3 border-b border-zinc-800">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search your recipes..."
              className="w-full pl-9 pr-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder:text-zinc-600 outline-none focus:border-orange-500"
              autoFocus
            />
          </div>
        </div>
        <div className="overflow-y-auto flex-1 p-2">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-orange-500 animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-zinc-500 text-sm">
              {recipes.length === 0 ? (
                <><p>No recipes yet.</p><Link to="/add-recipe" className="text-orange-500 hover:underline">Add your first recipe</Link></>
              ) : 'No recipes match your search'}
            </div>
          ) : (
            filtered.map(recipe => (
              <button
                key={recipe.recipe_id}
                onClick={() => onSelect({
                  recipe_id: recipe.recipe_id,
                  recipe_title: recipe.title,
                  recipe_image: recipe.image || '',
                  custom_meal: recipe.title,
                })}
                className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-zinc-800 transition-colors text-left"
              >
                {recipe.image ? (
                  <img src={recipe.image} alt={recipe.title}
                    className="w-12 h-12 rounded-lg object-cover shrink-0"
                    onError={e => { e.target.style.display = 'none'; }} />
                ) : (
                  <div className="w-12 h-12 rounded-lg bg-zinc-700 shrink-0 flex items-center justify-center">
                    <span className="text-xl">🍽️</span>
                  </div>
                )}
                <div className="min-w-0">
                  <p className="text-sm font-medium text-zinc-100 truncate">{recipe.title}</p>
                  <p className="text-xs text-zinc-500">{recipe.prep_time || ''} {recipe.cook_time ? `· ${recipe.cook_time}` : ''}</p>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

const MealPlanner = () => {
  const navigate = useNavigate();
  const [monday, setMonday] = useState(() => getMondayOfWeek(new Date()));
  const [days, setDays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [picker, setPicker] = useState(null); // { dayIndex, mealType }

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');
  const weekStart = toISODate(monday);

  // ── Load meal plan for current week ──────────────────────────────────────

  const loadPlan = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/meal-plans/${weekStart}`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDays(data.days && data.days.length === 7 ? data.days : buildEmptyWeek(monday));
      } else {
        setDays(buildEmptyWeek(monday));
      }
    } catch (e) {
      setDays(buildEmptyWeek(monday));
    }
    setLoading(false);
  }, [weekStart]);

  useEffect(() => { loadPlan(); }, [loadPlan]);

  // ── Save current week ──────────────────────────────────────────────────

  const savePlan = async (updatedDays) => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/meal-plans/${weekStart}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ week_start: weekStart, days: updatedDays })
      });
      if (!res.ok) throw new Error('Save failed');
    } catch (e) {
      toast.error('Failed to save meal plan');
    }
    setSaving(false);
  };

  // ── Week navigation ────────────────────────────────────────────────────

  const prevWeek = () => {
    const d = new Date(monday);
    d.setDate(d.getDate() - 7);
    setMonday(d);
  };
  const nextWeek = () => {
    const d = new Date(monday);
    d.setDate(d.getDate() + 7);
    setMonday(d);
  };
  const goToThisWeek = () => setMonday(getMondayOfWeek(new Date()));

  // ── Slot actions ───────────────────────────────────────────────────────

  const assignRecipe = async (dayIndex, mealType, slot) => {
    const updated = days.map((day, i) =>
      i === dayIndex ? { ...day, [mealType]: slot } : day
    );
    setDays(updated);
    await savePlan(updated);
  };

  const removeSlot = async (dayIndex, mealType) => {
    const updated = days.map((day, i) =>
      i === dayIndex ? { ...day, [mealType]: null } : day
    );
    setDays(updated);
    await savePlan(updated);
  };

  // ── AI generate ───────────────────────────────────────────────────────

  const generateAI = async () => {
    setGenerating(true);
    try {
      const res = await fetch(`${API_URL}/api/meal-plans/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
        body: JSON.stringify({ week_start: weekStart })
      });
      if (!res.ok) throw new Error('Generation failed');
      const data = await res.json();
      if (data.days) {
        setDays(data.days);
        toast.success('Meal plan generated!');
      }
    } catch (e) {
      toast.error('Failed to generate meal plan');
    }
    setGenerating(false);
  };

  // ── Clear week ────────────────────────────────────────────────────────

  const clearWeek = async () => {
    const empty = buildEmptyWeek(monday);
    setDays(empty);
    await savePlan(empty);
    toast.success('Week cleared');
  };

  // ── Generate shopping list ─────────────────────────────────────────────

  const generateShoppingList = async () => {
    // Collect all recipe IDs from the plan
    const recipeIds = [];
    days.forEach(day => {
      MEAL_TYPES.forEach(mt => {
        if (day[mt]?.recipe_id) recipeIds.push(day[mt].recipe_id);
      });
    });
    if (recipeIds.length === 0) {
      toast.info('Add some recipes to your plan first');
      return;
    }
    toast.success(`Adding ingredients from ${recipeIds.length} recipes to shopping list`);
    navigate('/shopping-list');
  };

  const isThisWeek = toISODate(getMondayOfWeek(new Date())) === weekStart;

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Recipe picker modal */}
      {picker && (
        <RecipePicker
          onSelect={async (slot) => {
            setPicker(null);
            await assignRecipe(picker.dayIndex, picker.mealType, slot);
            toast.success(`${slot.recipe_title} added to ${picker.mealType}`);
          }}
          onClose={() => setPicker(null)}
        />
      )}

      {/* Hero */}
      <div className="relative h-[25vh] min-h-[200px]">
        <img
          src="https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=1920&h=600&fit=crop"
          alt="Meal Planning"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-overlay" />
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-7xl mx-auto">
            <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">Meal Planner</h1>
            <p className="text-zinc-400 mt-2">Plan your weekly meals and stay organised</p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Week navigation */}
        <div className="flex items-center justify-between mb-6 gap-3">
          <Button variant="outline" size="sm"
            onClick={prevWeek}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            <ChevronLeft className="w-5 h-5" />
          </Button>

          <div className="text-center">
            <h2 className="text-lg font-semibold text-zinc-100">{formatWeekLabel(monday)}</h2>
            {!isThisWeek && (
              <button onClick={goToThisWeek}
                className="text-xs text-orange-500 hover:text-orange-400 mt-0.5">
                → Back to this week
              </button>
            )}
          </div>

          <Button variant="outline" size="sm"
            onClick={nextWeek}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap gap-3 mb-6">
          <Button
            onClick={generateAI}
            disabled={generating}
            className="bg-orange-600 hover:bg-orange-700"
          >
            {generating
              ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Generating...</>
              : <><Sparkles className="w-4 h-4 mr-2" />AI Generate Week</>
            }
          </Button>
          <Button variant="outline"
            onClick={generateShoppingList}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            <ShoppingCart className="w-4 h-4 mr-2" />
            Shopping List
          </Button>
          <Button variant="outline"
            onClick={clearWeek}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            Clear Week
          </Button>
          {saving && (
            <div className="flex items-center gap-1.5 text-xs text-zinc-500 ml-auto self-center">
              <Loader2 className="w-3 h-3 animate-spin" />Saving...
            </div>
          )}
        </div>

        {/* Meal plan grid */}
        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
          </div>
        ) : (
          <Card className="bg-zinc-900 border-zinc-800 overflow-hidden mb-6">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px]">
                <thead className="bg-zinc-800/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-zinc-300 w-28">Day</th>
                    {MEAL_TYPES.map(type => (
                      <th key={type} className="px-4 py-3 text-left text-sm font-semibold text-zinc-300 capitalize">
                        {type}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {days.map((day, dayIndex) => {
                    const isToday = day.date === toISODate(new Date());
                    return (
                      <tr key={day.date}
                        className={dayIndex % 2 === 0 ? 'bg-zinc-900' : 'bg-zinc-900/50'}>
                        <td className="px-4 py-4">
                          <p className={`font-semibold text-sm ${isToday ? 'text-orange-400' : 'text-zinc-100'}`}>
                            {day.day_name}
                            {isToday && <span className="ml-1 text-xs font-normal">(Today)</span>}
                          </p>
                          <p className="text-xs text-zinc-500 mt-0.5">
                            {new Date(day.date + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                          </p>
                        </td>
                        {MEAL_TYPES.map(mealType => {
                          const slot = day[mealType];
                          return (
                            <td key={mealType} className="px-3 py-3">
                              {slot ? (
                                <div className="group relative">
                                  {slot.recipe_id ? (
                                    <Link to={`/recipe/${slot.recipe_id}`}>
                                      <div className="flex items-center gap-2 p-2 rounded-lg hover:bg-zinc-800 transition-colors cursor-pointer">
                                        {slot.recipe_image ? (
                                          <img src={slot.recipe_image} alt={slot.recipe_title}
                                            className="w-12 h-12 rounded-lg object-cover shrink-0"
                                            onError={e => { e.target.style.display = 'none'; }} />
                                        ) : (
                                          <div className="w-12 h-12 rounded-lg bg-zinc-700 shrink-0 flex items-center justify-center text-lg">🍽️</div>
                                        )}
                                        <p className="text-xs font-medium text-zinc-200 line-clamp-2">
                                          {slot.recipe_title || slot.custom_meal}
                                        </p>
                                      </div>
                                    </Link>
                                  ) : (
                                    <div className="flex items-center gap-2 p-2 rounded-lg bg-zinc-800/50">
                                      <div className="w-12 h-12 rounded-lg bg-zinc-700 shrink-0 flex items-center justify-center text-lg">🍽️</div>
                                      <p className="text-xs font-medium text-zinc-300 line-clamp-2">
                                        {slot.custom_meal}
                                      </p>
                                    </div>
                                  )}
                                  <button
                                    onClick={() => removeSlot(dayIndex, mealType)}
                                    className="absolute -top-1 -right-1 p-1 bg-zinc-800 border border-zinc-700 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-500/20">
                                    <X className="w-3 h-3 text-red-400" />
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => setPicker({ dayIndex, mealType })}
                                  className="w-full p-3 border-2 border-dashed border-zinc-700 rounded-lg hover:border-orange-600 hover:bg-orange-600/5 transition-colors group">
                                  <Plus className="w-5 h-5 mx-auto text-zinc-600 group-hover:text-orange-500" />
                                </button>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {/* Tips */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-zinc-100 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-orange-500" />
              Planning Tips
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm text-zinc-400">
              <li className="flex items-start gap-2"><span className="text-orange-500 mt-0.5">•</span>Tap the + button to add recipes from your collection</li>
              <li className="flex items-start gap-2"><span className="text-orange-500 mt-0.5">•</span>Use AI Generate to fill a full week based on your pantry</li>
              <li className="flex items-start gap-2"><span className="text-orange-500 mt-0.5">•</span>Shopping List creates a list from all recipes in your plan</li>
              <li className="flex items-start gap-2"><span className="text-orange-500 mt-0.5">•</span>Plans are saved automatically as you make changes</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MealPlanner;
