import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Clock, Users, ChefHat, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useAuth } from '../context/AuthContext';
import LoadingScreen from '../components/LoadingScreen';
import BottomNavigation from '../components/BottomNavigation';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ============================================================================
// MASTER LIST OF CURATED FEATURED RECIPES
// These rotate daily - high quality recipes with good images
// ============================================================================
const MASTER_FEATURED_LIST = [
  {
    id: 'featured-1',
    title: 'Creamy Tuscan Chicken',
    description: 'A rich and creamy Italian-inspired chicken dish with sun-dried tomatoes and spinach',
    image: 'https://images.unsplash.com/photo-1598103442097-8b74394b95c6?w=800',
    prepTime: '15 min',
    cookTime: '25 min',
    servings: 4,
    difficulty: 'Medium',
  },
  {
    id: 'featured-2',
    title: 'Classic Beef Stew',
    description: 'Hearty comfort food with tender beef and root vegetables',
    image: 'https://images.unsplash.com/photo-1539114870285-2f39f0c83e9a?w=800',
    prepTime: '20 min',
    cookTime: '2 hours',
    servings: 6,
    difficulty: 'Medium',
  },
  {
    id: 'featured-3',
    title: 'Thai Green Curry',
    description: 'Aromatic coconut curry with vegetables and your choice of protein',
    image: 'https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=800',
    prepTime: '15 min',
    cookTime: '25 min',
    servings: 4,
    difficulty: 'Medium',
  },
  {
    id: 'featured-4',
    title: 'Mediterranean Salmon',
    description: 'Baked salmon with olives, tomatoes, and fresh herbs',
    image: 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=800',
    prepTime: '10 min',
    cookTime: '20 min',
    servings: 4,
    difficulty: 'Easy',
  },
  {
    id: 'featured-5',
    title: 'Mushroom Risotto',
    description: 'Creamy Italian rice dish with mixed mushrooms and parmesan',
    image: 'https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=800',
    prepTime: '10 min',
    cookTime: '35 min',
    servings: 4,
    difficulty: 'Medium',
  },
  {
    id: 'featured-6',
    title: 'Chicken Tikka Masala',
    description: 'Classic Indian curry with tender chicken in rich tomato sauce',
    image: 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=800',
    prepTime: '30 min',
    cookTime: '30 min',
    servings: 4,
    difficulty: 'Medium',
  },
  {
    id: 'featured-7',
    title: 'Pasta Carbonara',
    description: 'Traditional Roman pasta with eggs, cheese, and pancetta',
    image: 'https://images.unsplash.com/photo-1612874742237-6526221588e3?w=800',
    prepTime: '10 min',
    cookTime: '15 min',
    servings: 4,
    difficulty: 'Medium',
  },
  {
    id: 'featured-8',
    title: 'Korean Bibimbap',
    description: 'Colorful rice bowl with vegetables, egg, and gochujang',
    image: 'https://images.unsplash.com/photo-1553163147-622ab57be1c7?w=800',
    prepTime: '30 min',
    cookTime: '20 min',
    servings: 2,
    difficulty: 'Medium',
  },
  {
    id: 'featured-9',
    title: 'Shakshuka',
    description: 'Middle Eastern eggs poached in spiced tomato sauce',
    image: 'https://images.unsplash.com/photo-1590412200988-a436970781fa?w=800',
    prepTime: '10 min',
    cookTime: '20 min',
    servings: 4,
    difficulty: 'Easy',
  },
  {
    id: 'featured-10',
    title: 'Lamb Tagine',
    description: 'Moroccan slow-cooked lamb with apricots and almonds',
    image: 'https://images.unsplash.com/photo-1511690743698-d9d85f2fbf38?w=800',
    prepTime: '20 min',
    cookTime: '2 hours',
    servings: 6,
    difficulty: 'Medium',
  },
  {
    id: 'featured-11',
    title: 'Pad Thai',
    description: 'Classic Thai stir-fried noodles with shrimp and peanuts',
    image: 'https://images.unsplash.com/photo-1559314809-0d155014e29e?w=800',
    prepTime: '20 min',
    cookTime: '15 min',
    servings: 4,
    difficulty: 'Medium',
  },
  {
    id: 'featured-12',
    title: 'Butter Chicken',
    description: 'Creamy and mild Indian chicken curry',
    image: 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=800',
    prepTime: '20 min',
    cookTime: '30 min',
    servings: 4,
    difficulty: 'Easy',
  },
  {
    id: 'featured-13',
    title: 'Beef Tacos',
    description: 'Mexican street-style tacos with seasoned beef and fresh toppings',
    image: 'https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?w=800',
    prepTime: '15 min',
    cookTime: '20 min',
    servings: 4,
    difficulty: 'Easy',
  },
  {
    id: 'featured-14',
    title: 'Chicken Parmesan',
    description: 'Crispy breaded chicken with marinara and melted cheese',
    image: 'https://images.unsplash.com/photo-1632778149955-e80f8ceca2e8?w=800',
    prepTime: '20 min',
    cookTime: '25 min',
    servings: 4,
    difficulty: 'Medium',
  },
];

