import React, { useCallback, useEffect, useState } from 'react';
import { MessageCircle, Flag, Trash2, CornerDownRight, Loader2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import ReportDialog from './ReportDialog';
import { askConfirm } from '../utils/confirm';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const headers = () => {
  const token = localStorage.getItem('token') || sessionStorage.getItem('token');
  return { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
};
const when = (iso) => {
  try { return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }); } catch (e) { return ''; }
};

const Composer = ({ onSend, placeholder, autoFocus, onCancel }) => {
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true); setError('');
    const err = await onSend(text);
    setBusy(false);
    if (err) setError(err); else setText('');
  };
  return (
    <div className="space-y-2">
      <Textarea value={text} onChange={e => { setText(e.target.value); setError(''); }} rows={2} maxLength={1000} autoFocus={autoFocus}
        placeholder={placeholder} className="bg-zinc-900 border-zinc-800" data-testid="comment-input" />
      {error && <p className="text-sm text-red-400" data-testid="comment-error">{error}</p>}
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={submit} disabled={busy || !text.trim()} className="bg-orange-600 hover:bg-orange-700 text-white" data-testid="comment-send">
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Post'}
        </Button>
        {onCancel && <Button size="sm" variant="ghost" onClick={onCancel} className="text-zinc-400">Cancel</Button>}
        <span className="text-xs text-zinc-600 ml-auto">No phone numbers, emails, links or bad language</span>
      </div>
    </div>
  );
};

const Comment = ({ c, onReply, onDelete, onReport, isReply }) => (
  <div className={isReply ? 'pl-4 border-l border-zinc-800' : ''} data-testid="comment">
    <div className="flex items-baseline gap-2">
      <span className="font-medium text-zinc-200 text-sm">{c.author_name}</span>
      <span className="text-xs text-zinc-600">{when(c.created_at)}</span>
    </div>
    <p className="text-zinc-300 text-sm whitespace-pre-wrap break-words mt-0.5">{c.text}</p>
    <div className="flex gap-4 mt-1 text-xs text-zinc-500">
      {!isReply && <button onClick={() => onReply(c.comment_id)} className="hover:text-zinc-200 inline-flex items-center gap-1"><CornerDownRight className="w-3 h-3" /> Reply</button>}
      {c.can_delete && <button onClick={() => onDelete(c.comment_id)} className="hover:text-red-400 inline-flex items-center gap-1"><Trash2 className="w-3 h-3" /> Delete</button>}
      {!c.mine && <button onClick={() => onReport(c.comment_id)} className="hover:text-amber-400 inline-flex items-center gap-1"><Flag className="w-3 h-3" /> Report</button>}
    </div>
  </div>
);

// Comments + replies + report buttons for a shared recipe.
const Comments = ({ recipeId, isOwner }) => {
  const [data, setData] = useState(null);
  const [replyTo, setReplyTo] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/social/recipes/${recipeId}/comments`, { headers: headers() });
      if (res.ok) setData(await res.json());
    } catch (e) { /* leave as is */ }
  }, [recipeId]);
  useEffect(() => { load(); }, [load]);

  const send = (parentId) => async (text) => {
    try {
      const res = await fetch(`${API_URL}/api/social/recipes/${recipeId}/comments`, {
        method: 'POST', headers: headers(), body: JSON.stringify({ text, parent_id: parentId || null }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) return typeof body.detail === 'string' ? body.detail : 'Could not post your comment.';
      setReplyTo(null); await load(); return null;
    } catch (e) { return 'Could not post your comment. Check your connection.'; }
  };

  const del = async (id) => {
    if (!(await askConfirm('Delete this comment?', { confirmLabel: 'Delete' }))) return;
    const res = await fetch(`${API_URL}/api/social/comments/${id}`, { method: 'DELETE', headers: headers() });
    if (res.ok) { toast.success('Deleted'); load(); } else toast.error('Could not delete.');
  };
  const [reporting, setReporting] = useState(null);
  const report = (id) => setReporting({ type: 'comment', id });
  const reportRecipe = () => setReporting({ type: 'recipe', id: recipeId });

  return (
    <section className="mt-10" data-testid="comments-section">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-display text-xl font-bold text-zinc-100 flex items-center gap-2">
          <MessageCircle className="w-5 h-5 text-orange-500" /> Comments{data ? ` (${data.count})` : ''}
        </h3>
        {!isOwner && (
          <button onClick={reportRecipe} className="text-xs text-zinc-500 hover:text-amber-400 inline-flex items-center gap-1" data-testid="report-recipe-btn">
            <Flag className="w-3 h-3" /> Report recipe
          </button>
        )}
      </div>

      <Composer onSend={send(null)} placeholder="Share how it turned out, or ask a question…" />

      <div className="mt-6 space-y-5">
        {!data ? <Loader2 className="w-5 h-5 animate-spin text-zinc-500" /> :
          data.comments.length === 0 ? <p className="text-zinc-500 text-sm">No comments yet. Be the first!</p> :
          data.comments.map(c => (
            <div key={c.comment_id} className="space-y-3">
              <Comment c={c} onReply={setReplyTo} onDelete={del} onReport={report} />
              {c.replies.length > 0 && (
                <div className="ml-4 space-y-3">
                  {c.replies.map(r => <Comment key={r.comment_id} c={r} isReply onReply={setReplyTo} onDelete={del} onReport={report} />)}
                </div>
              )}
              {replyTo === c.comment_id && (
                <div className="ml-4"><Composer autoFocus onSend={send(c.comment_id)} placeholder={`Reply to ${c.author_name}…`} onCancel={() => setReplyTo(null)} /></div>
              )}
            </div>
          ))}
      </div>
      <p className="text-xs text-zinc-600 mt-6 flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Comments are checked automatically and can be reported. See our community rules in the Terms.</p>
      <ReportDialog target={reporting} onClose={() => setReporting(null)} onDone={load} />
    </section>
  );
};

export default Comments;
