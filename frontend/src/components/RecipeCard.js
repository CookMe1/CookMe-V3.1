import React from 'react';
import { Link } from 'react-router-dom';
import { Heart, Bookmark, Clock, Users, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { PLACEHOLDER_IMAGE, onImageError } from '../utils/placeholder';

// ── Nutrition mini-strip shown on every card that has nutrition data ──────────
const NutritionStrip = ({ nutrition }) => (
  <div className="flex gap-2 mt-3 pt-3 border-t border-zinc-800">
    {[
      { label: 'cal', value: nutrition.calories, color: 'text-orange-400' },
      { label: 'P', value: `${nutrition.protein}g`, color: 'text-green-400' },
      { label: 'C', value: `${nutrition.carbs}g`, color: 'text-blue-400' },
      { label: 'F', value: `${nutrition.fat}g`, color: 'text-red-400' },
    ].map(({ label, value, color }) => (
      <div key={label} className="flex-1 text-center bg-zinc-800/60 rounded-md py-1">
        <div className={`text-xs font-bold ${color}`}>{value}</div>
        <div className="text-[10px] text-zinc-600">{label}</div>
      </div>
    ))}
  </div>
);

const API_URL = process.env.REACT_APP_BACKEND_URL;

const RecipeCard = ({ recipe, showNutrition = false, onLikeChange, onSaveChange, onDelete, showDelete = false }) => {
  const [isSaved, setIsSaved] = React.useState(recipe.isSaved || false);
  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');
  // Support both recipe_id (backend) and id (legacy)
  const recipeId = recipe.recipe_id || recipe.id;

  const handleLike = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${recipeId}/like`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        toast.success(data.liked ? 'Recipe liked!' : 'Like removed');
        if (onLikeChange) onLikeChange(recipeId, data.liked);
      }
    } catch (error) {
      console.error('Failed to like recipe:', error);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${recipeId}/save`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setIsSaved(data.saved);
        toast.success(data.saved ? 'Added to favorites!' : 'Removed from favorites');
        if (onSaveChange) onSaveChange(recipeId, data.saved);
      }
    } catch (error) {
      console.error('Failed to save recipe:', error);
    }
  };

  const handleDelete = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Remove "${recipe.title}" from your collection? It will still be available in the master recipe list.`)) return;
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${recipeId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        toast.success('Recipe removed from your collection');
        if (onDelete) onDelete(recipeId);
      }
    } catch (error) {
      console.error('Failed to delete recipe:', error);
      toast.error('Failed to remove recipe');
    }
  };

  return (
    <Link to={`/recipe/${recipeId}`} data-testid={`recipe-card-${recipeId}`}>
      <div className="group bg-zinc-900 border border-zinc-800/50 rounded-xl overflow-hidden card-hover">
        {/* Image */}
        <div className="relative h-48 overflow-hidden">
          <img
            src={recipe.image || PLACEHOLDER_IMAGE}
            alt={recipe.title}
            className="w-full h-full object-cover img-zoom"
            loading="lazy"
            onError={onImageError}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-zinc-900/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          
          {/* Action Buttons */}
          <div className="absolute top-3 right-3 flex gap-2">
            <button onClick={handleLike} className="p-2 rounded-full bg-zinc-900/80 backdrop-blur-sm hover:bg-zinc-800 transition-colors" data-testid={`like-btn-${recipeId}`}>
              <Heart className={`w-4 h-4 ${recipe.isLiked ? 'fill-red-500 text-red-500' : 'text-zinc-400'}`} />
            </button>
            <button onClick={handleSave} className="p-2 rounded-full bg-zinc-900/80 backdrop-blur-sm hover:bg-zinc-800 transition-colors" data-testid={`save-btn-${recipeId}`}>
              <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-orange-500 text-orange-500' : 'text-zinc-400'}`} />
            </button>
            {showDelete && (
              <button onClick={handleDelete} className="p-2 rounded-full bg-zinc-900/80 backdrop-blur-sm hover:bg-red-900/80 transition-colors" data-testid={`delete-btn-${recipeId}`} title="Remove from my collection">
                <Trash2 className="w-4 h-4 text-zinc-400 hover:text-red-400" />
              </button>
            )}
          </div>
          
          {/* Difficulty Badge */}
          <div className="absolute bottom-3 left-3">
            <span className="px-2 py-1 text-xs font-medium bg-orange-600 text-white rounded-full">
              {recipe.difficulty || 'Medium'}
            </span>
          </div>

          {/* Cookbook badge */}
          {recipe.cookbook && (
            <div className="absolute bottom-3 right-3">
              <span className="px-2 py-1 text-xs font-medium bg-zinc-800/80 text-zinc-300 rounded-full">
                📚 {recipe.cookbook}
              </span>
            </div>
          )}

          {/* Source Badge (only when no cookbook) */}
          {!recipe.cookbook && recipe.source_url && (
            <div className="absolute bottom-3 right-3">
              <span className="px-2 py-1 text-xs font-medium bg-zinc-800/80 text-zinc-300 rounded-full">
                {recipe.source_url.includes('youtube') ? '📺 YouTube' : '🔗 Imported'}
              </span>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4">
          <h3 className="font-semibold text-zinc-100 mb-1 line-clamp-1 group-hover:text-orange-400 transition-colors">
            {recipe.title}
          </h3>
          <p className="text-sm text-zinc-500 mb-3 line-clamp-2">
            {recipe.description || 'A delicious recipe'}
          </p>

          {/* Meta Info */}
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {recipe.prep_time || recipe.prepTime || '30 min'}
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-3.5 h-3.5" />
              {recipe.servings || 4}
            </span>
          </div>

          {/* Nutrition Strip — always visible when data exists */}
          {recipe.nutrition && <NutritionStrip nutrition={recipe.nutrition} />}

          {/* Tags — only shown when no nutrition data */}
          {recipe.tags && recipe.tags.length > 0 && !recipe.nutrition && (
            <div className="flex flex-wrap gap-1 mt-3 pt-3 border-t border-zinc-800">
              {recipe.tags.slice(0, 3).map((tag, idx) => (
                <span key={idx} className="px-2 py-0.5 text-xs bg-zinc-800 text-zinc-400 rounded-full">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Author */}
          {recipe.author && (
            <div className="flex items-center justify-between mt-4 pt-3 border-t border-zinc-800">
              <div className="flex items-center gap-2">
                <img loading="lazy" decoding="async"
                  src={recipe.author.avatar || 'https://i.pravatar.cc/150?img=8'}
                  alt={recipe.author.name || 'You'}
                  className="w-6 h-6 rounded-full"
                />
                <span className="text-xs text-zinc-500">{recipe.author.name || 'You'}</span>
              </div>
              <span className="text-xs text-zinc-600">{recipe.likes || 0} likes</span>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
};

export default RecipeCard;
