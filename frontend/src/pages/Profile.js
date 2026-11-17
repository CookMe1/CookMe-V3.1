import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Instagram, Facebook, Globe, BookOpen, Heart, Settings, LogOut, Loader2, ChefHat } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import LanguagePicker from '../components/LanguagePicker';
import RecipeCard from '../components/RecipeCard';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Profile = () => {
  const { userId } = useParams();
  const { user: authUser, logout } = useAuth();
  const { language } = useLanguage();
  const isOwnProfile = !userId || userId === authUser?.user_id;

  const [profileUser, setProfileUser] = useState(null);
  const [recipes, setRecipes] = useState([]);
  const [savedRecipes, setSavedRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('recipes');
  const [showLanguagePicker, setShowLanguagePicker] = useState(false);

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  useEffect(() => {
    fetchProfile();
  }, [userId]);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const token = getToken();
      const headers = { Authorization: `Bearer ${token}` };

      // Fetch user data
      const userRes = await fetch(`${API_URL}/api/auth/me`, { headers });
      if (userRes.ok) {
        const userData = await userRes.json();
        setProfileUser(userData);
      }

      // Fetch user's recipes
      const recRes = await fetch(`${API_URL}/api/recipes`, { headers });
      if (recRes.ok) {
        const recData = await recRes.json();
        setRecipes(recData);
      }

      // Fetch saved/favorited recipes
      const savRes = await fetch(`${API_URL}/api/recipes/favorites`, { headers });
      if (savRes.ok) {
        const savData = await savRes.json();
        setSavedRecipes(savData);
      }
    } catch (e) {
      toast.error('Failed to load profile');
    }
    setLoading(false);
  };

  const handleLogout = () => {
    if (logout) logout();
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    window.location.href = '/login';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  const displayUser = profileUser || authUser;

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24">
      {/* Language Picker Modal */}
      {showLanguagePicker && (
        <LanguagePicker isModal={true} onDismiss={() => setShowLanguagePicker(false)} />
      )}

      {/* Hero / Cover */}
      <div className="relative h-40 bg-gradient-to-r from-orange-700 via-orange-600 to-amber-500">
        <div className="absolute inset-0 bg-[#09090b]/30" />
        {isOwnProfile && (
          <div className="absolute top-4 right-4 flex gap-2">
            <button
              onClick={() => setShowLanguagePicker(true)}
              className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/80 hover:bg-zinc-800 rounded-lg text-sm text-zinc-300 transition-colors"
              title="Change language"
            >
              🌍 {language.name}
            </button>
            <button
              onClick={handleLogout}
              className="p-2 bg-zinc-900/80 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-red-400 transition-colors"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6">
        {/* Profile card */}
        <div className="-mt-16 mb-8">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="pt-6 pb-5">
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5">
                {/* Avatar */}
                <img
                  src={displayUser?.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(displayUser?.name || 'User')}&background=D35400&color=fff`}
                  alt={displayUser?.name}
                  className="w-24 h-24 rounded-full border-4 border-zinc-900 shadow-xl shrink-0"
                  onError={e => { e.target.src = `https://ui-avatars.com/api/?name=U&background=D35400&color=fff`; }}
                />

                {/* Info */}
                <div className="flex-1 text-center sm:text-left">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-2">
                    <div>
                      <h1 className="text-2xl font-bold text-zinc-100">{displayUser?.name}</h1>
                      <p className="text-zinc-500 text-sm">{displayUser?.email}</p>
                      {displayUser?.is_food_blogger && (
                        <span className="inline-block mt-1 px-2 py-0.5 text-xs font-semibold bg-orange-600/20 text-orange-400 rounded-full border border-orange-600/30">
                          Food Blogger
                        </span>
                      )}
                    </div>
                  </div>

                  {displayUser?.bio && (
                    <p className="text-zinc-400 text-sm mb-3">{displayUser.bio}</p>
                  )}

                  {/* Stats */}
                  <div className="flex justify-center sm:justify-start gap-6 mb-3">
                    <div className="text-center">
                      <p className="text-xl font-bold text-zinc-100">{recipes.length}</p>
                      <p className="text-xs text-zinc-500">Recipes</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xl font-bold text-zinc-100">{savedRecipes.length}</p>
                      <p className="text-xs text-zinc-500">Saved</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xl font-bold text-zinc-100">{displayUser?.followers_count || 0}</p>
                      <p className="text-xs text-zinc-500">Followers</p>
                    </div>
                  </div>

                  {/* Language preference badge */}
                  {isOwnProfile && (
                    <button
                      onClick={() => setShowLanguagePicker(true)}
                      className="inline-flex items-center gap-2 px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-sm text-zinc-300 transition-colors"
                    >
                      🌍 <span>Recipe language: <strong>{language.name}</strong></span>
                      <span className="text-xs text-zinc-500">· Change</span>
                    </button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800 mb-6 gap-1">
          {[
            { id: 'recipes', label: 'My Recipes', icon: BookOpen, count: recipes.length },
            { id: 'saved', label: 'Saved', icon: Heart, count: savedRecipes.length },
            ...(isOwnProfile ? [{ id: 'settings', label: 'Settings', icon: Settings }] : []),
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'text-orange-500 border-orange-500'
                  : 'text-zinc-500 border-transparent hover:text-zinc-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.count > 0 && (
                <span className="px-1.5 py-0.5 text-xs bg-zinc-800 text-zinc-400 rounded-full">{tab.count}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'recipes' && (
          recipes.length === 0 ? (
            <div className="text-center py-16">
              <ChefHat className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
              <p className="text-zinc-400">No recipes yet</p>
              <Link to="/add-recipe">
                <Button className="mt-4 bg-orange-600 hover:bg-orange-700">Add your first recipe</Button>
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {recipes.map(recipe => (
                <RecipeCard key={recipe.recipe_id} recipe={recipe} showDelete={isOwnProfile} />
              ))}
            </div>
          )
        )}

        {activeTab === 'saved' && (
          savedRecipes.length === 0 ? (
            <div className="text-center py-16">
              <Heart className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
              <p className="text-zinc-400">No saved recipes yet</p>
              <Link to="/recipes">
                <Button className="mt-4 bg-orange-600 hover:bg-orange-700">Browse recipes</Button>
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {savedRecipes.map(recipe => (
                <RecipeCard key={recipe.recipe_id} recipe={recipe} />
              ))}
            </div>
          )
        )}

        {activeTab === 'settings' && isOwnProfile && (
          <div className="max-w-lg space-y-4">
            {/* Language setting */}
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="pt-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-zinc-100 mb-1">Recipe Language</h3>
                    <p className="text-sm text-zinc-500">
                      Recipes are automatically translated to <strong className="text-zinc-300">{language.name}</strong> when imported.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowLanguagePicker(true)}
                    className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 rounded-lg text-sm text-zinc-300 transition-colors shrink-0 ml-4"
                  >
                    Change
                  </button>
                </div>
              </CardContent>
            </Card>

            {/* Sign out */}
            <Card className="bg-zinc-900 border-zinc-800">
              <CardContent className="pt-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-zinc-100 mb-1">Sign Out</h3>
                    <p className="text-sm text-zinc-500">Sign out of your CookMe account.</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 border border-red-600/40 rounded-lg text-sm text-red-400 transition-colors shrink-0 ml-4"
                  >
                    Sign Out
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;
