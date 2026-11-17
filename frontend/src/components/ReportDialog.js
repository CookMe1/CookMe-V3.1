import React, { useState } from 'react';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';

const API_URL = process.env.REACT_APP_BACKEND_URL;
const REASONS = [
  ['inappropriate', 'Inappropriate or offensive'], ['harassment', 'Harassment or abuse'], ['spam', 'Spam or advertising'],
  ['contact_info', 'Shares contact details'], ['copied', 'Copied from somewhere else'], ['unsafe', 'Unsafe or misleading'], ['other', 'Something else'],
];

// target: { type: 'comment' | 'recipe', id }
const ReportDialog = ({ target, onClose, onDone }) => {
  const [what, setWhat] = useState('item');
  const [reason, setReason] = useState('inappropriate');
  const [details, setDetails] = useState('');
  const [busy, setBusy] = useState(false);
  if (!target) return null;
  const noun = target.type === 'comment' ? 'comment' : 'recipe';
  const base = `${API_URL}/api/social/${target.type === 'comment' ? 'comments' : 'recipes'}/${target.id}`;

  const submit = async () => {
    setBusy(true);
    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token');
      const res = await fetch(`${base}/${what === 'user' ? 'report-user' : 'report'}`, {
        method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason, details }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Could not send the report.');
      toast.success(body.message || 'Thanks, we’ll review it.');
      onDone && onDone(); onClose();
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="bg-zinc-900 border-zinc-800 text-zinc-100 max-w-md">
        <DialogHeader>
          <DialogTitle>Report</DialogTitle>
          <DialogDescription className="text-zinc-400">Tell us what’s wrong. Only report things that break our rules; false reports can switch off your ability to report.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4" data-testid="report-dialog">
          <div className="space-y-2 text-sm">
            <label className="flex items-start gap-2 cursor-pointer"><input type="radio" checked={what === 'item'} onChange={() => setWhat('item')} className="mt-1 accent-orange-500" />
              <span>Report this {noun}{target.type === 'recipe' ? ' (it is taken down while we review it)' : ''}</span></label>
            <label className="flex items-start gap-2 cursor-pointer"><input type="radio" checked={what === 'user'} onChange={() => setWhat('user')} className="mt-1 accent-orange-500" data-testid="report-user-radio" />
              <span>Report the person who {target.type === 'comment' ? 'wrote' : 'shared'} it (their account is put under review straight away)</span></label>
          </div>
          <select value={reason} onChange={e => setReason(e.target.value)} className="w-full h-10 rounded-md bg-zinc-950 border border-zinc-800 px-3 text-sm">
            {REASONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <Textarea value={details} onChange={e => setDetails(e.target.value)} rows={3} maxLength={500} placeholder="Anything else we should know? (optional)" className="bg-zinc-950 border-zinc-800" />
          <div className="flex gap-3">
            <Button onClick={submit} disabled={busy} className="flex-1 bg-orange-600 hover:bg-orange-700 text-white" data-testid="report-submit">Send report</Button>
            <Button variant="outline" onClick={onClose} className="border-zinc-700 text-zinc-300">Cancel</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ReportDialog;
