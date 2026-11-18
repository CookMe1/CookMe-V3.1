import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import ShareRecipe from '../components/ShareRecipe';
import Comments from '../components/Comments';
import { Clock, Users, ChefHat, Heart, Bookmark, Share2, Minus, Plus, Printer, Loader2, Camera, ImageIcon, Trash2, Upload, AlertCircle, ShoppingCart, Check } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { toast } from 'sonner';
import CookingMode from '../components/CookingMode';
import CookingOptions from '../components/CookingOptions';
import useCookingSetup from '../hooks/useCookingSetup';
import { stepCooksProtein, showTemp, fmtLabel } from '../utils/cookingTools';
import SourceCredit from '../components/SourceCredit';
import { convertAmount } from '../utils/units';
import { PLACEHOLDER_IMAGE, onImageError } from '../utils/placeholder';
import { validateImageQuality, getRejectMessage, compressImage } from '../utils/imageValidator';
import { useLanguage } from '../context/LanguageContext';
import { askConfirm } from '../utils/confirm';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const RecipeDetail = () => {
  const { id } = useParams();
  const { checkSeasonal } = useLanguage();
  const { user: currentUser } = useAuth();
  const [recipe, setRecipe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [servings, setServings] = useState(4);
  const [originalServings, setOriginalServings] = useState(4);
  const [activeTab, setActiveTab] = useState('ingredients');
  const [units, setUnits] = useState(() => { try { return localStorage.getItem('units') || 'original'; } catch (e) { return 'original'; } });
  const [cooking, setCooking] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const setup = useCookingSetup(recipe);
  const [isLiked, setIsLiked] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [nutrition, setNutrition] = useState(null);
  const [loadingNutrition, setLoadingNutrition] = useState(false);
  const [galleryImages, setGalleryImages] = useState([]);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [similarRecipes, setSimilarRecipes] = useState([]);
  const [loadingSimilar, setLoadingSimilar] = useState(false);
  const fileInputRef = useRef(null);

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');
  const [pantryNames, setPantryNames] = useState([]);
  const [onList, setOnList] = useState({});

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    fetch(`${API_URL}/api/pantry`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => (r.ok ? r.json() : []))
      .then(items => setPantryNames(
        (Array.isArray(items) ? items : []).filter(i => i.in_stock !== false).map(i => (i.name || '').toLowerCase())
      ))
      .catch(() => {});
  }, [id]);

  const inPantry = (name) => {
    const n = (name || '').toLowerCase();
    return !!n && pantryNames.some(p => p && (p === n || n.includes(p) || p.includes(n)));
  };

  const authedPost = (path, body) => fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
    body: JSON.stringify(body),
  });

  const addToShopping = async (names) => {
    try {
      const r = await authedPost('/api/shopping-list/add-items', { items: names });
      if (!r.ok) throw new Error();
      const d = await r.json();
      setOnList(prev => ({ ...prev, ...Object.fromEntries(names.map(n => [n, true])) }));
      toast.success(d.added_count ? `Added ${d.added_count} to your shopping list` : 'Already on your shopping list');
    } catch { toast.error('Could not add to shopping list'); }
  };

  const addToPantry = async (ing) => {
    const name = ing.item || (typeof ing === 'string' ? ing : '');
    try {
      const r = await authedPost('/api/pantry', { name, category: ing.category || 'Other', amount: '1', in_stock: true });
      if (!r.ok) throw new Error();
      setPantryNames(prev => [...prev, name.toLowerCase()]);
      toast.success(`${name} added to your pantry`);
    } catch { toast.error('Could not add to pantry'); }
  };

  useEffect(() => {
    setNutrition(null);   // a different recipe: never keep the previous recipe's numbers
    fetchRecipe();
    fetchGalleryImages();
    fetchSimilarRecipes();
  // eslint-disable-next-line react-hooks/exhaustive-deps -- runs only on these triggers on purpose (adding the functions would loop)
  }, [id]);

  // Auto-calculate nutrition when recipe loads without nutrition data
  useEffect(() => {
    if (recipe && recipe.ingredients && recipe.ingredients.length > 0 && !nutrition && !loadingNutrition) {
      calculateNutrition();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- runs only on these triggers on purpose (adding the functions would loop)
  }, [recipe]);

  const fetchRecipe = async () => {
    try {
      setLoading(true);
      const token = getToken();
      
      const response = await fetch(`${API_URL}/api/recipes/${id}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setRecipe(data);
        setServings(parseInt(data.servings) || 4);
        setOriginalServings(parseInt(data.servings) || 4);
        
        // Set nutrition if available
        // Values calculated by an older, inaccurate version are recalculated (calc_v 2 = fixed)
        const n = data.nutrition;
        const stale = n && n.source && n.source !== 'ai' && n.calc_v !== 2;
        setNutrition(n && !stale ? n : null);
      } else {
        toast.error('Recipe not found');
      }
    } catch (error) {
      console.error('Failed to fetch recipe:', error);
      toast.error('Failed to load recipe');
    } finally {
      setLoading(false);
    }
  };

  const fetchGalleryImages = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${id}/gallery`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setGalleryImages(data.images || []);
      }
    } catch (error) {
      console.error('Failed to fetch gallery:', error);
    }
  };

  const fetchSimilarRecipes = async () => {
    setLoadingSimilar(true);
    try {
      const token = getToken();
      const res = await fetch(
        `${API_URL}/api/community/recipes/similar?recipe_id=${id}&limit=4`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        const data = await res.json();
        setSimilarRecipes(data.recipes || []);
      }
    } catch (error) {
      console.error('Failed to fetch similar recipes:', error);
    } finally {
      setLoadingSimilar(false);
    }
  };

  const saveCommunityRecipe = async (communityRecipeId, title) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/api/community/recipes/${communityRecipeId}/save`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        toast.success(data.already_existed ? `"${title}" already in your collection` : `"${title}" saved to your recipes!`);
      }
    } catch {
      toast.error('Failed to save recipe');
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploadingImage(true);
    
    try {
      // Convert to base64
      const reader = new FileReader();
      reader.readAsDataURL(file);
      
      reader.onload = async () => {
        const base64Image = reader.result;
        const token = getToken();
        
        try {
          // Step 1: Validate image quality
          const validation = await validateImageQuality(base64Image, token);
          
          if (!validation.valid) {
            // Image rejected
            const message = getRejectMessage(validation.reason);
            toast.error(message);
            setUploadingImage(false);
            e.target.value = '';
            return;
          }
          
          // Use compressed image from validation
          const compressedImage = validation.compressedImage || base64Image;
          
          // Step 2: Upload to gallery
          const response = await fetch(`${API_URL}/api/recipes/${id}/gallery`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ image_data: compressedImage })
          });
          
          if (response.ok) {
            const data = await response.json();
            setGalleryImages(prev => [...prev, data.image]);
            toast.success('Image uploaded to gallery!');
          } else {
            toast.error('Failed to upload image');
          }
        } catch (innerErr) {
          console.error('Upload failed:', innerErr);
          toast.error('Failed to upload image');
        }
        setUploadingImage(false);
      };
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Failed to upload image');
      setUploadingImage(false);
    }
  };

  const handleDeleteGalleryImage = async (imageId) => {
    if (!(await askConfirm('Delete this image from the gallery?', { confirmLabel: 'Delete' }))) return;
    
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${id}/gallery/${imageId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        setGalleryImages(prev => prev.filter(img => img.image_id !== imageId));
        toast.success('Image deleted');
      } else {
        toast.error('Failed to delete image');
      }
    } catch (error) {
      console.error('Delete failed:', error);
      toast.error('Failed to delete image');
    }
  };

  const calculateNutrition = async () => {
    if (!recipe?.ingredients || recipe.ingredients.length === 0) {
      toast.error('No ingredients to calculate nutrition');
      return;
    }
    try {
      setLoadingNutrition(true);
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/calculate-nutrition`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          ingredients: recipe.ingredients,
          servings: servings,
          recipe_id: id   // tells backend to save result back to recipe document
        })
      });
      if (response.ok) {
        const data = await response.json();
        setNutrition(data);
        toast.success('Nutrition calculated!');
      }
    } catch (error) {
      console.error('Failed to calculate nutrition:', error);
      toast.error('Failed to calculate nutrition');
    } finally {
      setLoadingNutrition(false);
    }
  };

  const handleLike = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${id}/like`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setIsLiked(data.liked);
        toast.success(data.liked ? 'Recipe liked!' : 'Like removed');
      }
    } catch (error) {
      console.error('Failed to like recipe:', error);
    }
  };

  const handleSave = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${id}/save`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setIsSaved(data.saved);
        toast.success(data.saved ? 'Recipe saved!' : 'Removed from saved');
      }
    } catch (error) {
      console.error('Failed to save recipe:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="flex flex-col items-center">
          <Loader2 className="w-12 h-12 text-orange-500 animate-spin mb-4" />
          <p className="text-zinc-400">Loading recipe...</p>
        </div>
      </div>
    );
  }

  if (!recipe) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="text-center">
          <p className="text-zinc-400 mb-4">Recipe not found</p>
          <Link to="/recipes">
            <Button className="bg-orange-600 hover:bg-orange-700">
              Back to Recipes
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // ── Improved fraction-aware ingredient scaler ──────────────────────────────
  const scaleAmount = (amount) => {
    if (!amount) return amount;
    const ratio = servings / originalServings;
    if (ratio === 1) return amount;

    // Nice unicode fractions for common values
    const FRACS = { 0.125: '⅛', 0.25: '¼', 0.333: '⅓', 0.5: '½', 0.667: '⅔', 0.75: '¾' };

    const formatNum = (n) => {
      if (n === 0) return '0';
      const whole = Math.floor(n);
      const dec = n - whole;
      // Find closest unicode fraction
      const frac = Object.entries(FRACS).find(([k]) => Math.abs(dec - parseFloat(k)) < 0.04);
      if (frac) return whole ? `${whole} ${frac[1]}` : frac[1];
      // Otherwise 1 decimal, strip trailing .0
      return n % 1 === 0 ? `${n}` : n.toFixed(1).replace(/\.0$/, '');
    };

    const parseNum = (str) => {
      str = str.trim();
      // Handle mixed numbers like "1 1/2"
      const mixed = str.match(/^(\d+)\s+(\d+)\/(\d+)$/);
      if (mixed) return parseInt(mixed[1]) + parseInt(mixed[2]) / parseInt(mixed[3]);
      // Handle fractions like "1/2"
      const frac = str.match(/^(\d+)\/(\d+)$/);
      if (frac) return parseInt(frac[1]) / parseInt(frac[2]);
      return parseFloat(str);
    };

    // Replace all numeric tokens (including fractions) in the string
    return amount.toString().replace(
      /\d+\s+\d+\/\d+|\d+\/\d+|\d+\.?\d*/g,
      (match) => {
        const val = parseNum(match);
        if (isNaN(val)) return match;
        return formatNum(val * ratio);
      }
    );
  };

  // Scale nutrition based on servings — pure frontend math, no API call
  const getScaledNutrition = () => {
    if (!nutrition) return null;
    const ratio = servings / originalServings;
    return {
      calories: Math.round((nutrition.calories || 0) * ratio),
      protein: Math.round((nutrition.protein || 0) * ratio),
      carbs: Math.round((nutrition.carbs || 0) * ratio),
      fat: Math.round((nutrition.fat || 0) * ratio),
      fiber: Math.round((nutrition.fiber || 0) * ratio),
      sugar: Math.round((nutrition.sugar || 0) * ratio)
    };
  };

  // Scale cooking times based on servings (for larger batches)
  const getScaledTime = (timeStr) => {
    if (!timeStr) return '30 min';
    if (servings <= originalServings * 1.5) return timeStr;
    const multiplier = servings > originalServings * 2 ? 1.3 : 1.15;
    const minutes = parseInt(timeStr);
    if (!isNaN(minutes)) {
      return `${Math.round(minutes * multiplier)} min`;
    }
    return timeStr;
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: recipe.title,
          text: `Check out this recipe: ${recipe.title}`,
          url: window.location.href
        });
      } catch (err) {
      }
    } else {
      navigator.clipboard.writeText(window.location.href);
      toast.success('Link copied to clipboard!');
    }
  };

  const ingredients = recipe.ingredients || [];
  const steps = recipe.steps || [];
  const scaledNutrition = getScaledNutrition();

  const cookingIngredients = ingredients.map((ing) => ({
    name: ing.item || (typeof ing === 'string' ? ing : ''),
    amount: ing.amount ? scaleAmount(convertAmount(ing.amount, units)) : '',
  }));

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {cooking && (
        <CookingMode title={recipe.title} steps={steps} ingredients={cookingIngredients} setup={setup} onClose={() => setCooking(false)} />
      )}
      {/* Hero Image */}
      <div className="relative h-[42vh] min-h-[260px] md:h-[55vh]">
        <img 
          src={recipe.image || PLACEHOLDER_IMAGE}
          alt={recipe.title}
          className="absolute inset-0 w-full h-full object-cover"
          onError={onImageError}
        />
        {/* light shade at the top only, so the buttons stay readable; the photo itself is clear */}
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-black/50 to-transparent pointer-events-none" />
        
        {/* Back Button */}
        <Link 
          to="/recipes"
          className="absolute top-6 left-6 p-2 rounded-full bg-zinc-900/50 backdrop-blur-sm hover:bg-zinc-800 transition-colors z-20"
          data-testid="back-btn"
        >
          <svg className="w-6 h-6 text-zinc-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        
        {/* Action Buttons */}
        <div className="absolute top-6 right-6 flex gap-2 z-20">
          <button
            onClick={handleLike}
            className="p-3 rounded-full bg-zinc-900/50 backdrop-blur-sm hover:bg-zinc-800 transition-colors"
            data-testid="like-recipe-btn"
          >
            <Heart className={`w-5 h-5 ${isLiked ? 'fill-red-500 text-red-500' : 'text-zinc-100'}`} />
          </button>
          <button
            onClick={handleSave}
            className="p-3 rounded-full bg-zinc-900/50 backdrop-blur-sm hover:bg-zinc-800 transition-colors"
            data-testid="save-recipe-btn"
          >
            <Bookmark className={`w-5 h-5 ${isSaved ? 'fill-orange-500 text-orange-500' : 'text-zinc-100'}`} />
          </button>
          <button
            onClick={handleShare}
            className="p-3 rounded-full bg-zinc-900/50 backdrop-blur-sm hover:bg-zinc-800 transition-colors"
            data-testid="share-recipe-btn"
          >
            <Share2 className="w-5 h-5 text-zinc-100" />
          </button>
        </div>
        
      </div>

      {/* Recipe Info: below the photo so the photo stays clear */}
      <div className="px-6 md:px-8 pt-6">
          <div className="max-w-4xl mx-auto">
            <div className="flex flex-wrap gap-2 mb-4">
              <span className="inline-block px-3 py-1 bg-orange-600 text-white text-xs font-semibold rounded-full">
                {recipe.difficulty || 'Medium'}
              </span>
              {recipe.category && (
                <span className="inline-block px-3 py-1 bg-purple-600/80 text-white text-xs font-semibold rounded-full capitalize">
                  {recipe.category.replace('_', ' ')}
                </span>
              )}
              {recipe.cuisine && (
                <span className="inline-block px-3 py-1 bg-blue-600/80 text-white text-xs font-semibold rounded-full capitalize">
                  {recipe.cuisine.replace('_', ' ')}
                </span>
              )}
              {recipe.source_url && (
                <span className="inline-block px-3 py-1 bg-zinc-800 text-zinc-300 text-xs font-semibold rounded-full">
                  {recipe.source_url.includes('youtube') ? 'From YouTube' : 'Imported'}
                </span>
              )}
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100 mb-4">
              {recipe.title}
            </h1>
            <p className="text-zinc-300 mb-6 max-w-2xl">{recipe.description}</p>
            {currentUser && recipe.user_id === currentUser.user_id && (
              <div className="flex flex-wrap items-center gap-3 mb-6" data-testid="owner-actions">
                <Link to={`/recipe/${recipe.recipe_id}/edit`} className="inline-flex items-center px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-100 text-sm font-medium" data-testid="edit-recipe-btn">
                  Edit
                </Link>
                <ShareRecipe recipe={recipe} onChange={fetchRecipe} />
              </div>
            )}
            
            <div className="flex flex-wrap items-center gap-6 text-zinc-400">
              <span className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                {(() => {
                  const f = recipe.time_estimated ? '~' : '';
                  const p = recipe.prep_time ? getScaledTime(recipe.prep_time) : '';
                  const c = recipe.cook_time || '';
                  return p && c ? `Prep ${f}${p} · Cook ${f}${c}` : (p || c || '—');
                })()}
              </span>
              <span className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                {servings} servings
              </span>
              <span className="flex items-center gap-2">
                <ChefHat className="w-5 h-5" />
                {recipe.difficulty || 'Medium'}
              </span>
              {recipe.uploader_name && (
                <span className="flex items-center gap-2 text-orange-400">
                  <span className="w-5 h-5 rounded-full bg-orange-600/30 flex items-center justify-center text-xs">
                    {recipe.uploader_name.charAt(0).toUpperCase()}
                  </span>
                  Added by {recipe.uploader_name}
                </span>
              )}
            </div>
          </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 md:px-8 py-8">
        {/* Serving Adjuster */}
        <Card className="bg-zinc-900 border-zinc-800 p-6 mb-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h3 className="font-semibold text-zinc-100 mb-1">Adjust Servings</h3>
              <p className="text-sm text-zinc-500">Ingredients and nutrition will scale automatically</p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setServings(Math.max(1, servings - 1))}
                className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors"
                data-testid="decrease-servings"
              >
                <Minus className="w-5 h-5 text-zinc-300" />
              </button>
              <span className="text-2xl font-bold text-orange-500 w-12 text-center" data-testid="servings-count">
                {servings}
              </span>
              <button
                onClick={() => setServings(servings + 1)}
                className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors"
                data-testid="increase-servings"
              >
                <Plus className="w-5 h-5 text-zinc-300" />
              </button>
              <div className="flex rounded-lg overflow-hidden border border-zinc-700 text-sm" data-testid="units-toggle">
                {[['original', 'Original'], ['metric', 'Metric'], ['us', 'US']].map(([v, label]) => (
                  <button
                    key={v}
                    onClick={() => { setUnits(v); try { localStorage.setItem('units', v); } catch (e) { /* ignore */ } }}
                    className={`px-3 py-2 ${units === v ? 'bg-orange-600 text-white' : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <Button
                variant="outline"
                onClick={() => window.print()}
                className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 ml-4"
              >
                <Printer className="w-4 h-4 mr-2" />
                Print
              </Button>
            </div>
          </div>
        </Card>

        {/* Nutrition Card - Auto-displayed */}
        <Card className="bg-zinc-900 border-zinc-800 p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-zinc-100">Nutrition per serving</h3>
            {loadingNutrition && (
              <div className="flex items-center gap-2 text-orange-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-sm">Calculating...</span>
              </div>
            )}
          </div>
          
          {scaledNutrition ? (
            <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
              {[
                { label: 'Calories', value: scaledNutrition.calories, unit: 'kcal' },
                { label: 'Protein', value: scaledNutrition.protein, unit: 'g' },
                { label: 'Carbs', value: scaledNutrition.carbs, unit: 'g' },
                { label: 'Fat', value: scaledNutrition.fat, unit: 'g' },
                { label: 'Fiber', value: scaledNutrition.fiber, unit: 'g' },
                { label: 'Sugar', value: scaledNutrition.sugar, unit: 'g' }
              ].map((item) => (
                <div key={item.label} className="text-center p-3 bg-zinc-800/50 rounded-lg">
                  <div className="text-xl font-bold text-orange-500">{item.value}</div>
                  <div className="text-xs text-zinc-500">{item.unit}</div>
                  <div className="text-xs text-zinc-400 mt-1">{item.label}</div>
                </div>
              ))}
            </div>
          ) : !loadingNutrition ? (
            <div className="flex items-center justify-center py-4">
              <div className="animate-pulse flex space-x-4">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div key={i} className="text-center p-3 bg-zinc-800/50 rounded-lg w-16">
                    <div className="h-6 bg-zinc-700 rounded mb-1"></div>
                    <div className="h-3 bg-zinc-700 rounded w-8 mx-auto"></div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </Card>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b border-zinc-800 overflow-x-auto">
          {['ingredients', 'instructions', 'images'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-2 text-sm font-medium capitalize transition-colors whitespace-nowrap flex items-center gap-2 ${
                activeTab === tab
                  ? 'text-orange-500 border-b-2 border-orange-500'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
              data-testid={`tab-${tab}`}
            >
              {tab === 'images' && <ImageIcon className="w-4 h-4" />}
              {tab}
              {tab === 'images' && galleryImages.length > 0 && (
                <span className="ml-1 px-1.5 py-0.5 bg-orange-600/20 text-orange-500 text-xs rounded-full">
                  {galleryImages.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {activeTab === 'ingredients' && (
          <div className="space-y-3" data-testid="ingredients-list">
            {ingredients.length > 0 && getToken() && (
              <button
                data-testid="add-missing-to-shopping"
                onClick={() => {
                  const missing = ingredients.map(i => i.item || (typeof i === 'string' ? i : '')).filter(n => n && !inPantry(n));
                  if (!missing.length) { toast.success('You already have everything in your pantry'); return; }
                  addToShopping(missing);
                }}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-lg bg-orange-500/10 border border-orange-500/30 text-orange-400 text-sm font-medium hover:bg-orange-500/20"
              >
                <ShoppingCart className="w-4 h-4" /> Add what I'm missing to shopping list
              </button>
            )}
            {ingredients.length > 0 ? (
              ingredients.map((ing, index) => {
                const ingName = ing.item || (typeof ing === 'string' ? ing : '');
                const inSeason = ingName ? checkSeasonal(ingName) : null;
                return (
                  <div
                    key={index}
                    className="flex items-center gap-4 p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg"
                  >
                    <div className="w-6 h-6 rounded-full border-2 border-zinc-700 flex-shrink-0" />
                    <span className="text-zinc-300 flex-1">{ingName}</span>
                    {inSeason === true && (
                      <span
                        title="In season this month"
                        className="text-xs px-2 py-0.5 bg-emerald-600/20 text-emerald-400 border border-emerald-600/30 rounded-full shrink-0"
                      >
                        🌱 In season
                      </span>
                    )}
                    {ing.amount && (
                      <span className="text-orange-500 font-medium shrink-0" data-testid={`amount-${index}`}>
                        {scaleAmount(convertAmount(ing.amount, units))}
                      </span>
                    )}
                    {ingName && getToken() && (
                      <div className="flex items-center gap-1 shrink-0">
                        {inPantry(ingName) ? (
                          <span title="In your pantry" className="text-xs text-emerald-400 flex items-center gap-1 px-1">
                            <Check className="w-4 h-4" /> Have
                          </span>
                        ) : (
                          <button
                            title="I have this: add to pantry"
                            aria-label={`Add ${ingName} to pantry`}
                            data-testid={`pantry-add-${index}`}
                            onClick={() => addToPantry(ing)}
                            className="text-xs px-2 py-1.5 rounded-md border border-zinc-700 text-zinc-300 hover:border-emerald-500 hover:text-emerald-400"
                          >
                            + Pantry
                          </button>
                        )}
                        <button
                          title="Add to shopping list"
                          aria-label={`Add ${ingName} to shopping list`}
                          data-testid={`shop-add-${index}`}
                          onClick={() => addToShopping([ingName])}
                          className={`p-2 rounded-md border ${onList[ingName] ? 'border-orange-500 text-orange-400' : 'border-zinc-700 text-zinc-300 hover:border-orange-500 hover:text-orange-400'}`}
                        >
                          {onList[ingName] ? <Check className="w-4 h-4" /> : <ShoppingCart className="w-4 h-4" />}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <p className="text-zinc-500 text-center py-8">No ingredients listed</p>
            )}
          </div>
        )}

        {activeTab === 'instructions' && (
          <div className="space-y-4" data-testid="instructions-list">
            {setup.available && (
              <div data-testid="cooking-setup-card">
                <button
                  onClick={() => setShowSetup((v) => !v)}
                  className="w-full flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-3 text-left"
                  data-testid="toggle-cooking-setup"
                >
                  <span className="text-sm text-zinc-200">
                    <span className="font-semibold">Cooking setup</span>
                    <span className="text-zinc-500"> · {setup.type ? `${setup.type.name}, ${setup.method === 'airfryer' ? 'air fryer' : setup.method}` : 'air fryer option'}</span>
                  </span>
                  <span className="text-orange-400 text-sm">{showSetup ? 'Hide' : 'Customise'}</span>
                </button>
                {showSetup && <div className="mt-3"><CookingOptions setup={setup} /></div>}
              </div>
            )}
            {steps.length > 0 && (
              <Button onClick={() => setCooking(true)} className="w-full h-12 bg-orange-600 hover:bg-orange-700 text-white font-semibold" data-testid="start-cooking">
                Start cooking
              </Button>
            )}
            {steps.length > 0 ? (
              steps.map((step, index) => (
                <div
                  key={index}
                  className="flex gap-4 p-4 bg-zinc-900/50 border border-zinc-800 rounded-lg"
                >
                  <div className="w-8 h-8 rounded-full bg-orange-600 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-bold text-white">{index + 1}</span>
                  </div>
                  <div className="pt-1">
                    <p className="text-zinc-300">{step}</p>
                    {setup.plan && stepCooksProtein(step, setup.type) && (
                      <p className="mt-2 text-xs text-orange-300" data-testid="step-plan-note">
                        Your plan: {setup.plan.stages.map((s) => `${fmtLabel(s.seconds)}${s.perSide ? ' per side' : ''}`).join(' + ')}
                        {setup.plan.tempC && !setup.plan.heat.includes('Oven') ? ` at ${showTemp(setup.plan.tempC)}` : ''}, until {showTemp(setup.plan.internalC)} in the centre
                      </p>
                    )}
                    {setup.afOn && setup.afSteps[index] && !(setup.plan && stepCooksProtein(step, setup.type)) && (
                      <p className="mt-2 text-xs text-orange-300" data-testid="step-af-note">
                        🍟 Air fryer: {showTemp(setup.afSteps[index].tempC)}{setup.afSteps[index].kind === 'cook' ? `, ${fmtLabel(setup.afSteps[index].seconds)}` : ' (preheat 3 min)'}
                      </p>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <p className="text-zinc-500 text-center py-8">No instructions available</p>
            )}
            
            {servings > originalServings * 1.5 && (
              <div className="p-4 bg-orange-600/10 border border-orange-600/30 rounded-lg">
                <p className="text-orange-400 text-sm">
                  <strong>Tip:</strong> For larger batches, you may need to increase cooking time by 15-30% 
                  and consider using larger cookware.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Images Tab Content */}
        {activeTab === 'images' && (
          <div className="space-y-6" data-testid="images-gallery">
            {/* Upload Button */}
            <div 
              className="border-2 border-dashed border-zinc-700 rounded-xl p-6 text-center hover:border-orange-600 transition-colors cursor-pointer"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
              {uploadingImage ? (
                <div className="flex flex-col items-center gap-2">
                  <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                  <p className="text-zinc-400">Uploading...</p>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload className="w-8 h-8 text-zinc-500" />
                  <p className="text-zinc-400">Click to upload your photos of this dish</p>
                  <p className="text-xs text-zinc-600">Share your creation with the community!</p>
                </div>
              )}
            </div>

            {/* Gallery Grid */}
            {galleryImages.length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {galleryImages.map((img, index) => (
                  <div key={img.image_id || index} className="relative group rounded-lg overflow-hidden">
                    <img loading="lazy" decoding="async"
                      src={img.image_url}
                      alt={`Recipe photo ${index + 1}`}
                      className="w-full h-40 object-cover"
                      onError={onImageError}
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-900/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="absolute bottom-2 left-2 right-2">
                        <p className="text-xs text-zinc-300 truncate">By {img.user_name || 'Anonymous'}</p>
                      </div>
                      <button
                        onClick={() => handleDeleteGalleryImage(img.image_id)}
                        className="absolute top-2 right-2 p-1.5 bg-red-600/80 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                        title="Delete image"
                      >
                        <Trash2 className="w-4 h-4 text-white" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <ImageIcon className="w-12 h-12 text-zinc-700 mx-auto mb-3" />
                <p className="text-zinc-500">No photos yet</p>
                <p className="text-xs text-zinc-600">Be the first to share your creation!</p>
              </div>
            )}
          </div>
        )}

        {/* Tags */}
        {recipe.tags && recipe.tags.length > 0 && (
          <div className="mt-8 pt-8 border-t border-zinc-800">
            <h3 className="font-semibold text-zinc-100 mb-4">Tags</h3>
            <div className="flex flex-wrap gap-2">
              {recipe.tags.map((tag, idx) => (
                <span key={idx} className="px-3 py-1 bg-zinc-800 text-zinc-300 rounded-full text-sm">
                  {tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Source and credits */}
        <SourceCredit recipe={recipe} />
        {(recipe.visibility === 'public' || recipe.user_id === 'system_seeder') && (
          <Comments recipeId={recipe.recipe_id} isOwner={!!currentUser && recipe.user_id === currentUser.user_id} />
        )}

        {/* Similar Recipes from Community DB */}
        {(loadingSimilar || similarRecipes.length > 0) && (
          <div className="mt-8 pt-8 border-t border-zinc-800">
            <h3 className="font-semibold text-zinc-100 mb-4 flex items-center gap-2">
              <ChefHat className="w-5 h-5 text-orange-500" />
              Similar Recipes
            </h3>

            {loadingSimilar ? (
              <div className="flex items-center gap-2 text-zinc-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Finding similar recipes...
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {similarRecipes.map(similar => (
                  <div
                    key={similar.community_recipe_id}
                    className="group bg-zinc-900 border border-zinc-800/50 rounded-xl overflow-hidden hover:border-orange-600/50 transition-colors"
                  >
                    {/* Image */}
                    <div className="relative h-28 overflow-hidden bg-zinc-800">
                      {similar.image ? (
                        <img loading="lazy" decoding="async"
                          src={similar.image}
                          alt={similar.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          onError={e => { e.target.style.display = 'none'; }}
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <ChefHat className="w-8 h-8 text-zinc-600" />
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="p-2.5">
                      <p className="text-xs font-medium text-zinc-200 line-clamp-2 mb-1.5 group-hover:text-orange-400 transition-colors">
                        {similar.title}
                      </p>
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-zinc-600">
                          {similar.prep_time || similar.cook_time || '—'}
                        </span>
                        <button
                          onClick={() => saveCommunityRecipe(similar.community_recipe_id, similar.title)}
                          className="text-[10px] px-1.5 py-0.5 bg-orange-600/20 hover:bg-orange-600 text-orange-400 hover:text-white border border-orange-600/40 rounded transition-colors"
                        >
                          + Save
                        </button>
                      </div>
                    </div>
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

export default RecipeDetail;
