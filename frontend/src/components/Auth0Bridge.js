import React, { useEffect } from 'react';
import { Auth0Provider, useAuth0 } from '@auth0/auth0-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';
import { takeReturnPath } from '../utils/returnPath';

// Email login via Auth0. Only active when REACT_APP_AUTH0_DOMAIN and REACT_APP_AUTH0_CLIENT_ID are set.
export const AUTH0_ENABLED = !!(process.env.REACT_APP_AUTH0_DOMAIN && process.env.REACT_APP_AUTH0_CLIENT_ID);
const PENDING = 'cookme_auth0_pending';

// The Login page calls this; it hands over to Auth0's own login page.
export const startAuth0Login = () => {
  try { sessionStorage.setItem(PENDING, '1'); } catch (e) { /* private mode */ }
  window.dispatchEvent(new Event('cookme:auth0-login'));
};

// While Auth0 is reading the login code from the address bar, hold the rest of the app back.
// Otherwise the router's own redirects (/ -> /dashboard -> /login) erase the code and login never finishes.
const Gate = ({ children }) => {
  const { isLoading, error } = useAuth0();
  const returning = /[?&](code|state|error)=/.test(window.location.search);
  useEffect(() => {
    if (error) toast.error(error.message || 'Login failed. Please try again.');
  }, [error]);
  if (returning && isLoading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center text-zinc-400 text-sm">
        Signing you in...
      </div>
    );
  }
  return children;
};

const Handler = () => {
  const { loginWithRedirect, isAuthenticated, isLoading, getIdTokenClaims } = useAuth0();
  const { handleOAuthCallback } = useAuth();

  useEffect(() => {
    const go = () => loginWithRedirect({ authorizationParams: { scope: 'openid profile email' } });
    window.addEventListener('cookme:auth0-login', go);
    return () => window.removeEventListener('cookme:auth0-login', go);
  }, [loginWithRedirect]);

  // After Auth0 sends the person back, swap its ID token for a CookMe session.
  useEffect(() => {
    if (isLoading || !isAuthenticated) return;
    let pending = false;
    try { pending = sessionStorage.getItem(PENDING) === '1'; } catch (e) { /* ignore */ }
    if (!pending) return;
    try { sessionStorage.removeItem(PENDING); } catch (e) { /* ignore */ }
    (async () => {
      try {
        const claims = await getIdTokenClaims();
        await handleOAuthCallback('auth0', { id_token: claims.__raw });
        window.location.replace(takeReturnPath());
      } catch (e) {
        toast.error('Could not log in. If you just signed up, verify your email first, then try again.');
      }
    })();
  }, [isLoading, isAuthenticated, getIdTokenClaims, handleOAuthCallback]);

  return null;
};

const Auth0Bridge = ({ children }) => {
  if (!AUTH0_ENABLED) return children;
  return (
    <Auth0Provider
      domain={process.env.REACT_APP_AUTH0_DOMAIN}
      clientId={process.env.REACT_APP_AUTH0_CLIENT_ID}
      authorizationParams={{ redirect_uri: window.location.origin }}
      cacheLocation="localstorage"
    >
      <Handler />
      <Gate>{children}</Gate>
    </Auth0Provider>
  );
};

export default Auth0Bridge;
