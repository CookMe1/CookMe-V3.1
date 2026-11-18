import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Loader2, Sparkles } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const headers = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('token')}`,
});

// AI-made recipes that someone has cooked: check them, pick a free photo, publish to the shared library.
const AiRecipeReview = () => {
  const [items, setItems] = useState(null);
  const [photosOk, setPhotosOk] = useState(true);
  const [open, setOpen] = useState(null);       // recipe_id being reviewed
  const [photos, setPhotos] = useState({});     // recipe_id -> candidates
  const [pick, setPick] = useState({});         // recipe_id -> chosen photo
  const [busy, setBusy] = useState('');

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/admin/ai-recipes`, { headers: headers() });
      if (!r.ok) throw new Error();
      const d = await r.json();
      setItems(d.items); setPhotosOk(d.photos_configured);
    } catch (e) { setItems([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const findPhotos = async (id) => {
    setBusy(`photos-${id}`);
    try {
      const r = await fetch(`${API_URL}/api/admin/ai-recipes/photos`, { method: 'POST', headers: headers(), body: JSON.stringify({ recipe_id: id }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Could not search for photos');
      setPhotos((p) => ({ ...p, [id]: d.photos }));
      if (!d.photos.length) toast.info('No photos found. You can publish without one.');
    } catch (e) { toast.error(e.message); }
    finally { setBusy(''); }
  };

  const act = async (id, action) => {
    setBusy(`${action}-${id}`);
    try {
      const chosen = pick[id];
      const r = await fetch(`${API_URL}/api/admin/ai-recipes/${action}`, {
        method: 'POST', headers: headers(),
        body: JSON.stringify({ recipe_id: id, image_url: chosen?.url, credit: chosen?.credit }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || 'Something went wrong');
      toast.success(action === 'approve' ? 'Published to the shared library' : 'Rejected');
      setOpen(null); load();
    } catch (e) { toast.error(e.message); }
    finally { setBusy(''); }
  };

  if (items === null || items.length === 0) return null;
  return (
    <div className="mb-8" data-testid="ai-review">
      <h2 className="font-display text-xl font-bold flex items-center gap-2 mb-1"><Sparkles className="w-5 h-5 text-purple-400" /> AI recipes ready for review ({items.length})</h2>
      <p className="text-zinc-500 text-sm mb-3">Someone cooked these. Check the method makes sense and is safe, add a free photo, then publish to the shared library for everyone.</p>
      {!photosOk && <p className="text-xs text-amber-400 mb-3">To search photos, add PIXABAY_API_KEY or PEXELS_API_KEY to the backend settings. You can still publish without a photo.</p>}
      <div className="space-y-3">
        {items.map((r) => (
          <div key={r.recipe_id} className="p-4 rounded-xl bg-zinc-900 border border-zinc-800" data-testid="ai-review-item">
            <button className="w-full text-left" onClick={() => setOpen(open === r.recipe_id ? null : r.recipe_id)}>
              <p className="font-semibold text-zinc-100">{r.title}</p>
              <p className="text-xs text-zinc-500">Cooked by {r.cooked_by} {r.cooked_by === 1 ? 'person' : 'people'} · {r.ingredients.length} ingredients · {r.steps.length} steps</p>
            </button>
            {open === r.recipe_id && (
              <div className="mt-3 space-y-3">
                <p className="text-sm text-zinc-400">{r.description}</p>
                <ul className="text-sm text-zinc-300 list-disc list-inside">
                  {r.ingredients.map((i, n) => <li key={n}>{i.amount} {i.item}</li>)}
                </ul>
                <ol className="text-sm text-zinc-300 list-decimal list-inside space-y-1">
                  {r.steps.map((s, n) => <li key={n}>{s}</li>)}
                </ol>
                <div>
                  <button
                    onClick={() => findPhotos(r.recipe_id)}
                    disabled={!!busy}
                    className="text-sm text-orange-400 underline disabled:opacity-50"
                    data-testid="find-photos"
                  >{busy === `photos-${r.recipe_id}` ? 'Searching…' : 'Find a free photo'}</button>
                  {photos[r.recipe_id]?.length > 0 && (
                    <div className="grid grid-cols-3 gap-2 mt-2">
                      {photos[r.recipe_id].map((p, n) => (
                        <button
                          key={n}
                          onClick={() => setPick((x) => ({ ...x, [r.recipe_id]: p }))}
                          className={`rounded-lg overflow-hidden border-2 ${pick[r.recipe_id]?.url === p.url ? 'border-orange-500' : 'border-transparent'}`}
                          title={p.credit}
                        >
                          <img src={p.thumb} alt="" className="w-full h-20 object-cover" />
                        </button>
                      ))}
                    </div>
                  )}
                  {pick[r.recipe_id] && <p className="text-xs text-zinc-500 mt-1">{pick[r.recipe_id].credit}. A stock photo, so it will show as illustrative.</p>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => act(r.recipe_id, 'approve')}
                    disabled={!!busy}
                    className="flex-1 h-11 rounded-lg bg-green-600 hover:bg-green-700 text-white font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                    data-testid="ai-approve"
                  >{busy === `approve-${r.recipe_id}` && <Loader2 className="w-4 h-4 animate-spin" />}Publish to library</button>
                  <button
                    onClick={() => act(r.recipe_id, 'reject')}
                    disabled={!!busy}
                    className="px-4 h-11 rounded-lg border border-zinc-700 text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
                    data-testid="ai-reject"
                  >Reject</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default AiRecipeReview;
