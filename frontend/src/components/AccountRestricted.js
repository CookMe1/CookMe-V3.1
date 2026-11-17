import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { Button } from './ui/button';
import { useAuth } from '../context/AuthContext';

// Shown instead of the app when an account is under review (or closed).
const AccountRestricted = ({ status }) => {
  const { logout } = useAuth();
  const closed = status === 'banned';
  const signOut = async () => {
    try { if (logout) await logout(); } catch (e) { /* ignore */ }
    localStorage.removeItem('token'); sessionStorage.removeItem('token');
    window.location.href = '/login';
  };
  return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center px-6" data-testid="account-restricted">
      <div className="max-w-md text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-600/20 mb-6">
          <ShieldAlert className="w-8 h-8 text-amber-400" />
        </div>
        <h1 className="font-display text-2xl font-bold text-zinc-100 mb-3">
          {closed ? 'This account has been closed' : 'Your profile is under review'}
        </h1>
        <p className="text-zinc-400 mb-6 leading-relaxed">
          {closed
            ? 'This account was closed because it broke our Terms of Service.'
            : 'We received a report about your account and we’re checking it. Your account and anything you shared are paused while we look. We’ll restore everything if we find nothing wrong.'}
        </p>
        <Button onClick={signOut} variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">Log out</Button>
        <p className="text-xs text-zinc-600 mt-6">
          <a href="/terms" className="underline">Terms of Service</a> · <a href="/privacy" className="underline">Privacy Policy</a>
        </p>
      </div>
    </div>
  );
};

export default AccountRestricted;
