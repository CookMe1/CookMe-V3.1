import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Camera, Flag, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card } from './ui/card';
import { askConfirm } from '../utils/confirm';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const authHeaders = () => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};
const ago = (iso) => {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m || 1} min ago`;
  if (m < 1440) return `${Math.round(m / 60)} h ago`;
  return `${Math.round(m / 1440)} d ago`;
};

// Photos people shared of dishes they cooked. Pass recipeId to show only one recipe's posts.
const MadePosts = ({ recipeId, refreshKey = 0, title = 'Shared by the community' }) => {
  const [posts, setPosts] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(async () => {
    try {
      const q = recipeId ? `&recipe_id=${encodeURIComponent(recipeId)}` : '';
      const r = await fetch(`${API_URL}/api/social/made?limit=20${q}`, { headers: authHeaders() });
      const j = await r.json();
      setPosts(j.posts || []);
    } catch (e) { setPosts([]); }
    setLoaded(true);
  }, [recipeId]);

  useEffect(() => { load(); }, [load, refreshKey]);

  const remove = async (id) => {
    if (!(await askConfirm('Delete this post?'))) return;
    const r = await fetch(`${API_URL}/api/social/made/${id}`, { method: 'DELETE', headers: authHeaders() });
    if (r.ok) { setPosts(p => p.filter(x => x.post_id !== id)); toast.success('Deleted'); } else toast.error('Could not delete');
  };
  const report = async (id) => {
    if (!(await askConfirm('Report this post to the moderators?'))) return;
    const r = await fetch(`${API_URL}/api/social/made/${id}/report`, { method: 'POST', headers: authHeaders(), body: JSON.stringify({ reason: 'other' }) });
    toast[r.ok ? 'success' : 'error'](r.ok ? 'Thank you. We will review it.' : 'Could not send the report');
  };

  if (!loaded || posts.length === 0) return recipeId || !loaded ? null : (
    <div className="mb-6 text-center py-8 border border-dashed border-zinc-800 rounded-xl" data-testid="made-empty">
      <Camera className="w-8 h-8 text-zinc-700 mx-auto mb-2" />
      <p className="text-zinc-400 text-sm">Nothing shared yet. Be the first!</p>
    </div>
  );

  return (
    <div className="mb-8" data-testid="made-posts">
      <h2 className="font-display text-2xl font-bold text-zinc-100 mb-3">{title}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {posts.map(p => (
          <Card key={p.post_id} className="bg-zinc-900 border-zinc-800 overflow-hidden">
            <img loading="lazy" decoding="async" src={p.photo_url ? `${API_URL}${p.photo_url}` : (p.recipe_image || '')} alt={`${p.recipe_title} made by ${p.author_name}`} className="w-full h-56 object-cover" />
            <div className="p-4">
              <p className="text-sm text-zinc-400"><span className="text-zinc-200 font-semibold">{p.author_name}</span> {p.kind === 'made' ? 'made' : 'shared'} <Link to={`/recipe/${p.recipe_id}`} className="text-orange-400 hover:underline">{p.recipe_title}</Link></p>
              {p.note && <p className="text-zinc-300 text-sm mt-2">{p.note}</p>}
              <div className="flex items-center justify-between mt-3 text-xs text-zinc-500">
                <span>{ago(p.created_at)}</span>
                {p.mine ? (
                  <button type="button" onClick={() => remove(p.post_id)} className="flex items-center gap-1 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /> Delete</button>
                ) : (
                  <button type="button" onClick={() => report(p.post_id)} className="flex items-center gap-1 hover:text-amber-400"><Flag className="w-3.5 h-3.5" /> Report</button>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default MadePosts;
