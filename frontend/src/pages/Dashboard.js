import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Clock, Users, ChefHat, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import LoadingScreen from '../components/LoadingScreen';
import BottomNavigation from '../components/BottomNavigation';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Dashboard = () => {
  const { user } = useAuth();
  const [showLoading, setShowLoading] = useState(true);
  const [recentRecipes, setRecentRecipes] = useState([]);
  const [loadingRecipes, setLoadingRecipes] = useState(true);
  const [featured, setFeatured] = useState([]);

  // Featured today: a daily-stable pick from the shared master recipes
  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (!token) return;
        const res = await fetch(`${API_URL}/api/recipes/featured?count=3`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setFeatured(data.recipes || []);
        }
      } catch (e) {
        // no featured section if the request fails
      }
    };
    fetchFeatured();
  }, []);

  // Fetch recent recipes from database
  useEffect(() => {
    const fetchRecentRecipes = async () => {
      try {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (!token) {
          setLoadingRecipes(false);
          return;
        }
        
        const response = await fetch(`${API_URL}/api/recipes?limit=6`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          const validRecipes = (Array.isArray(data) ? data : (data.recipes || [])).filter(r => r.image && r.image.length > 10);
          setRecentRecipes(validRecipes.slice(0, 4));
        }
      } catch (error) {
        console.error('Error fetching recipes:', error);
      } finally {
        setLoadingRecipes(false);
      }
    };
    
    fetchRecentRecipes();
  }, []);

  if (showLoading) {
    return <LoadingScreen onComplete={() => setShowLoading(false)} />;
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Hero Section - Cinematic Style */}
      <div className="relative h-[60vh] min-h-[500px]">
        <img 
          src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=1920&h=1080&fit=crop"
          alt="Culinary hero"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-overlay" />
        
        {/* Welcome Content */}
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-7xl mx-auto">
            <p className="text-xs font-medium text-zinc-400 uppercase tracking-[3px] mb-2">
              Welcome back
            </p>
            <h1 className="font-display text-5xl md:text-7xl font-bold mb-2">
              <span className="text-orange-500">Chef</span>{' '}
              <span className="text-zinc-100">{user?.name?.split(' ')[0] || 'Friend'}</span>
            </h1>
            <p className="text-zinc-400 text-lg">Ready to cook something amazing?</p>
          </div>
        </div>
      </div>

      {/* Content Container */}
      <div className="max-w-7xl mx-auto px-6 md:px-8">
        
        {/* Featured Section - Changes Daily */}
        {featured.length > 0 && (
        <section className="py-12">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h2 className="font-display text-2xl md:text-3xl font-semibold text-zinc-100">
                Featured Today
              </h2>
              <p className="text-xs text-zinc-500 mt-1">
                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
              </p>
            </div>
            <Link to="/recipes" className="text-orange-500 hover:text-orange-400 text-sm font-medium">
              View all →
            </Link>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Featured */}
            <Link
              to={`/recipe/${featured[0].recipe_id}`}
              className="lg:col-span-2 group"
              data-testid="featured-recipe"
            >
              <div className="relative h-[350px] rounded-2xl overflow-hidden">
                <img
                  src={featured[0].image}
                  alt={featured[0].title}
                  className="absolute inset-0 w-full h-full object-cover img-zoom"
                />
                <div className="absolute inset-0 gradient-overlay-subtle" />
                <div className="absolute bottom-0 left-0 right-0 p-6">
                  <span className="inline-block px-3 py-1 bg-orange-600 text-white text-xs font-semibold rounded-full mb-3">
                    Chef's Pick
                  </span>
                  <h3 className="font-display text-2xl md:text-3xl font-semibold text-zinc-100 mb-2">
                    {featured[0].title}
                  </h3>
                  <p className="text-zinc-400 text-sm flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {featured[0].prep_time || '—'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {featured[0].servings || 4} servings
                    </span>
                    <span className="flex items-center gap-1">
                      <ChefHat className="w-4 h-4" />
                      {featured[0].difficulty || 'Medium'}
                    </span>
                  </p>
                </div>
              </div>
            </Link>

            {/* Side Featured */}
            <div className="flex flex-col gap-4">
              {featured.slice(1, 3).map((recipe, index) => (
                <Link
                  key={recipe.recipe_id}
                  to={`/recipe/${recipe.recipe_id}`}
                  className="group flex-1"
                  data-testid={`side-recipe-${index}`}
                >
                  <div className="relative h-full min-h-[165px] rounded-xl overflow-hidden">
                    <img
                      src={recipe.image}
                      alt={recipe.title}
                      className="absolute inset-0 w-full h-full object-cover img-zoom"
                    />
                    <div className="absolute inset-0 gradient-overlay-subtle" />
                    <div className="absolute bottom-0 left-0 right-0 p-4">
                      <h4 className="font-semibold text-zinc-100 group-hover:text-orange-400 transition-colors">
                        {recipe.title}
                      </h4>
                      <p className="text-xs text-zinc-500">{recipe.prep_time || '—'}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
        )}

        {/* Your Recent Recipes Section */}
        {recentRecipes.length > 0 && (
          <section className="py-12 border-t border-zinc-800/50">
            <div className="flex items-center justify-between mb-8">
              <h2 className="font-display text-2xl md:text-3xl font-semibold text-zinc-100">
                Your Recent Recipes
              </h2>
              <Link to="/recipes" className="text-orange-500 hover:text-orange-400 text-sm font-medium">
                View all →
              </Link>
            </div>
            
            {loadingRecipes ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {recentRecipes.map((recipe) => (
                  <Link 
                    key={recipe.recipe_id}
                    to={`/recipe/${recipe.recipe_id}`}
                    className="group"
                  >
                    <div className="relative h-[180px] rounded-xl overflow-hidden">
                      <img 
                        src={recipe.image}
                        alt={recipe.title}
                        className="absolute inset-0 w-full h-full object-cover img-zoom"
                      />
                      <div className="absolute inset-0 gradient-overlay-subtle" />
                      <div className="absolute bottom-0 left-0 right-0 p-3">
                        <h4 className="font-medium text-zinc-100 text-sm group-hover:text-orange-400 transition-colors line-clamp-2">
                          {recipe.title}
                        </h4>
                        <p className="text-xs text-zinc-500 mt-1">{recipe.prep_time || '30 min'}</p>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Categories Section */}
        <section className="py-12 border-t border-zinc-800/50">
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-zinc-100 mb-8">
            Browse Categories
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            {[
              { name: 'Student', icon: '🎓', path: '/student', desc: 'Quick & Easy' },
              { name: '30 Minutes', icon: '⚡', path: '/quick', desc: 'Fast Cooking' },
              { name: 'One Pot', icon: '🍲', path: '/instapot', desc: 'Instant Pot & One Pot' },
              { name: 'Budget', icon: '💰', path: '/budget', desc: 'Cost Effective' },
              { name: 'Air Fryer', icon: '🍟', path: '/airfryer', desc: 'Crispy & Healthy' },
              { name: 'All Recipes', icon: '🌍', path: '/recipes', desc: 'Browse everything' }
            ].map((category) => (
              <Link 
                key={category.name}
                to={category.path}
                data-testid={`category-${category.name.toLowerCase().replace(/ /g, '-')}`}
              >
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 card-hover group">
                  <div className="text-3xl mb-3">{category.icon}</div>
                  <h3 className="font-semibold text-zinc-100 group-hover:text-orange-400 transition-colors">
                    {category.name}
                  </h3>
                  <p className="text-xs text-zinc-600 mt-1">{category.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {/* Quick Actions */}
        <section className="py-12">
          <h2 className="font-display text-2xl md:text-3xl font-semibold text-zinc-100 mb-8">
            Quick Actions
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { name: 'Scan Ingredients', icon: '📷', path: '/add-recipe', desc: 'AI-powered' },
              { name: 'Import URL', icon: '🔗', path: '/share', desc: 'From any site' },
              { name: 'YouTube Recipe', icon: '▶️', path: '/add-recipe', desc: 'Extract from video' },
              { name: 'Meal Plan', icon: '📅', path: '/meal-planner', desc: 'Plan your week' }
            ].map((action) => (
              <Link key={action.name} to={action.path}>
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 text-center card-hover group">
                  <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-zinc-800 flex items-center justify-center text-2xl group-hover:bg-zinc-700 transition-colors">
                    {action.icon}
                  </div>
                  <h3 className="font-medium text-zinc-300 text-sm">{action.name}</h3>
                  <p className="text-xs text-zinc-600 mt-1">{action.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>

      </div>

      <BottomNavigation />
    </div>
  );
};

export default Dashboard;
