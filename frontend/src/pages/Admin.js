import React, { useCallback, useEffect, useState } from 'react';
import AiRecipeReview from '../components/AiRecipeReview';
import { Link, Navigate } from 'react-router-dom';
import { ArrowLeft, Loader2, ShieldCheck, Check, Trash2, Ban } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { useAuth } from '../context/AuthContext';
import { askConfirm } from '../utils/confirm';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const headers = () => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};
const when = (iso) => { try { return new Date(iso).toLocaleString(); } catch (e) { return ''; } };

const UserBlock = ({ u, title }) => (
  <div className="text-sm text-zinc-300 space-y-0.5">
    {title && <p className="text-xs uppercase tracking-wide text-zinc-500">{title}</p>}
    <p><span className="font-semibold text-zinc-100">{u.name}</span> · {u.email}</p>
    <p className="text-zinc-500">Joined {when(u.joined)} · sign-in: {u.provider || '?'} · status: {u.status}</p>
  </div>
);

const Target = ({ item }) => {
  const t = item.target;
  if (item.kind === 'user') return (
    <div className="space-y-3">
      <UserBlock u={t} title="Reported account" />
      <div className="text-sm text-zinc-400"><p className="mb-1 text-zinc-300">{t.recipe_count} recipes</p>
        <ul className="list-disc pl-5">{t.recipes.map(r => <li key={r.recipe_id}>{r.title} <span className="text-zinc-600">({r.publish_status || r.visibility})</span></li>)}</ul></div>
      {t.recent_comments.length > 0 && <div className="text-sm text-zinc-400"><p className="mb-1 text-zinc-300">Recent comments</p>
        <ul className="list-disc pl-5">{t.recent_comments.map((c, i) => <li key={i}>“{c.text}”</li>)}</ul></div>}
    </div>
  );
  if (item.kind === 'recipe') return (
    <div className="space-y-3">
      <UserBlock u={t.owner} title="Posted by" />
      <p className="font-semibold text-zinc-100">{t.title} <span className="text-xs text-zinc-500">({t.publish_status || t.visibility})</span></p>
      {t.image && <img loading="lazy" decoding="async" src={t.image} alt="" className="max-h-48 rounded-lg" />}
      <p className="text-sm text-zinc-400">{t.description}</p>
      <div className="text-sm text-zinc-400"><p className="text-zinc-300">Ingredients</p><ul className="list-disc pl-5">{(t.ingredients || []).map((i, n) => <li key={n}>{i.amount} {i.item || i.name}</li>)}</ul></div>
      <div className="text-sm text-zinc-400"><p className="text-zinc-300">Method</p><ol className="list-decimal pl-5 space-y-1">{(t.steps || []).map((s, n) => <li key={n}>{s}</li>)}</ol></div>
    </div>
  );
  return (
    <div className="space-y-3">
      <UserBlock u={t.author} title="Written by" />
      {t.photo_url && <img loading="lazy" decoding="async" src={`${API_URL}${t.photo_url}`} alt="" className="max-h-56 rounded-lg" />}
      <p className="text-zinc-100 border-l-2 border-zinc-700 pl-3">“{t.text}”</p>
      <p className="text-xs text-zinc-500">On recipe: {t.recipe_title}</p>
    </div>
  );
};

const LABEL = { user: 'Account', recipe: 'Recipe', comment: 'Comment', made_post: 'Photo post' };

