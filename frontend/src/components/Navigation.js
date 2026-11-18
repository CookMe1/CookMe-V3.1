import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router-dom';
import { CATEGORIES } from '../constants/categories';
import { Search, Home, BookOpen, Calendar, ShoppingCart, Package, Users, User, Plus, Menu, X, LogOut, ShieldCheck, FileText } from 'lucide-react';
import { Button } from './ui/button';
import { useAuth } from '../context/AuthContext';

const Navigation = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const navItems = [
    { path: '/dashboard', label: 'Home', icon: Home },
    { path: '/recipes', label: 'Recipes', icon: BookOpen },
    { path: '/search', label: 'Search', icon: Search },
    { path: '/meal-planner', label: 'Planner', icon: Calendar },
    { path: '/shopping-list', label: 'Shopping', icon: ShoppingCart },
    { path: '/pantry', label: 'Pantry', icon: Package },
    { path: '/social', label: 'Social', icon: Users }
  ];

  const categoryItems = CATEGORIES.map(c => ({ path: c.path, label: c.label, icon: c.Icon }));

  // Account links: the same list in the website's profile dropdown and the phone menu
  const accountItems = [
    { path: '/profile', label: 'Profile', icon: User },
    ...(user?.is_admin ? [{ path: '/admin', label: 'Admin: review reports', icon: ShieldCheck }] : []),
    { path: '/terms', label: 'Terms of Service', icon: FileText },
    { path: '/privacy', label: 'Privacy Policy', icon: FileText },
  ];

  // Close the menu when you go somewhere, press Escape, or the screen gets wide enough for the full menu
  useEffect(() => { setMenuOpen(false); }, [location.pathname]);
  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setMenuOpen(false); };
    const onResize = () => { if (window.innerWidth >= 1024) setMenuOpen(false); };
    window.addEventListener('keydown', onKey);
    window.addEventListener('resize', onResize);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';          // the page behind doesn't scroll while the menu is open
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('resize', onResize); document.body.style.overflow = prev; };
  }, [menuOpen]);

  return (
    <nav
      className="bg-zinc-950/90 backdrop-blur-xl border-b border-zinc-800 sticky top-0 z-50"
      style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}
      data-testid="top-navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14 md:h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center space-x-2" data-testid="logo-link">
            <span className="font-handwriting text-2xl text-orange-500">CookMe</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={`nav-${item.label.toLowerCase()}`}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-zinc-800 text-orange-500'
                      : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="text-sm font-medium">{item.label}</span>
                </Link>
              );
            })}

            {/* Category Dropdown */}
            <div className="relative group">
              <button className="flex items-center space-x-2 px-3 py-2 rounded-lg text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100 transition-colors">
                <BookOpen className="w-4 h-4" />
                <span className="text-sm font-medium">Categories</span>
              </button>
              <div className="absolute top-full left-0 mt-1 w-48 bg-zinc-900 rounded-lg shadow-xl border border-zinc-800 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                {categoryItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className="flex items-center space-x-2 px-4 py-3 hover:bg-zinc-800 first:rounded-t-lg last:rounded-b-lg text-zinc-300 hover:text-zinc-100"
                    >
                      <Icon className="w-4 h-4 text-orange-500" />
                      <span className="text-sm">{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Side (website) */}
          <div className="hidden lg:flex items-center space-x-3">
            <Link to="/add-recipe">
              <Button className="bg-orange-600 hover:bg-orange-700 text-white btn-glow" data-testid="nav-add-recipe">
                <Plus className="w-4 h-4 mr-2" />
                Add Recipe
              </Button>
            </Link>

            {/* User Menu */}
            <div className="relative group">
              <button className="flex items-center space-x-2 px-2 py-1 rounded-lg hover:bg-zinc-800 transition-colors">
                <img
                  src={user?.avatar || 'https://ui-avatars.com/api/?name=User&background=ea580c&color=fff'}
                  alt={user?.name || 'User'}
                  className="w-8 h-8 rounded-full ring-2 ring-zinc-700"
                />
              </button>
              <div className="absolute top-full right-0 mt-1 w-56 bg-zinc-900 rounded-lg shadow-xl border border-zinc-800 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                {accountItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link key={item.path} to={item.path} className="flex items-center space-x-2 px-4 py-3 hover:bg-zinc-800 first:rounded-t-lg text-zinc-300 hover:text-zinc-100">
                      <Icon className="w-4 h-4" />
                      <span className="text-sm">{item.label}</span>
                    </Link>
                  );
                })}
                <button
                  onClick={logout}
                  className="flex items-center space-x-2 px-4 py-3 hover:bg-zinc-800 rounded-b-lg w-full text-left text-zinc-300 hover:text-zinc-100"
                  data-testid="logout-btn"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="text-sm">Logout</span>
                </button>
              </div>
            </div>
          </div>

          {/* Three-line menu button (phones and tablets) */}
          <button
            className="lg:hidden p-2 -mr-2 rounded-lg text-zinc-300 hover:bg-zinc-800"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            data-testid="menu-button"
          >
            {menuOpen ? <X className="w-7 h-7" /> : <Menu className="w-7 h-7" />}
          </button>
        </div>
      </div>

      {/* Menu panel: same options as the website, scrolls on its own */}
      {menuOpen && createPortal(
        <>
          <div className="lg:hidden fixed inset-0 top-[var(--top-nav-h)] bg-black/50 z-[44]" onClick={() => setMenuOpen(false)} aria-hidden="true" />
          <div
            className="lg:hidden fixed inset-x-0 top-[var(--top-nav-h)] bottom-0 z-[45] overflow-y-auto overscroll-contain border-t border-zinc-800 bg-zinc-950"
            style={{ paddingBottom: 'calc(1rem + var(--bottom-nav-h))' }}
            data-testid="mobile-menu"
          >
            <div className="max-w-md mx-auto px-4 py-3 space-y-1">
              <Link to="/profile" className="flex items-center gap-3 px-3 py-3 mb-2 rounded-lg bg-zinc-900 border border-zinc-800">
                <img src={user?.avatar || 'https://ui-avatars.com/api/?name=User&background=ea580c&color=fff'} alt="" className="w-10 h-10 rounded-full ring-2 ring-zinc-700" />
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-zinc-100 truncate">{user?.name || 'Your profile'}</span>
                  <span className="block text-xs text-zinc-500">View profile</span>
                </span>
              </Link>

              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    data-testid={`menu-${item.label.toLowerCase()}`}
                    className={`flex items-center space-x-3 px-3 py-3 rounded-lg transition-colors ${isActive ? 'bg-zinc-800 text-orange-500' : 'text-zinc-300 hover:bg-zinc-800'}`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}

              <div className="pt-3 pb-1">
                <p className="px-3 text-xs font-semibold text-zinc-600 uppercase tracking-wider mb-2">Categories</p>
                {categoryItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link key={item.path} to={item.path} className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-zinc-400 hover:bg-zinc-800">
                      <Icon className="w-4 h-4 text-orange-500" />
                      <span className="text-sm">{item.label}</span>
                    </Link>
                  );
                })}
              </div>

              <Link to="/add-recipe" className="block pt-2">
                <Button className="w-full bg-orange-600 hover:bg-orange-700 text-white h-12" data-testid="menu-add-recipe">
                  <Plus className="w-5 h-5 mr-2" />
                  Add Recipe
                </Button>
              </Link>

              <div className="pt-3 mt-2 border-t border-zinc-800">
                {accountItems.filter((i) => i.path !== '/profile').map((item) => {
                  const Icon = item.icon;
                  return (
                    <Link key={item.path} to={item.path} className="flex items-center space-x-3 px-3 py-2.5 rounded-lg text-zinc-400 hover:bg-zinc-800">
                      <Icon className="w-4 h-4" />
                      <span className="text-sm">{item.label}</span>
                    </Link>
                  );
                })}
                <button
                  onClick={() => { setMenuOpen(false); logout(); }}
                  className="flex items-center space-x-3 px-3 py-3 rounded-lg text-zinc-300 hover:bg-zinc-800 w-full text-left"
                  data-testid="menu-logout"
                >
                  <LogOut className="w-5 h-5" />
                  <span className="font-medium">Logout</span>
                </button>
              </div>
            </div>
          </div>
        </>,
        document.body
      )}
    </nav>
  );
};

export default Navigation;
