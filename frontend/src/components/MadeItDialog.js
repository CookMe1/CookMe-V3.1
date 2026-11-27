import React, { useEffect, useRef, useState } from 'react';
import { Camera, Loader2, Search } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const authHeaders = () => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};

// Shrink the photo in the browser first so uploads are quick on a phone connection.
const readPhoto = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onerror = () => reject(new Error('read'));
  reader.onload = () => {
    const img = new Image();
    img.onerror = () => reject(new Error('image'));
    img.onload = () => {
      const scale = Math.min(1, 1000 / Math.max(img.width, img.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(img.width * scale); canvas.height = Math.round(img.height * scale);
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL('image/jpeg', 0.8));
    };
    img.src = reader.result;
  };
  reader.readAsDataURL(file);
});

// "I made this": a photo and a few words about a recipe you cooked. Works for any recipe in the library, shared or your own.
const MadeItDialog = ({ open, onClose, recipe: fixed, onPosted }) => {
  const [recipe, setRecipe] = useState(fixed || null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [photo, setPhoto] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => { if (open) { setRecipe(fixed || null); setQuery(''); setResults([]); setPhoto(''); setNote(''); } }, [open, fixed]);

  useEffect(() => {
    if (!open || recipe || query.trim().length < 2) { setResults([]); return undefined; }
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`${API_URL}/api/recipes/search?q=${encodeURIComponent(query.trim())}&limit=6`, { headers: authHeaders() });
        const j = await r.json();
        setResults(j.recipes || []);
      } catch (e) { setResults([]); }
    }, 300);
    return () => clearTimeout(t);
  }, [query, recipe, open]);

  const choosePhoto = async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    try { setPhoto(await readPhoto(file)); } catch (err) { toast.error('We could not read that photo. Please try another one.'); }
  };

  const submit = async () => {
    if (!recipe) return;
    setBusy(true);
    try {
      const r = await fetch(`${API_URL}/api/social/made`, { method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ recipe_id: recipe.recipe_id, note, image_data: photo || '' }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { toast.error(typeof j.detail === 'string' ? j.detail : 'Could not share. Please try again.'); return; }
      toast.success('Shared to Social!');
      onPosted && onPosted(j);
      onClose();
    } catch (err) { toast.error('Could not share. Please try again.'); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <DialogContent className="bg-zinc-900 border-zinc-800 max-h-[90vh] overflow-y-auto" data-testid="made-it-dialog">
        <DialogHeader>
          <DialogTitle className="text-zinc-100">Share to Social</DialogTitle>
          <DialogDescription className="text-zinc-400">Share this recipe with other Grubly members. Add a photo of your own if you made it. The recipe stays in the library with its credit.</DialogDescription>
        </DialogHeader>

        {!recipe ? (
          <div>
            <label className="text-sm text-zinc-300">Which recipe do you want to share?</label>
            <div className="relative mt-1">
              <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-3" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search the recipe library, e.g. cowboy butter chicken"
                className="w-full pl-9 pr-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100" data-testid="made-it-search" />
            </div>
            <ul className="mt-2 space-y-1">
              {results.map(r => (
                <li key={r.recipe_id}>
                  <button type="button" onClick={() => setRecipe(r)} className="w-full text-left px-3 py-2 rounded-lg hover:bg-zinc-800 text-zinc-200 text-sm">{r.title}</button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-zinc-100">{recipe.title}</p>
              {!fixed && <button type="button" onClick={() => setRecipe(null)} className="text-xs text-orange-400">Change</button>}
            </div>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={choosePhoto} />
            {photo ? (
              <div className="relative">
                <img src={photo} alt="Your dish" className="w-full max-h-72 object-cover rounded-lg" />
                <button type="button" onClick={() => fileRef.current && fileRef.current.click()} className="absolute bottom-2 right-2 px-3 py-1 text-xs rounded bg-black/70 text-white">Change photo</button>
              </div>
            ) : (
              <button type="button" onClick={() => fileRef.current && fileRef.current.click()} data-testid="made-it-photo"
                className="w-full h-36 border-2 border-dashed border-zinc-700 rounded-lg flex flex-col items-center justify-center text-zinc-400 hover:border-orange-600">
                <Camera className="w-6 h-6 mb-1" /> Add a photo of your dish (optional)
              </button>
            )}
            <Textarea value={note} onChange={(e) => setNote(e.target.value.slice(0, 300))} placeholder="Say something about it (optional, no web links please)"
              className="bg-zinc-950 border-zinc-800 text-zinc-100" />
            <p className="text-xs text-zinc-500">{note.length}/300 · If you add a photo it must be your own. Others can report posts they think break the rules.</p>
            <Button onClick={submit} disabled={busy} className="w-full bg-orange-600 hover:bg-orange-700 text-white" data-testid="made-it-submit">
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Share to Social'}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default MadeItDialog;
