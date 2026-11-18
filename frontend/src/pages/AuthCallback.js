import React, { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import { takeReturnPath } from '../utils/returnPath';

const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);
  const { handleOAuthCallback, checkAuth } = useAuth();

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processCallback = async () => {
      try {
        const hash = location.hash.substring(1);
        const hashParams = new URLSearchParams(hash);
        const searchParams = new URLSearchParams(location.search);
        const path = location.pathname;

        // ── Google (Emergent Auth) — session_id in hash ──────────────────
        const sessionId = hashParams.get('session_id');
        if (sessionId) {
          await handleOAuthCallback('google', { session_id: sessionId });
          await checkAuth();
          navigate(takeReturnPath(), { replace: true });
          return;
        }

        // ── Facebook / Instagram — access_token in hash ──────────────────
        const fbToken = hashParams.get('access_token');
        if (fbToken || path.includes('/auth/facebook/callback')) {
          const provider = path.includes('instagram') ? 'instagram' : 'facebook';
          await handleOAuthCallback(provider, { access_token: fbToken });
          await checkAuth();
          navigate(takeReturnPath(), { replace: true });
          return;
        }

        // ── Twitter/X — code in search params ────────────────────────────
        const twitterCode = searchParams.get('code');
        if (twitterCode || path.includes('/auth/twitter/callback')) {
          // Exchange code for token via backend (PKCE)
          await handleOAuthCallback('twitter', { access_token: twitterCode });
          await checkAuth();
          navigate(takeReturnPath(), { replace: true });
          return;
        }

        // ── Apple — id_token in search params (form_post) ────────────────
        const appleIdToken = searchParams.get('id_token');
        if (appleIdToken || path.includes('/auth/apple/callback')) {
          const userStr = searchParams.get('user');
          let appleUser = {};
          if (userStr) {
            try { appleUser = JSON.parse(userStr); } catch {}
          }
          await handleOAuthCallback('apple', { id_token: appleIdToken, user: appleUser });
          await checkAuth();
          navigate(takeReturnPath(), { replace: true });
          return;
        }

        // No recognised callback params
        navigate('/login', { replace: true });
      } catch (error) {
        toast.error('Sign in failed. Please try again.');
        navigate('/login', { replace: true });
      }
    };

    processCallback();
  }, [location, navigate, handleOAuthCallback, checkAuth]);

  return (
    <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-600 mb-4 shadow-lg shadow-orange-500/20 animate-pulse">
          <span className="text-white font-bold text-2xl">C</span>
        </div>
        <p className="text-zinc-400">Signing you in...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
