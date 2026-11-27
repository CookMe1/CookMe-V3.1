import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Users, Lock, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const authHeaders = () => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};

// Owner-only: make a recipe public (after our checks and the person's consent) or private again.
const ShareRecipe = ({ recipe, onChange }) => {
  const [open, setOpen] = useState(false);
  const [terms, setTerms] = useState(null);
  const [check, setCheck] = useState(null);       // { ready, issues }
  const [consent, setConsent] = useState(false);
  const [showName, setShowName] = useState(true);
  const [busy, setBusy] = useState(false);
  const [caption, setCaption] = useState('');
  const navigate = useNavigate();
  const isPublic = recipe.visibility === 'public';

  const load = useCallback(async () => {
    try {
      const [t, c] = await Promise.all([
        fetch(`${API_URL}/api/recipes/terms/public-sharing`, { headers: authHeaders() }).then(r => r.json()),
        fetch(`${API_URL}/api/recipes/${recipe.recipe_id}/publish-check`, { headers: authHeaders() }).then(r => r.json()),
      ]);
      setTerms(t); setCheck(c);
    } catch (e) {
      toast.error('Could not check the recipe. Please try again.');
    }
  }, [recipe.recipe_id]);

  useEffect(() => { if (open) { setConsent(false); load(); } }, [open, load]);

  const publish = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/recipes/${recipe.recipe_id}/publish`, {
        method: 'POST', headers: authHeaders(),
        body: JSON.stringify({ consent: true, terms_version: terms.version, show_name: showName, caption }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed');
      if (data.status === 'public') {
        toast.success('Shared to Social!', { action: { label: 'View', onClick: () => navigate('/social') } });
        setOpen(false); onChange && onChange();
      } else {
        setCheck({ ready: false, issues: data.issues });
        toast.error('A few things need fixing before this can go public.');
        onChange && onChange();
      }
    } catch (e) {
      toast.error(e.message || 'Something went wrong.');
    } finally { setBusy(false); }
  };

  const makePrivate = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/recipes/${recipe.recipe_id}/unpublish`, { method: 'POST', headers: authHeaders() });
      if (!res.ok) throw new Error();
      toast.success('Your recipe is private again.');
      onChange && onChange();
    } catch (e) { toast.error('Could not change it. Please try again.'); }
    finally { setBusy(false); }
  };

  return (
    <div className="flex flex-wrap items-center gap-3" data-testid="share-recipe">
      {isPublic ? (
        <>
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-600/20 text-green-400 text-sm font-medium">
            <Users className="w-4 h-4" /> Shared on Social
          </span>
          <Button variant="outline" size="sm" onClick={makePrivate} disabled={busy} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800" data-testid="make-private-btn">
            <Lock className="w-4 h-4 mr-2" /> Remove from Social
          </Button>
        </>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)} className="bg-orange-600 hover:bg-orange-700 text-white" data-testid="share-publicly-btn">
          <Users className="w-4 h-4 mr-2" /> Share to Social
        </Button>
      )}
      {!isPublic && recipe.publish_status === 'needs_changes' && (
        <span className="text-sm text-amber-400 flex items-center gap-1"><AlertCircle className="w-4 h-4" /> Needs changes before it can go public</span>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Share to Social</DialogTitle>
            <DialogDescription className="text-zinc-400">
              Your recipe will appear on the Social page for other Grubly members. We check every recipe first, so everyone gets one they can cook from.
            </DialogDescription>
          </DialogHeader>

          {!check || !terms ? (
            <div className="py-8 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-zinc-400" /></div>
          ) : (
            <div className="space-y-4">
              {check.ready ? (
                <p className="flex items-center gap-2 text-green-400 text-sm"><CheckCircle2 className="w-4 h-4" /> Your recipe passes all our checks.</p>
              ) : (
                <div className="rounded-lg border border-amber-600/40 bg-amber-600/10 p-3" data-testid="publish-issues">
                  <p className="text-amber-300 text-sm font-medium mb-2">Please fix these first:</p>
                  <ul className="list-disc pl-5 space-y-1 text-sm text-amber-100">
                    {check.issues.map((i, n) => <li key={n}>{i.message}</li>)}
                  </ul>
                  {!check.issues.some(i => i.field === 'source') && (
                    <Link to={`/recipe/${recipe.recipe_id}/edit`} className="inline-block mt-3 text-sm font-semibold text-orange-400 hover:text-orange-300 underline">
                      Edit recipe
                    </Link>
                  )}
                </div>
              )}

              <Textarea value={caption} onChange={e => setCaption(e.target.value)} maxLength={200} rows={2}
                placeholder="Say something about it (optional), e.g. “My nan’s Sunday soup”" className="bg-zinc-950 border-zinc-800" data-testid="share-caption" />

              <label className="flex items-start gap-3 text-sm text-zinc-300 cursor-pointer">
                <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} className="mt-1 accent-orange-500" data-testid="consent-checkbox" />
                <span>{terms.text}</span>
              </label>
              <label className="flex items-center gap-3 text-sm text-zinc-400 cursor-pointer">
                <input type="checkbox" checked={showName} onChange={e => setShowName(e.target.checked)} className="accent-orange-500" />
                Show my name on the recipe
              </label>

              <Button onClick={publish} disabled={busy || !consent || !check.ready} className="w-full bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-40" data-testid="publish-btn">
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Share to Social'}
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ShareRecipe;
