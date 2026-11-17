import React, { useState, useEffect } from 'react';
import { Search, Plus, SlidersHorizontal, Share2, Loader2, Library, Star, Filter, ChefHat, Globe } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import RecipeCard from '../components/RecipeCard';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Recipes = () => {
  const location = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('recent');
  const [viewMode, setViewMode] = useState('my'); // 'my', 'master', 'favorites', 'community'
  const [communityRecipes, setCommunityRecipes] = useState([]);
  const [communityLoading, setCommunityLoading] = useState(false);
  const [communityTotal, setCommunityTotal] = useState(0);
  const [communitySkip, setCommunitySkip] = useState(0);
  
  // Filter states - initialize from URL params
  const [filterOptions, setFilterOptions] = useState({ categories: [], cuisines: [] });
  const [selectedCategory, setSelectedCategory] = useState(searchParams.get('category') || '');
  const [selectedCuisine, setSelectedCuisine] = useState(searchParams.get('cuisine') || '');
  const [showFilters, setShowFilters] = useState(!!searchParams.get('category') || !!searchParams.get('cuisine'));

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  // Fetch filter options on mount
  useEffect(() => {
    fetchFilterOptions();
  }, []);

  // Update filters from URL params when they change
  useEffect(() => {
    const categoryParam = searchParams.get('category');
    const cuisineParam = searchParams.get('cuisine');
    const filterParam = searchParams.get('filter');
    
    if (categoryParam !== null) {
      setSelectedCategory(categoryParam);
      setShowFilters(true);
    }
    if (cuisineParam !== null) {
      setSelectedCuisine(cuisineParam);
      setShowFilters(true);
    }
    // If filter=cuisine is set, just open the filter panel for international browsing
    if (filterParam === 'cuisine') {
      setShowFilters(true);
    }
  }, [searchParams]);

  // Fetch recipes from database
  useEffect(() => {
    fetchRecipes();
  }, [viewMode, selectedCategory, selectedCuisine]);

  // Fetch community recipes when that tab is active
  useEffect(() => {
    if (viewMode === 'community') {
      fetchCommunityRecipes(0);
    }
  }, [viewMode, selectedCategory, selectedCuisine]);

  const fetchCommunityRecipes = async (skip = 0) => {
    setCommunityLoading(true);
    try {
      const token = getToken();
      const params = new URLSearchParams({ limit: 24, skip });
      if (selectedCategory) params.append('category', selectedCategory);
      if (selectedCuisine) params.append('cuisine', selectedCuisine);
      if (searchQuery) params.append('search', searchQuery);
      const res = await fetch(`${API_URL}/api/community/recipes?${params}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (skip === 0) {
          setCommunityRecipes(data.recipes || []);
        } else {
          setCommunityRecipes(prev => [...prev, ...(data.recipes || [])]);
        }
        setCommunityTotal(data.total || 0);
        setCommunitySkip(skip + 24);
      }
    } catch (e) {
      console.error('Failed to fetch community recipes', e);
    }
    setCommunityLoading(false);
  };

  // Handle ingredient suggestions from photo analysis
  useEffect(() => {
    if (location.state?.suggestions) {
      toast.success(`Found ${location.state.detectedIngredients?.length || 0} ingredients! Here are some recipe ideas.`);
    }
  }, [location.state]);

  const fetchFilterOptions = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/filters/options`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setFilterOptions(data);
      }
    } catch (error) {
      console.error('Failed to fetch filter options:', error);
    }
  };

  const fetchRecipes = async () => {
    try {
      setLoading(true);
      const token = getToken();
      
      // Build query params
      const params = new URLSearchParams();
      if (selectedCategory) params.append('category', selectedCategory);
      if (selectedCuisine) params.append('cuisine', selectedCuisine);
      
      // Use different endpoint based on view mode
      let endpoint;
      if (viewMode === 'master') {
        endpoint = `${API_URL}/api/recipes/master/all`;
      } else if (viewMode === 'favorites') {
        endpoint = `${API_URL}/api/recipes/favorites`;
      } else if (viewMode === 'community') {
        // Community recipes use a different endpoint — handled separately
        return;
      } else {
        endpoint = `${API_URL}/api/recipes`;
      }
      
      const queryString = params.toString();
      if (queryString) {
        endpoint += (endpoint.includes('?') ? '&' : '?') + queryString;
      }
      
      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        // Transform database recipes to match the card component format
        const transformedRecipes = data.map(recipe => ({
          id: recipe.recipe_id,
          title: recipe.title,
          description: recipe.description,
          image: recipe.image || null,
          prepTime: recipe.prep_time,
          cookTime: recipe.cook_time,
          servings: recipe.servings,
          difficulty: recipe.difficulty,
          calories: recipe.nutrition?.calories || 0,
          author: {
            id: recipe.user_id,
            name: recipe.uploader_name || 'You',
            avatar: 'https://i.pravatar.cc/150?img=8'
          },
          uploaderId: recipe.uploader_id,
          uploaderName: recipe.uploader_name,
          category: recipe.category,
          cuisine: recipe.cuisine,
          likes: recipe.likes_count || 0,
          saves: recipe.saves_count || 0,
          isLiked: false,
          isSaved: recipe.is_favorited || false,
          isHiddenByMe: recipe.is_hidden_by_me || false,
          collections: recipe.tags || [],
          ingredients: recipe.ingredients || [],
          steps: recipe.steps || [],
          tags: recipe.tags || [],
          nutrition: recipe.nutrition,
          createdAt: recipe.created_at,
          sourceUrl: recipe.source_url
        }));
        setRecipes(transformedRecipes);
      }
    } catch (error) {
      console.error('Failed to fetch recipes:', error);
      toast.error('Failed to load recipes');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (recipeId) => {
    // Remove from local state immediately
    setRecipes(prev => prev.filter(r => r.id !== recipeId));
  };

  const handleRestore = async (recipeId) => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/${recipeId}/restore`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        toast.success('Recipe restored to your collection');
        // Update local state
        setRecipes(prev => prev.map(r => 
          r.id === recipeId ? { ...r, isHiddenByMe: false } : r
        ));
      }
    } catch (error) {
      console.error('Failed to restore recipe:', error);
      toast.error('Failed to restore recipe');
    }
  };

  const clearFilters = () => {
    setSelectedCategory('');
    setSelectedCuisine('');
    // Clear URL params
    setSearchParams({});
  };

  const filterRecipes = (recipeList) => {
    return recipeList.filter(recipe => {
      const matchesSearch = recipe.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           recipe.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           recipe.cuisine?.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSearch;
    });
  };

  const sortRecipes = (recipeList) => {
    const sorted = [...recipeList];
    if (sortBy === 'popular') {
      return sorted.sort((a, b) => (b.likes || 0) - (a.likes || 0));
    } else if (sortBy === 'recent') {
      return sorted.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0));
    } else if (sortBy === 'title') {
      return sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
    return sorted;
  };

  const filteredRecipes = sortRecipes(filterRecipes(recipes));
  const hasActiveFilters = selectedCategory || selectedCuisine;

  // Web Share API handler
  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'CookMe Recipes',
          text: 'Check out these amazing recipes on CookMe!',
          url: window.location.href
        });
      } catch (err) {
      }
    }
  };

  const getViewModeTitle = () => {
    switch(viewMode) {
      case 'favorites': return 'My Favorites';
      case 'master': return 'All Recipes';
      default: return 'My Recipes';
    }
  };

  // Get label for selected filter
  const getCategoryLabel = (value) => {
    const cat = filterOptions.categories.find(c => c.value === value);
    return cat ? cat.label : value;
  };

  const getCuisineLabel = (value) => {
    const cui = filterOptions.cuisines.find(c => c.value === value);
    return cui ? cui.label : value;
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Hero Header */}
      <div className="relative h-[30vh] min-h-[250px]">
        <img 
          src="https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=1920&h=600&fit=crop"
          alt="Recipes"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-overlay" />
        
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100 mb-2">
                {getViewModeTitle()}
              </h1>
              <p className="text-zinc-400">Your saved culinary collection ({filteredRecipes.length} recipes)</p>
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={handleShare}
                className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                data-testid="share-btn"
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Link to="/add-recipe">
                <Button 
                  className="bg-orange-600 hover:bg-orange-700 text-white btn-glow"
                  data-testid="add-recipe-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Recipe
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 md:px-8 py-8">
        {/* Ingredient Suggestions Banner */}
        {location.state?.suggestions && (
          <div className="bg-gradient-to-r from-orange-600/20 to-rose-600/20 border border-orange-600/30 rounded-xl p-6 mb-8">
            <h3 className="font-semibold text-orange-500 mb-2">Recipe Suggestions Based on Your Ingredients</h3>
            <p className="text-zinc-400 text-sm mb-4">
              Detected ingredients: {location.state.detectedIngredients?.join(', ')}
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {location.state.suggestions?.map((suggestion, idx) => (
                <div key={idx} className="bg-zinc-900/50 rounded-lg p-4">
                  <h4 className="font-medium text-zinc-100">{suggestion.name}</h4>
                  <p className="text-zinc-500 text-sm">{suggestion.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filter Buttons - Stacked on mobile, inline on desktop */}
        <div className="flex justify-center mb-6">
          <div className="flex flex-col md:flex-row gap-2 md:gap-3 w-full md:w-auto px-4 md:px-0">
            <button
              onClick={() => setViewMode('my')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all border ${
                viewMode === 'my' 
                  ? 'bg-orange-600 text-white border-orange-600' 
                  : 'bg-transparent text-zinc-400 border-zinc-700 hover:border-zinc-500 hover:text-zinc-200'
              }`}
              data-testid="my-recipes-btn"
            >
              My Recipes
            </button>
            <button
              onClick={() => setViewMode('favorites')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all border flex items-center justify-center gap-2 ${
                viewMode === 'favorites' 
                  ? 'bg-orange-600 text-white border-orange-600' 
                  : 'bg-transparent text-zinc-400 border-zinc-700 hover:border-zinc-500 hover:text-zinc-200'
              }`}
              data-testid="favorites-btn"
            >
              <Star className="w-3.5 h-3.5" />
              Favorites
            </button>
            <button
              onClick={() => setViewMode('master')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all border flex items-center justify-center gap-2 ${
                viewMode === 'master' 
                  ? 'bg-orange-600 text-white border-orange-600' 
                  : 'bg-transparent text-zinc-400 border-zinc-700 hover:border-zinc-500 hover:text-zinc-200'
              }`}
              data-testid="master-list-btn"
            >
              <Library className="w-3.5 h-3.5" />
              Master List
            </button>
            <button
              onClick={() => setViewMode('community')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all border flex items-center justify-center gap-2 ${
                viewMode === 'community' 
                  ? 'bg-orange-600 text-white border-orange-600' 
                  : 'bg-transparent text-zinc-400 border-zinc-700 hover:border-zinc-500 hover:text-zinc-200'
              }`}
              data-testid="community-btn"
            >
              <Globe className="w-3.5 h-3.5" />
              Community
            </button>
          </div>
        </div>

        {/* Search & Sort */}
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 mb-4">
          <div className="flex flex-col md:flex-row md:items-center gap-4">
            {/* Search Bar */}
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
              <Input
                type="text"
                placeholder="Search recipes by name, ingredients, or cuisine..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-12 pr-4 py-3 h-12 w-full bg-zinc-950 border-zinc-800 text-zinc-100 placeholder:text-zinc-600 focus:border-orange-600 text-base"
                data-testid="recipe-search"
              />
            </div>

            {/* Sort, Filter, and Refresh */}
            <div className="flex items-center gap-3">
              <div className="flex flex-col gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowFilters(!showFilters)}
                  className={`border-zinc-700 text-zinc-300 hover:bg-zinc-800 ${hasActiveFilters ? 'border-orange-600 text-orange-500' : ''}`}
                  data-testid="filter-toggle-btn"
                >
                  <Filter className="w-4 h-4 mr-2" />
                  Filters
                  {hasActiveFilters && (
                    <span className="ml-1 w-2 h-2 bg-orange-500 rounded-full" />
                  )}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={fetchRecipes}
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                  data-testid="refresh-btn"
                >
                  Refresh
                </Button>
              </div>

              <div className="flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-zinc-500" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="px-4 py-2 bg-zinc-950 border border-zinc-800 text-zinc-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600"
                  data-testid="sort-select"
                >
                  <option value="recent">Most Recent</option>
                  <option value="popular">Most Popular</option>
                  <option value="title">Alphabetical</option>
                </select>
              </div>
            </div>
          </div>
          
          {viewMode === 'master' && (
            <p className="text-sm text-zinc-500 mt-3">
              Viewing all recipes in the database. Hidden recipes from your collection are marked and can be restored.
            </p>
          )}
          {viewMode === 'favorites' && (
            <p className="text-sm text-zinc-500 mt-3">
              Showing recipes you've marked as favorites. Click the bookmark icon on any recipe to add it here.
            </p>
          )}
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-4 mb-6 animate-fade-in">
            <div className="flex flex-col md:flex-row gap-4">
              {/* Category Filter */}
              <div className="flex-1">
                <label className="flex items-center gap-2 text-sm font-medium text-zinc-300 mb-2">
                  <ChefHat className="w-4 h-4" />
                  Category
                </label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 text-zinc-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600"
                  data-testid="category-filter"
                >
                  <option value="">All Categories</option>
                  {filterOptions.categories.map(cat => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>

              {/* Cuisine Filter */}
              <div className="flex-1">
                <label className="flex items-center gap-2 text-sm font-medium text-zinc-300 mb-2">
                  <Globe className="w-4 h-4" />
                  Cuisine / Country
                </label>
                <select
                  value={selectedCuisine}
                  onChange={(e) => setSelectedCuisine(e.target.value)}
                  className="w-full px-4 py-2 bg-zinc-950 border border-zinc-800 text-zinc-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-600"
                  data-testid="cuisine-filter"
                >
                  <option value="">All Cuisines</option>
                  {filterOptions.cuisines.map(cui => (
                    <option key={cui.value} value={cui.value}>{cui.label}</option>
                  ))}
                </select>
              </div>

              {/* Clear Filters */}
              <div className="flex items-end">
                <Button
                  variant="outline"
                  onClick={clearFilters}
                  disabled={!hasActiveFilters}
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
                  data-testid="clear-filters-btn"
                >
                  Clear Filters
                </Button>
              </div>
            </div>

            {/* Active Filters Display */}
            {hasActiveFilters && (
              <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-zinc-800">
                <span className="text-sm text-zinc-500">Active filters:</span>
                {selectedCategory && (
                  <span className="px-3 py-1 bg-orange-600/20 text-orange-400 text-sm rounded-full flex items-center gap-1">
                    <ChefHat className="w-3 h-3" />
                    {getCategoryLabel(selectedCategory)}
                    <button onClick={() => setSelectedCategory('')} className="ml-1 hover:text-orange-300">×</button>
                  </span>
                )}
                {selectedCuisine && (
                  <span className="px-3 py-1 bg-blue-600/20 text-blue-400 text-sm rounded-full flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    {getCuisineLabel(selectedCuisine)}
                    <button onClick={() => setSelectedCuisine('')} className="ml-1 hover:text-blue-300">×</button>
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16">
            <Loader2 className="w-12 h-12 text-orange-500 animate-spin mb-4" />
            <p className="text-zinc-400">Loading your recipes...</p>
          </div>
        ) : filteredRecipes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredRecipes.map((recipe, index) => (
              <div key={recipe.id} className="animate-fade-in relative" style={{ animationDelay: `${index * 0.1}s` }}>
                {/* Hidden badge for master list view */}
                {viewMode === 'master' && recipe.isHiddenByMe && (
                  <div className="absolute top-0 left-0 right-0 z-10 bg-zinc-800/90 text-center py-2 rounded-t-xl">
                    <span className="text-sm text-zinc-400">Hidden from your collection</span>
                    <button
                      onClick={() => handleRestore(recipe.id)}
                      className="ml-2 text-sm text-orange-500 hover:text-orange-400 underline"
                    >
                      Restore
                    </button>
                  </div>
                )}
                <RecipeCard 
                  recipe={recipe} 
                  showNutrition 
                  showDelete={viewMode === 'my'}
                  onDelete={handleDelete}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800 flex items-center justify-center">
              {viewMode === 'favorites' ? <Star className="w-8 h-8 text-zinc-600" /> : <Plus className="w-8 h-8 text-zinc-600" />}
            </div>
            <p className="text-zinc-400 text-lg mb-2">
              {viewMode === 'favorites' ? 'No favorites yet' : hasActiveFilters ? 'No recipes match your filters' : 'No recipes found'}
            </p>
            <p className="text-zinc-600 mb-6">
              {viewMode === 'favorites' 
                ? 'Save recipes by clicking the bookmark icon on any recipe card!'
                : hasActiveFilters
                  ? 'Try adjusting your filters or search criteria'
                  : 'Start building your collection by adding your first recipe!'
              }
            </p>
            {hasActiveFilters ? (
              <Button onClick={clearFilters} className="bg-orange-600 hover:bg-orange-700 text-white">
                Clear Filters
              </Button>
            ) : viewMode !== 'favorites' && (
              <Link to="/add-recipe">
                <Button className="bg-orange-600 hover:bg-orange-700 text-white">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Your First Recipe
                </Button>
              </Link>
            )}
          </div>
        )}

        {/* ── Community Recipes Grid ── */}
        {viewMode === 'community' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-zinc-500 text-sm">{communityTotal.toLocaleString()} community recipes</p>
            </div>

            {communityLoading && communityRecipes.length === 0 ? (
              <div className="flex justify-center py-16">
                <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
              </div>
            ) : communityRecipes.length === 0 ? (
              <div className="text-center py-16">
                <Globe className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
                <p className="text-zinc-400">No community recipes found</p>
                <p className="text-zinc-600 text-sm mt-2">Try a different search or filter</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {communityRecipes.map(recipe => (
                    <div key={recipe.community_recipe_id} className="group bg-zinc-900 border border-zinc-800/50 rounded-xl overflow-hidden card-hover">
                      <div className="relative h-40 overflow-hidden bg-zinc-800">
                        {recipe.image ? (
                          <img src={recipe.image} alt={recipe.title} className="w-full h-full object-cover img-zoom"
                            onError={e => { e.target.style.display = 'none'; }} />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <ChefHat className="w-10 h-10 text-zinc-600" />
                          </div>
                        )}
                        <div className="absolute bottom-2 left-2">
                          <span className="px-2 py-0.5 text-xs bg-orange-600 text-white rounded-full">
                            {recipe.difficulty || 'Medium'}
                          </span>
                        </div>
                        <div className="absolute bottom-2 right-2">
                          <span className="px-2 py-0.5 text-xs bg-zinc-800/80 text-zinc-300 rounded-full">
                            Community
                          </span>
                        </div>
                      </div>
                      <div className="p-3">
                        <h3 className="font-semibold text-zinc-100 text-sm mb-1 line-clamp-1 group-hover:text-orange-400 transition-colors">
                          {recipe.title}
                        </h3>
                        <p className="text-xs text-zinc-500 line-clamp-2 mb-2">{recipe.description}</p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-zinc-600">{recipe.prep_time || '—'}</span>
                          <button
                            onClick={async () => {
                              try {
                                const token = getToken();
                                const res = await fetch(`${API_URL}/api/community/recipes/${recipe.community_recipe_id}/save`, {
                                  method: 'POST', headers: { Authorization: `Bearer ${token}` }
                                });
                                if (res.ok) {
                                  const data = await res.json();
                                  toast.success(data.already_existed ? 'Already in your collection' : 'Saved to your recipes!');
                                }
                              } catch { toast.error('Failed to save'); }
                            }}
                            className="px-2 py-1 text-xs bg-orange-600/20 hover:bg-orange-600 text-orange-400 hover:text-white border border-orange-600/40 rounded transition-colors"
                          >
                            + Save
                          </button>
                        </div>
                        {recipe.nutrition && (
                          <div className="flex gap-1.5 mt-2">
                            {[
                              { v: recipe.nutrition.calories, l: 'cal', c: 'text-orange-400' },
                              { v: `${recipe.nutrition.protein}g`, l: 'P', c: 'text-green-400' },
                              { v: `${recipe.nutrition.carbs}g`, l: 'C', c: 'text-blue-400' },
                              { v: `${recipe.nutrition.fat}g`, l: 'F', c: 'text-red-400' },
                            ].map(({ v, l, c }) => (
                              <div key={l} className="flex-1 text-center bg-zinc-800/60 rounded py-0.5">
                                <div className={`text-[10px] font-bold ${c}`}>{v}</div>
                                <div className="text-[9px] text-zinc-600">{l}</div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Load more */}
                {communityRecipes.length < communityTotal && (
                  <div className="flex justify-center mt-8">
                    <Button
                      onClick={() => fetchCommunityRecipes(communitySkip)}
                      disabled={communityLoading}
                      variant="outline"
                      className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                    >
                      {communityLoading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                      Load More ({communityTotal - communityRecipes.length} remaining)
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Recipes;
