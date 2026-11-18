import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AccountRestricted from './AccountRestricted';
import { saveReturnPath } from '../utils/returnPath';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-600 mb-4 shadow-lg shadow-orange-500/20 animate-pulse">
            <span className="text-white font-bold text-2xl">C</span>
          </div>
          <p className="text-zinc-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    saveReturnPath(location.pathname + location.search);
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user && (user.status === 'under_review' || user.status === 'banned')) {
    return <AccountRestricted status={user.status} />;
  }

  return children;
};

export default ProtectedRoute;