// Side dishes that rotate alongside main featured
const SIDE_FEATURED_LIST = [
  {
    id: 'side-1',
    title: 'Avocado Toast with Poached Egg',
    image: 'https://images.unsplash.com/photo-1541519227354-08fa5d50c44d?w=800',
    prepTime: '10 min',
  },
  {
    id: 'side-2',
    title: 'Caesar Salad',
    image: 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=800',
    prepTime: '15 min',
  },
  {
    id: 'side-3',
    title: 'Chocolate Lava Cake',
    image: 'https://images.unsplash.com/photo-1624353365286-3f8d62daad51?w=800',
    prepTime: '25 min',
  },
  {
    id: 'side-4',
    title: 'Greek Salad',
    image: 'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800',
    prepTime: '10 min',
  },
  {
    id: 'side-5',
    title: 'Garlic Bread',
    image: 'https://images.unsplash.com/photo-1619535860434-ba1d8fa12536?w=800',
    prepTime: '15 min',
  },
  {
    id: 'side-6',
    title: 'Tiramisu',
    image: 'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=800',
    prepTime: '30 min',
  },
  {
    id: 'side-7',
    title: 'Bruschetta',
    image: 'https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=800',
    prepTime: '15 min',
  },
  {
    id: 'side-8',
    title: 'Mango Lassi',
    image: 'https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=800',
    prepTime: '5 min',
  },
  {
    id: 'side-9',
    title: 'Spring Rolls',
    image: 'https://images.unsplash.com/photo-1548507200-573a1c0aa2a5?w=800',
    prepTime: '30 min',
  },
  {
    id: 'side-10',
    title: 'Hummus with Pita',
    image: 'https://images.unsplash.com/photo-1577805947697-89e18249d767?w=800',
    prepTime: '15 min',
  },
];

/**
 * Get featured recipes for today based on the date
 * Changes daily at midnight
 */
function getTodaysFeatured() {
  // Get day of year (1-365)
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 0);
  const diff = now - start;
  const oneDay = 1000 * 60 * 60 * 24;
  const dayOfYear = Math.floor(diff / oneDay);
  
  // Rotate through master list based on day of year
  const mainIndex = dayOfYear % MASTER_FEATURED_LIST.length;
  const sideIndex1 = (dayOfYear * 2) % SIDE_FEATURED_LIST.length;
  const sideIndex2 = (dayOfYear * 2 + 1) % SIDE_FEATURED_LIST.length;
  
  return {
    main: MASTER_FEATURED_LIST[mainIndex],
    side: [
      SIDE_FEATURED_LIST[sideIndex1],
      SIDE_FEATURED_LIST[sideIndex2]
    ]
  };
}

