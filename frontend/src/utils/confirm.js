// In-app confirm dialog (replaces the browser's plain window.confirm, which looks poor on phones).
// Usage: if (!(await askConfirm('Delete this?'))) return;
export const askConfirm = (message, { confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger = true } = {}) =>
  new Promise((resolve) => {
    if (typeof document === 'undefined') { resolve(false); return; }
    const overlay = document.createElement('div');
    overlay.setAttribute('data-testid', 'confirm-dialog');
    overlay.setAttribute('role', 'alertdialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.style.cssText = 'position:fixed;inset:0;z-index:100000;background:rgba(0,0,0,.65);display:flex;align-items:center;justify-content:center;padding:16px;';
    const box = document.createElement('div');
    box.style.cssText = 'background:#18181b;color:#f4f4f5;border:1px solid #3f3f46;border-radius:16px;max-width:380px;width:100%;padding:20px;font-family:inherit;box-shadow:0 20px 50px rgba(0,0,0,.5);';
    const p = document.createElement('p');
    p.textContent = message;
    p.style.cssText = 'margin:0 0 18px;font-size:15px;line-height:1.45;';
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:10px;justify-content:flex-end;';
    const mk = (label, bg, testid) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      b.setAttribute('data-testid', testid);
      b.style.cssText = `min-height:44px;padding:0 18px;border-radius:10px;border:1px solid #52525b;background:${bg};color:#fff;font-size:14px;font-weight:600;cursor:pointer;`;
      return b;
    };
    const cancel = mk(cancelLabel, 'transparent', 'confirm-cancel');
    const ok = mk(confirmLabel, danger ? '#dc2626' : '#ea580c', 'confirm-ok');
    ok.style.borderColor = 'transparent';
    const done = (v) => { document.removeEventListener('keydown', onKey); overlay.remove(); resolve(v); };
    const onKey = (e) => { if (e.key === 'Escape') done(false); };
    cancel.onclick = () => done(false);
    ok.onclick = () => done(true);
    overlay.onclick = (e) => { if (e.target === overlay) done(false); };
    document.addEventListener('keydown', onKey);
    row.append(cancel, ok);
    box.append(p, row);
    overlay.append(box);
    document.body.append(overlay);
    cancel.focus();
  });
