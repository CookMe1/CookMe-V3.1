import React, { useState, useEffect } from 'react';
import {
  Heart, MessageCircle, Share2, Plus, Settings,
  Image, Video, Smile, X, Globe, Users as UsersIcon,
  Loader2, ChefHat
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import { Link } from 'react-router-dom';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import MemberRecipes from '../components/MemberRecipes';
import { totalTimeLabel } from '../utils/time';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const Social = () => {
  const { user } = useAuth();
  const [showCreatePost, setShowCreatePost] = useState(false);
  const [postText, setPostText] = useState('');
  const [socialEnabled, setSocialEnabled] = useState(true);
  const [communityRecipes, setCommunityRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [likedIds, setLikedIds] = useState(new Set());
  const [savedIds, setSavedIds] = useState(new Set());

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  // Load community recipes as the social feed
  useEffect(() => {
    const fetchFeed = async () => {
      setLoading(true);
      try {
        const token = getToken();
        const res = await fetch(`${API_URL}/api/community/recipes?limit=20`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setCommunityRecipes(data.recipes || []);
        }
      } catch (e) { console.error(e); }
      setLoading(false);
    };
    fetchFeed();
  }, []);

  const handleLike = async (recipeId) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/api/community/recipes/${recipeId}/like`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setLikedIds(prev => {
          const next = new Set(prev);
          data.liked ? next.add(recipeId) : next.delete(recipeId);
          return next;
        });
        setCommunityRecipes(prev => prev.map(r =>
          r.community_recipe_id === recipeId
            ? { ...r, likes_count: (r.likes_count || 0) + (data.liked ? 1 : -1) }
            : r
        ));
      }
    } catch (e) { toast.error('Failed to like'); }
  };

  const handleSave = async (recipeId, title) => {
    try {
      const token = getToken();
      const res = await fetch(`${API_URL}/api/community/recipes/${recipeId}/save`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSavedIds(prev => { const next = new Set(prev); next.add(recipeId); return next; });
        toast.success(data.already_existed ? 'Already in your collection' : `"${title}" saved to your recipes!`);
      }
    } catch (e) { toast.error('Failed to save'); }
  };

  const handleShare = async (recipe) => {
    if (navigator.share) {
      try {
        await navigator.share({ title: recipe.title, text: recipe.description, url: window.location.href });
      } catch { /* cancelled */ }
    } else {
      navigator.clipboard?.writeText(window.location.href);
      toast.success('Link copied!');
    }
  };

  const handleCreatePost = () => {
    toast.info('Community posting coming soon — share recipes by saving them from the Recipes tab!');
    setPostText('');
    setShowCreatePost(false);
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Hero */}
      <div className="relative h-[20vh] min-h-[150px] md:h-[25vh] md:min-h-[200px]">
        <img src="https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1920&h=600&fit=crop"
          alt="Social" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 gradient-overlay" />
        <div className="absolute bottom-0 left-0 right-0 p-5 md:p-12">
          <div className="max-w-4xl mx-auto">
            <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">Community</h1>
            <p className="text-zinc-400 mt-2">Discover and save recipes from the community</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

        {/* Settings */}
        <div className="flex justify-end mb-4">
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="border-zinc-700 text-zinc-300 flex items-center gap-2">
                <Settings className="w-4 h-4" />
                Settings
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-zinc-900 border-zinc-800">
              <DialogHeader>
                <DialogTitle className="text-zinc-100">Community Settings</DialogTitle>
              </DialogHeader>
              <div className="space-y-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-zinc-100">Show Community Feed</p>
                    <p className="text-sm text-zinc-500">Discover recipes from other users</p>
                  </div>
                  <Switch checked={socialEnabled} onCheckedChange={setSocialEnabled} />
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Share a recipe: the real way to post is from a recipe page */}
        {user && (
          <Card className="mb-6 bg-zinc-900 border-zinc-800" data-testid="share-prompt">
            <CardContent className="pt-5 flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-orange-600/20 flex items-center justify-center shrink-0">
                <UsersIcon className="w-5 h-5 text-orange-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-zinc-100">Share a recipe with the community</p>
                <p className="text-sm text-zinc-500">Open one of your recipes and tap <span className="text-orange-400">Share to Social</span>.</p>
              </div>
              <Link to="/recipes" className="shrink-0 px-3 py-2 rounded-lg bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium">My recipes</Link>
            </CardContent>
          </Card>
        )}

        {/* Create post modal */}
        {showCreatePost && (
          <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
            <Card className="w-full max-w-lg bg-zinc-900 border-zinc-800">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-zinc-100">Create Post</h3>
                  <button onClick={() => setShowCreatePost(false)}>
                    <X className="w-6 h-6 text-zinc-500 hover:text-zinc-300" />
                  </button>
                </div>
                {user && (
                  <div className="flex items-center gap-3 mb-4">
                    <img loading="lazy" decoding="async" src={user.avatar || `https://ui-avatars.com/api/?name=U&background=D35400&color=fff`}
                      alt={user.name} className="w-10 h-10 rounded-full" />
                    <div>
                      <p className="font-semibold text-zinc-100">{user.name}</p>
                      <div className="flex items-center gap-1 text-xs text-zinc-500">
                        <Globe className="w-3 h-3" /><span>Public</span>
                      </div>
                    </div>
                  </div>
                )}
                <Textarea
                  value={postText}
                  onChange={e => setPostText(e.target.value)}
                  placeholder="Share a recipe, a cooking tip, or what's on your mind..."
                  className="min-h-32 mb-4 text-base bg-zinc-950 border-zinc-800 text-zinc-100"
                />
                <Button onClick={handleCreatePost} disabled={!postText.trim()}
                  className="w-full bg-orange-600 hover:bg-orange-700 text-white">
                  Post
                </Button>
              </CardContent>
            </Card>
          </div>
        )}

        <MemberRecipes />

        {/* Community feed */}
        {!socialEnabled ? (
          <Card className="bg-gradient-to-r from-orange-600/20 to-rose-600/20 border-orange-600/30">
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-orange-600 flex items-center justify-center shrink-0">
                  <UsersIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-zinc-100 mb-2">Join the Grubly Community!</h3>
                  <p className="text-zinc-400 mb-4">Discover, save and share amazing recipes from fellow food lovers.</p>
                  <Button onClick={() => setSocialEnabled(true)} className="bg-orange-600 hover:bg-orange-700 text-white">
                    Enable Community Feed
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ) : loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
          </div>
        ) : communityRecipes.length === 0 ? (
          <div className="text-center py-16">
            <ChefHat className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
            <p className="text-zinc-400">No recipes shared yet</p>
            <p className="text-zinc-600 text-sm mt-1">Be the first: share one of your recipes above.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {communityRecipes.map(recipe => {
              const rid = recipe.community_recipe_id;
              const isLiked = likedIds.has(rid);
              const isSaved = savedIds.has(rid);
              return (
                <Card key={rid} className="bg-zinc-900 border-zinc-800 overflow-hidden">
                  {/* Header */}
                  <div className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 rounded-full bg-orange-600/20 flex items-center justify-center">
                        <ChefHat className="w-5 h-5 text-orange-500" />
                      </div>
                      <div>
                        <p className="font-semibold text-zinc-100 text-sm">{recipe.attribution || 'Community Chef'}</p>
                        <p className="text-xs text-zinc-500 capitalize">{recipe.cuisine || 'International'}</p>
                      </div>
                    </div>
                    <p className="text-zinc-300 text-sm">{recipe.description || recipe.title}</p>
                  </div>

                  {/* Image */}
                  {recipe.image && (
                    <div className="relative">
                      <img loading="lazy" decoding="async" src={recipe.image} alt={recipe.title}
                        className="w-full max-h-72 object-cover"
                        onError={e => { e.target.parentElement.style.display = 'none'; }} />
                    </div>
                  )}

                  {/* Stats */}
                  <div className="px-4 py-2 flex items-center justify-between text-xs text-zinc-500 border-b border-zinc-800">
                    <div className="flex items-center gap-1">
                      <Heart className={`w-3.5 h-3.5 ${isLiked ? 'fill-red-500 text-red-500' : ''}`} />
                      <span>{(recipe.likes_count || 0).toLocaleString()}</span>
                    </div>
                    <div className="flex gap-2">
                      {totalTimeLabel(recipe) !== '—' && <span>⏱ {totalTimeLabel(recipe)}</span>}
                      {recipe.servings && <span>👥 {recipe.servings}</span>}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="px-4 py-2 flex items-center justify-around">
                    <button
                      onClick={() => handleLike(rid)}
                      className={`flex items-center gap-1.5 px-3 py-2 hover:bg-zinc-800 rounded-lg transition-colors text-sm flex-1 justify-center ${isLiked ? 'text-red-400' : 'text-zinc-400'}`}>
                      <Heart className={`w-4 h-4 ${isLiked ? 'fill-red-400' : ''}`} />
                      Like
                    </button>
                    <button
                      onClick={() => handleSave(rid, recipe.title)}
                      className={`flex items-center gap-1.5 px-3 py-2 hover:bg-zinc-800 rounded-lg transition-colors text-sm flex-1 justify-center ${isSaved ? 'text-orange-400' : 'text-zinc-400'}`}>
                      <Plus className="w-4 h-4" />
                      {isSaved ? 'Saved' : 'Save'}
                    </button>
                    <button
                      onClick={() => handleShare(recipe)}
                      className="flex items-center gap-1.5 px-3 py-2 hover:bg-zinc-800 rounded-lg transition-colors text-sm flex-1 justify-center text-zinc-400">
                      <Share2 className="w-4 h-4" />
                      Share
                    </button>
                  </div>

                  {/* Recipe preview footer */}
                  <div className="p-4 border-t border-zinc-800">
                    <p className="font-semibold text-zinc-100 text-sm mb-1">{recipe.title}</p>
                    {recipe.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {recipe.tags.slice(0, 4).map(tag => (
                          <span key={tag} className="px-2 py-0.5 text-xs bg-zinc-800 text-zinc-400 rounded-full">{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default Social;
