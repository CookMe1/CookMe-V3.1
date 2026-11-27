import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Sparkles, X } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const today = () => new Date().toLocaleDateString('en-CA'); // local date, e.g. 2026-11-27

/** The first time someone opens the app each day: "X new recipes added", with a button to the Latest additions section. */
const NewRecipesPopup = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [info, setInfo] = useState(null);
  const uid = user && (user.user_id || user.id || user.email);

  useEffect(() => {
    if (!uid || pathname === '/login') return;
    const dayKey = `grubly_latest_day_${uid}`;
    const seenKey = `grubly_latest_seen_${uid}`;
    try { if (localStorage.getItem(dayKey) === today()) return; } catch (e) { /* storage unavailable: just try */ }
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (!token) return;
    let live = true;
    (async () => {
      try {
        let since = '';
        try { since = localStorage.getItem(seenKey) || ''; } catch (e) { /* ignore */ }
        const res = await fetch(`${API_URL}/api/recipes/latest/summary${since ? `?since=${encodeURIComponent(since)}` : ''}`, { headers: { Authorization: `Bearer ${token}` } });
        if (!res.ok || !live) return;
        const d = await res.json();
        try { localStorage.setItem(dayKey, today()); } catch (e) { /* ignore */ }
        if (d.new_since > 0) setInfo({ n: d.new_since, asOf: d.as_of, seenKey });
      } catch (e) { /* no pop-up is better than an error */ }
    })();
    return () => { live = false; };
  }, [uid, pathname]);

  if (!info) return null;
  const close = (go) => {
    try { localStorage.setItem(info.seenKey, info.asOf); } catch (e) { /* ignore */ }
    setInfo(null);
    if (go) navigate('/latest');
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 px-6" role="dialog" aria-modal="true" data-testid="new-recipes-popup">
      <div className="relative w-full max-w-sm rounded-2xl border border-zinc-800 bg-zinc-900 p-6 text-center shadow-xl">
        <button onClick={() => close(false)} aria-label="Close" className="absolute right-3 top-3 text-zinc-500 hover:text-zinc-300"><X className="h-5 w-5" /></button>
        <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-fuchsia-600/20"><Sparkles className="h-6 w-6 text-fuchsia-400" /></div>
        <h2 className="font-display text-2xl font-bold text-zinc-100">{info.n} new {info.n === 1 ? 'recipe' : 'recipes'} added</h2>
        <p className="mt-2 text-sm text-zinc-400">Have a look at the Latest additions before they join the main library.</p>
        <button onClick={() => close(true)} data-testid="new-recipes-view" className="mt-5 w-full rounded-xl bg-orange-600 py-3 text-sm font-semibold text-white hover:bg-orange-500">See the new recipes</button>
        <button onClick={() => close(false)} className="mt-2 w-full py-2 text-sm text-zinc-500 hover:text-zinc-300">Not now</button>
      </div>
    </div>
  );
};

export default NewRecipesPopup;
