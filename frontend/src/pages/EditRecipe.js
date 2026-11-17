import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Plus, Trash2, Camera, Loader2, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { compressImage } from '../utils/imageValidator';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const authHeaders = () => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};

const EditRecipe = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState(null);
  const [issues, setIssues] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/recipes/${id}`, { headers: authHeaders() });
        if (!res.ok) throw new Error();
        const r = await res.json();
        setForm({
          title: r.title || '', description: r.description || '', prep_time: r.prep_time || '', cook_time: r.cook_time || '',
          servings: r.servings || 4, difficulty: r.difficulty || 'Easy', image: r.image || '',
          ingredients: (r.ingredients || []).map(i => ({ amount: i.amount || '', item: i.item || i.name || '' })),
          steps: r.steps?.length ? r.steps : [''],
        });
        const c = await fetch(`${API_URL}/api/recipes/${id}/publish-check`, { headers: authHeaders() });
        if (c.ok) setIssues((await c.json()).issues || []);
      } catch (e) {
        toast.error('Could not open this recipe.'); navigate('/recipes');
      }
    })();
  }, [id, navigate]);

  if (!form) return <div className="min-h-screen bg-[#09090b] flex items-center justify-center"><Loader2 className="w-6 h-6 animate-spin text-zinc-400" /></div>;

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const setRow = (k, i, v) => setForm(f => ({ ...f, [k]: f[k].map((x, n) => (n === i ? v : x)) }));
  const addRow = (k, blank) => setForm(f => ({ ...f, [k]: [...f[k], blank] }));
  const delRow = (k, i) => setForm(f => ({ ...f, [k]: f[k].filter((_, n) => n !== i) }));

  const pickPhoto = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      try { set('image', await compressImage(reader.result, 1000)); }
      catch (e) { toast.error('Could not use that photo.'); }
    };
    reader.readAsDataURL(file);
  };

  const save = async () => {
    setSaving(true);
    try {
      const body = {
        ...form, servings: parseInt(form.servings, 10) || 4,
        ingredients: form.ingredients.filter(i => i.item.trim()),
        steps: form.steps.map(s => s.trim()).filter(Boolean),
      };
      const res = await fetch(`${API_URL}/api/recipes/${id}`, { method: 'PUT', headers: authHeaders(), body: JSON.stringify(body) });
      if (!res.ok) throw new Error();
      toast.success('Saved');
      navigate(`/recipe/${id}`);
    } catch (e) { toast.error('Could not save. Please try again.'); }
    finally { setSaving(false); }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-28">
      <div className="max-w-2xl mx-auto px-4 pt-20 space-y-6">
        <h1 className="font-display text-3xl font-bold">Edit recipe</h1>

        {issues.length > 0 && (
          <div className="rounded-lg border border-amber-600/40 bg-amber-600/10 p-4" data-testid="edit-issues">
            <p className="flex items-center gap-2 text-amber-300 text-sm font-medium mb-2"><AlertCircle className="w-4 h-4" /> To share this recipe publicly, fix:</p>
            <ul className="list-disc pl-5 space-y-1 text-sm text-amber-100">{issues.map((i, n) => <li key={n}>{i.message}</li>)}</ul>
          </div>
        )}

        <div className="space-y-2"><label className="text-sm text-zinc-400">Name</label>
          <Input value={form.title} onChange={e => set('title', e.target.value)} className="bg-zinc-900 border-zinc-800" data-testid="edit-title" /></div>
        <div className="space-y-2"><label className="text-sm text-zinc-400">Description</label>
          <Textarea value={form.description} onChange={e => set('description', e.target.value)} rows={3} className="bg-zinc-900 border-zinc-800" data-testid="edit-description" /></div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2"><label className="text-sm text-zinc-400">Prep time</label><Input value={form.prep_time} onChange={e => set('prep_time', e.target.value)} placeholder="15 min" className="bg-zinc-900 border-zinc-800" /></div>
          <div className="space-y-2"><label className="text-sm text-zinc-400">Cook time</label><Input value={form.cook_time} onChange={e => set('cook_time', e.target.value)} placeholder="30 min" className="bg-zinc-900 border-zinc-800" /></div>
          <div className="space-y-2"><label className="text-sm text-zinc-400">Servings</label><Input type="number" min="1" value={form.servings} onChange={e => set('servings', e.target.value)} className="bg-zinc-900 border-zinc-800" /></div>
          <div className="space-y-2"><label className="text-sm text-zinc-400">Difficulty</label>
            <select value={form.difficulty} onChange={e => set('difficulty', e.target.value)} className="w-full h-10 rounded-md bg-zinc-900 border border-zinc-800 px-3 text-sm">
              <option>Easy</option><option>Medium</option><option>Hard</option></select></div>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Photo (your own)</label>
          {form.image ? <img src={form.image} alt="" className="w-full max-h-64 object-cover rounded-lg" /> : <div className="h-32 rounded-lg border border-dashed border-zinc-700 flex items-center justify-center text-zinc-500 text-sm">No photo yet</div>}
          <div className="flex gap-3">
            <label className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-sm cursor-pointer">
              <Camera className="w-4 h-4" /> {form.image ? 'Change photo' : 'Add photo'}
              <input type="file" accept="image/*" className="hidden" onChange={e => pickPhoto(e.target.files?.[0])} data-testid="edit-photo" />
            </label>
            {form.image && <Button variant="outline" size="sm" onClick={() => set('image', '')} className="border-zinc-700 text-zinc-300">Remove</Button>}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Ingredients</label>
          {form.ingredients.map((ing, i) => (
            <div key={i} className="flex gap-2">
              <Input value={ing.amount} onChange={e => setRow('ingredients', i, { ...ing, amount: e.target.value })} placeholder="2 cups" className="w-28 bg-zinc-900 border-zinc-800" />
              <Input value={ing.item} onChange={e => setRow('ingredients', i, { ...ing, item: e.target.value })} placeholder="flour" className="flex-1 bg-zinc-900 border-zinc-800" />
              <button onClick={() => delRow('ingredients', i)} className="text-zinc-500 hover:text-red-400 px-2" aria-label="Remove ingredient"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => addRow('ingredients', { amount: '', item: '' })} className="border-zinc-700 text-zinc-300"><Plus className="w-4 h-4 mr-1" /> Add ingredient</Button>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-zinc-400">Method</label>
          {form.steps.map((s, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-zinc-500 pt-2 w-6 text-right">{i + 1}.</span>
              <Textarea value={s} onChange={e => setRow('steps', i, e.target.value)} rows={2} className="flex-1 bg-zinc-900 border-zinc-800" />
              <button onClick={() => delRow('steps', i)} className="text-zinc-500 hover:text-red-400 px-2" aria-label="Remove step"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => addRow('steps', '')} className="border-zinc-700 text-zinc-300"><Plus className="w-4 h-4 mr-1" /> Add step</Button>
        </div>

        <div className="flex gap-3 pt-2">
          <Button onClick={save} disabled={saving} className="flex-1 bg-orange-600 hover:bg-orange-700 text-white h-12" data-testid="edit-save">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save changes'}</Button>
          <Button variant="outline" onClick={() => navigate(`/recipe/${id}`)} className="border-zinc-700 text-zinc-300 h-12">Cancel</Button>
        </div>
      </div>
    </div>
  );
};

export default EditRecipe;
