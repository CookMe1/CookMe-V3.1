import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MessageCircle, Users } from 'lucide-react';
import { Card } from './ui/card';
import { PLACEHOLDER_IMAGE, onImageError } from '../utils/placeholder';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Recipes that CookMe members chose to share (they passed our checks), newest first.
const MemberRecipes = () => {
  const [recipes, setRecipes] = useState(null);
  useEffect(() => {
    (async () => {
      try {
        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        const res = await fetch(`${API_URL}/api/social/feed?limit=12`, { headers: { Authorization: `Bearer ${token}` } });
        setRecipes(res.ok ? (await res.json()).recipes || [] : []);
      } catch (e) { setRecipes([]); }
    })();
  }, []);

  if (!recipes || recipes.length === 0) return null;
  return (
    <section className="mb-8" data-testid="member-recipes">
      <h2 className="font-display text-xl font-bold text-zinc-100 mb-3 flex items-center gap-2"><Users className="w-5 h-5 text-orange-500" /> Shared by members</h2>
      <div className="flex gap-4 overflow-x-auto pb-2 -mx-4 px-4">
        {recipes.map(r => (
          <Link key={r.recipe_id} to={`/recipe/${r.recipe_id}`} className="shrink-0 w-56">
            <Card className="bg-zinc-900 border-zinc-800 overflow-hidden hover:border-zinc-700 transition-colors">
              <img src={r.image || PLACEHOLDER_IMAGE} onError={onImageError} alt={r.title} className="w-full h-36 object-cover" loading="lazy" />
              <div className="p-3">
                <p className="font-semibold text-zinc-100 text-sm line-clamp-2">{r.title}</p>
                <p className="text-xs text-zinc-500 mt-1">by {r.public_author || 'CookMe community'}</p>
                {r.share_caption && <p className="text-xs text-zinc-300 mt-1 line-clamp-2 italic">“{r.share_caption}”</p>}
                <p className="text-xs text-zinc-500 mt-1 inline-flex items-center gap-1"><MessageCircle className="w-3 h-3" /> {r.comment_count || 0}</p>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </section>
  );
};

export default MemberRecipes;
