import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const authCheckRef = useRef(false);

  const checkAuth = useCallback(async () => {
    if (authCheckRef.current) return;
    authCheckRef.current = true;

    try {
      const token = localStorage.getItem('token') || sessionStorage.getItem('token');

      if (!token) {
        setIsAuthenticated(false);
        setUser(null);
        setLoading(false);
        authCheckRef.current = false;
        return;
      }

      const headers = { 'Authorization': `Bearer ${token}` };

      const response = await fetch(`${API}/auth/me`, {
        credentials: 'include',
        headers
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
        setUser(null);
        localStorage.removeItem('token');
        sessionStorage.removeItem('token');
      }
    } catch (error) {
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setLoading(false);
      authCheckRef.current = false;
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // ── Google (via Emergent Auth) ───────────────────────────────────────────

  const loginWithGoogle = () => {
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  // ── Facebook ─────────────────────────────────────────────────────────────

  const loginWithFacebook = () => {
    const appId = process.env.REACT_APP_FACEBOOK_APP_ID;
    if (!appId) {
      console.error('REACT_APP_FACEBOOK_APP_ID not set');
      return;
    }
    const redirectUri = encodeURIComponent(window.location.origin + '/auth/facebook/callback');
    window.location.href =
      `https://www.facebook.com/v19.0/dialog/oauth?client_id=${appId}&redirect_uri=${redirectUri}&scope=email,public_profile&response_type=token`;
  };

  // ── Instagram (routes through Facebook OAuth) ────────────────────────────

  const loginWithInstagram = () => {
    const appId = process.env.REACT_APP_FACEBOOK_APP_ID;
    if (!appId) {
      console.error('REACT_APP_FACEBOOK_APP_ID not set');
      return;
    }
    const redirectUri = encodeURIComponent(window.location.origin + '/auth/facebook/callback');
    window.location.href =
      `https://www.facebook.com/v19.0/dialog/oauth?client_id=${appId}&redirect_uri=${redirectUri}&scope=email,public_profile&response_type=token&auth_type=rerequest`;
  };

  // ── Twitter/X ────────────────────────────────────────────────────────────

  const loginWithTwitter = () => {
    const clientId = process.env.REACT_APP_TWITTER_CLIENT_ID;
    if (!clientId) {
      console.error('REACT_APP_TWITTER_CLIENT_ID not set');
      return;
    }
    // PKCE flow — generate code_verifier and code_challenge
    const codeVerifier = generateCodeVerifier();
    sessionStorage.setItem('twitter_code_verifier', codeVerifier);
    const redirectUri = encodeURIComponent(window.location.origin + '/auth/twitter/callback');
    // For simplicity using S256 challenge = verifier (production should hash)
    window.location.href =
      `https://twitter.com/i/oauth2/authorize?response_type=code&client_id=${clientId}&redirect_uri=${redirectUri}&scope=users.read%20tweet.read&state=cookme&code_challenge=${codeVerifier}&code_challenge_method=plain`;
  };

  // ── Apple ────────────────────────────────────────────────────────────────

  const loginWithApple = () => {
    const clientId = process.env.REACT_APP_APPLE_CLIENT_ID;
    if (!clientId) {
      console.error('REACT_APP_APPLE_CLIENT_ID not set');
      return;
    }
    const redirectUri = encodeURIComponent(window.location.origin + '/auth/apple/callback');
    window.location.href =
      `https://appleid.apple.com/auth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code%20id_token&scope=name%20email&response_mode=form_post`;
  };

  // ── Handle OAuth callbacks from all providers ────────────────────────────

  const handleOAuthCallback = useCallback(async (provider, params) => {
    try {
      let body = {};
      let endpoint = '';

      if (provider === 'google') {
        endpoint = '/auth/google/callback';
        body = { session_id: params.session_id };
      } else if (provider === 'facebook' || provider === 'instagram') {
        endpoint = '/auth/facebook/callback';
        body = { access_token: params.access_token, provider };
      } else if (provider === 'twitter') {
        endpoint = '/auth/twitter/callback';
        body = { access_token: params.access_token };
      } else if (provider === 'apple') {
        endpoint = '/auth/apple/callback';
        body = { id_token: params.id_token, user: params.user };
      }

      const response = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error('Authentication failed');
      }

      const userData = await response.json();

      if (userData.access_token) {
        localStorage.setItem('token', userData.access_token);
      }

      setUser(userData);
      setIsAuthenticated(true);
      return userData;
    } catch (error) {
      throw error;
    }
  }, []);

  // ── Logout ───────────────────────────────────────────────────────────────

  const logout = async () => {
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      // Logout API failure is non-critical
    }
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    setUser(null);
    setIsAuthenticated(false);
  };

  const value = {
    user,
    loading,
    isAuthenticated,
    loginWithGoogle,
    loginWithFacebook,
    loginWithInstagram,
    loginWithTwitter,
    loginWithApple,
    handleOAuthCallback,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Helper for Twitter PKCE
function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(36).padStart(2, '0')).join('').slice(0, 64);
}