const Admin = () => {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(null);
  const [errors, setErrors] = useState(null);
  const [descBusy, setDescBusy] = useState(false);
  const [aiTest, setAiTest] = useState(null);

  const load = useCallback(async () => {
    const res = await fetch(`${API_URL}/api/admin/reports`, { headers: headers() });
    if (res.ok) setData(await res.json()); else setData({ items: [], count: 0, denied: true });
  }, []);
  useEffect(() => { if (user?.is_admin) load(); }, [user, load]);

  if (authLoading) return null;
  if (!user?.is_admin) return <Navigate to="/dashboard" replace />;

  const downloadBackup = async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/backup`, { headers: headers() });
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (res.headers.get('Content-Disposition') || '').split('filename=')[1]?.replace(/"/g, '') || 'cookme-backup.jsonl.gz';
      document.body.appendChild(a); a.click(); a.remove();
      toast.success('Backup downloaded. Keep it somewhere private.');
    } catch (e) { toast.error('Backup failed. Please try again.'); }
  };

  const loadErrors = async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/errors`, { headers: headers() });
      if (res.ok) setErrors((await res.json()).errors); else toast.error('Could not load errors.');
    } catch (e) { toast.error('Could not reach the server.'); }
  };

  const testAi = async () => {
    setAiTest({ busy: true });
    try {
      const res = await fetch(`${API_URL}/api/admin/ai-test`, { method: 'POST', headers: headers() });
      setAiTest(await res.json());
    } catch (e) { setAiTest({ ok: false, error: 'Could not reach the server.' }); }
  };

  const improveDescriptions = async () => {
    setDescBusy(true);
    try {
      let left = null, total = 0;
      for (let i = 0; i < 40; i++) {                      // up to 40 batches of 25 per click
        const res = await fetch(`${API_URL}/api/admin/improve-descriptions`, { method: 'POST', headers: headers(), body: JSON.stringify({ limit: 25 }) });
        if (!res.ok) throw new Error();
        const r = await res.json();
        total += r.updated; left = r.remaining;
        toast.message(`${total} descriptions improved, ${left} left`);
        if (!r.updated || !left) break;
      }
      if (left === 0) toast.success('All library descriptions are improved.');
      else if (total === 0) toast.error('The AI did not answer. Try again later.');
    } catch (e) { toast.error('Could not improve descriptions. Please try again.'); }
    setDescBusy(false);
  };

  const sendTest = async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/test-email`, { method: 'POST', headers: headers() });
      const body = await res.json();
      if (body.sent) toast.success('Test email sent. Check your inbox (and spam).');
      else toast.error(`Email failed: ${body.error || 'unknown error'}`);
    } catch (e) { toast.error('Could not reach the server.'); }
  };

  const act = async (item, action, confirmText) => {
    if (confirmText && !(await askConfirm(confirmText))) return;
    setBusy(item.target_id + action);
    try {
      const res = await fetch(`${API_URL}/api/admin/resolve`, { method: 'POST', headers: headers(), body: JSON.stringify({ kind: item.kind, target_id: item.target_id, action }) });
      if (!res.ok) throw new Error();
      toast.success('Done'); await load();
    } catch (e) { toast.error('That did not work. Please try again.'); } finally { setBusy(null); }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-28">
      <div className="max-w-3xl mx-auto px-4 pt-20">
        <Link to="/profile" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 mb-4"><ArrowLeft className="w-4 h-4" /> Back</Link>
        <h1 className="font-display text-3xl font-bold flex items-center gap-2 mb-1"><ShieldCheck className="w-7 h-7 text-orange-500" /> Review queue</h1>
        <p className="text-zinc-500 text-sm mb-2">Reported accounts are locked and reported recipes are taken down until you decide.</p>
        <div className="flex flex-wrap gap-x-5 gap-y-1 mb-6">
          <button onClick={sendTest} className="text-xs text-orange-400 underline" data-testid="test-email-btn">Send me a test email</button>
          <button onClick={downloadBackup} className="text-xs text-orange-400 underline" data-testid="backup-btn">Download backup</button>
          <button onClick={loadErrors} className="text-xs text-orange-400 underline" data-testid="errors-btn">Show recent app errors</button>
          <button onClick={improveDescriptions} disabled={descBusy} className="text-xs text-orange-400 underline disabled:opacity-50" data-testid="improve-desc-btn">{descBusy ? 'Improving descriptions…' : 'Improve library descriptions (AI)'}</button>
          <button onClick={testAi} className="text-xs text-orange-400 underline" data-testid="ai-test-btn">Test AI model</button>
        </div>
        {aiTest && !aiTest.busy && (
          <p className={`text-xs mb-4 ${aiTest.ok ? 'text-green-400' : 'text-red-400'}`} data-testid="ai-test-result">
            {aiTest.ok ? `AI works: ${aiTest.provider} / ${aiTest.model} answered in ${aiTest.seconds}s.` : `AI test failed (${aiTest.provider} / ${aiTest.model}): ${aiTest.error || 'no answer'}`}
          </p>
        )}
        {aiTest?.busy && <p className="text-xs mb-4 text-zinc-400">Testing the AI model…</p>}
        <AiRecipeReview />
        {errors && (
          <Card className="bg-zinc-900 border-zinc-800 mb-6" data-testid="errors-list"><CardContent className="pt-5 text-xs text-zinc-400 space-y-2">
            {errors.length === 0 ? <p>No errors reported in the last 30 days. 🎉</p> : errors.map((e, i) => (
              <p key={i}><span className="text-zinc-600">{when(e.created_at)}</span> <span className="text-zinc-200">{e.message}</span> <span className="text-zinc-600">{e.url}</span></p>
            ))}
          </CardContent></Card>
        )}

        {!data ? <Loader2 className="w-6 h-6 animate-spin text-zinc-500" /> : data.items.length === 0 ? (
          <p className="text-zinc-400" data-testid="admin-empty">Nothing to review. 🎉</p>
        ) : data.items.map(item => (
          <Card key={item.kind + item.target_id} className="bg-zinc-900 border-zinc-800 mb-5" data-testid="admin-item">
            <CardContent className="pt-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold px-2 py-1 rounded bg-amber-600/20 text-amber-300">{LABEL[item.kind]} reported ({item.reports.length})</span>
                <span className="text-xs text-zinc-600">{when(item.first_reported)}</span>
              </div>
              <div className="rounded-lg bg-zinc-950 border border-zinc-800 p-3 space-y-2">
                {item.reports.map((r, i) => (
                  <p key={i} className="text-sm text-zinc-400"><span className="text-zinc-200">{r.reason}</span>{r.details ? ` — “${r.details}”` : ''} <span className="text-zinc-600">· {r.reporter}</span></p>
                ))}
              </div>
              <Target item={item} />
              <div className="flex flex-wrap gap-3 pt-2 border-t border-zinc-800">
                <Button size="sm" disabled={!!busy} onClick={() => act(item, 'reinstate')} className="bg-green-700 hover:bg-green-800 text-white" data-testid="admin-reinstate">
                  <Check className="w-4 h-4 mr-1" /> {item.kind === 'user' ? 'Reinstate account' : 'Keep it'}
                </Button>
                {item.kind !== 'user' && (
                  <Button size="sm" variant="outline" disabled={!!busy} onClick={() => act(item, 'remove', `Delete this ${item.kind}?`)} className="border-zinc-700 text-zinc-200">
                    <Trash2 className="w-4 h-4 mr-1" /> Delete {item.kind}
                  </Button>
                )}
                <Button size="sm" variant="outline" disabled={!!busy} onClick={() => act(item, 'ban', 'Delete everything this person created and block them from signing in again? This can’t be undone.')} className="border-red-900 text-red-400 hover:bg-red-950" data-testid="admin-ban">
                  <Ban className="w-4 h-4 mr-1" /> Delete & block account
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default Admin;
