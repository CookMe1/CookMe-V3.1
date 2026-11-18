// Remember where the person was heading (e.g. a recipe shared from Facebook) so sign-in can send them back.
const KEY = 'cookme_return_to';

export const saveReturnPath = (path) => {
  try {
    if (path && path.startsWith('/') && !path.startsWith('/login') && !path.startsWith('/auth')) {
      localStorage.setItem(KEY, JSON.stringify({ path, t: Date.now() }));
    }
  } catch (e) { /* private mode */ }
};

// Returns the saved path (valid for 30 minutes) and clears it; falls back to /dashboard.
export const takeReturnPath = (fallback = '/dashboard') => {
  try {
    const raw = localStorage.getItem(KEY);
    localStorage.removeItem(KEY);
    if (raw) {
      const { path, t } = JSON.parse(raw);
      if (path && Date.now() - t < 30 * 60 * 1000) return path;
    }
  } catch (e) { /* ignore */ }
  return fallback;
};