const Dashboard = () => {
  const { user } = useAuth();
  const [showLoading, setShowLoading] = useState(true);
  const [recentRecipes, setRecentRecipes] = useState([]);
  const [loadingRecipes, setLoadingRecipes] = useState(true);
  const [featuredRecipe, setFeaturedRecipe] = useState(MASTER_FEATURED_LIST[0]);
  const [sideFeatured, setSideFeatured] = useState(SIDE_FEATURED_LIST.slice(0, 2));

  // Fetch featured recipes from community DB (falls back to hardcoded if DB empty)
  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        if (!token) return;
        const res = await fetch(`${API_URL}/api/community/recipes/featured?count=3`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          const recipes = data.recipes || [];
          if (recipes.length >= 1) {
            setFeaturedRecipe({
              id: recipes[0].community_recipe_id,
              title: recipes[0].title,
              description: recipes[0].description || '',
              image: recipes[0].image || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=1920',
              prepTime: recipes[0].prep_time || '—',
              cookTime: recipes[0].cook_time || '—',
              servings: recipes[0].servings || 4,
              difficulty: recipes[0].difficulty || 'Medium',
              isCommunity: true,
            });
          }
          if (recipes.length >= 3) {
            setSideFeatured([
              { id: recipes[1].community_recipe_id, title: recipes[1].title, image: recipes[1].image || SIDE_FEATURED_LIST[0].image, prepTime: recipes[1].prep_time || '—', isCommunity: true },
              { id: recipes[2].community_recipe_id, title: recipes[2].title, image: recipes[2].image || SIDE_FEATURED_LIST[1].image, prepTime: recipes[2].prep_time || '—', isCommunity: true },
            ]);
          }
        }
      } catch (e) {
        // Falls back to hardcoded list silently
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
          const validRecipes = (data.recipes || []).filter(r => r.image && r.image.length > 10);
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
        
        {/* Logo */}
        <div className="absolute top-6 left-6 md:left-8">
          <span className="font-handwriting text-3xl text-orange-500">CookMe</span>
        </div>
        
        {/* New Recipe Button */}
        <div className="absolute top-6 right-6 md:right-8">
          <Link to="/add-recipe">
            <Button 
              className="bg-orange-600 hover:bg-orange-700 text-white px-6 h-11 font-medium btn-glow"
              data-testid="new-recipe-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Recipe
            </Button>
          </Link>
        </div>
        
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
              to={`/recipes`}
              className="lg:col-span-2 group"
              data-testid="featured-recipe"
            >
              <div className="relative h-[350px] rounded-2xl overflow-hidden">
                <img 
                  src={featuredRecipe.image}
                  alt={featuredRecipe.title}
                  className="absolute inset-0 w-full h-full object-cover img-zoom"
                />
                <div className="absolute inset-0 gradient-overlay-subtle" />
                <div className="absolute bottom-0 left-0 right-0 p-6">
                  <span className="inline-block px-3 py-1 bg-orange-600 text-white text-xs font-semibold rounded-full mb-3">
                    Chef's Pick
                  </span>
                  <h3 className="font-display text-2xl md:text-3xl font-semibold text-zinc-100 mb-2">
                    {featuredRecipe.title}
                  </h3>
                  <p className="text-zinc-400 text-sm flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {featuredRecipe.prepTime}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {featuredRecipe.servings} servings
                    </span>
                    <span className="flex items-center gap-1">
                      <ChefHat className="w-4 h-4" />
                      {featuredRecipe.difficulty}
                    </span>
                  </p>
                </div>
              </div>
            </Link>
            
            {/* Side Featured */}
            <div className="flex flex-col gap-4">
              {sideFeatured.map((recipe, index) => (
                <Link 
                  key={recipe.id}
                  to={`/recipes`}
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
                      <p className="text-xs text-zinc-500">{recipe.prepTime}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

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
              { name: 'Student', icon: '🎓', count: 42, path: '/recipes?category=student', desc: 'Quick & Easy' },
              { name: '30 Minutes', icon: '⚡', count: 67, path: '/recipes?category=quick', desc: 'Fast Cooking' },
              { name: 'Instapot', icon: '🍲', count: 31, path: '/recipes?category=instapot', desc: 'One Pot' },
              { name: 'Budget', icon: '💰', count: 55, path: '/recipes?category=budget', desc: 'Cost Effective' },
              { name: 'Air Fryer', icon: '🍟', count: 38, path: '/recipes?category=airfryer', desc: 'Crispy & Healthy' },
              { name: 'International', icon: '🌍', count: 120, path: '/recipes?filter=cuisine', desc: 'World Cuisines' }
            ].map((category) => (
              <Link 
                key={category.name}
                to={category.path}
                data-testid={`category-${category.name.toLowerCase().replace(' ', '-')}`}
              >
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 card-hover group">
                  <div className="text-3xl mb-3">{category.icon}</div>
                  <h3 className="font-semibold text-zinc-100 group-hover:text-orange-400 transition-colors">
                    {category.name}
                  </h3>
                  <p className="text-xs text-zinc-600 mt-1">{category.desc}</p>
                  <p className="text-xs text-zinc-500 mt-2">{category.count} recipes</p>
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
