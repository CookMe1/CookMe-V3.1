import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { CATEGORIES } from '../constants/categories';
import { Home, BookOpen, Calendar, ShoppingCart, Package, Users, User, Plus, Menu, X, LogOut } from 'lucide-react';
import { Button } from './ui/button';
import { useAuth } from '../context/AuthContext';

const Navigation = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { path: '/dashboard', label: 'Home', icon: Home },
    { path: '/recipes', label: 'Recipes', icon: BookOpen },
    { path: '/meal-planner', label: 'Planner', icon: Calendar },
    { path: '/shopping-list', label: 'Shopping', icon: ShoppingCart },
    { path: '/pantry', label: 'Pantry', icon: Package },
    { path: '/social', label: 'Social', icon: Users }
  ];

  const categoryItems = CATEGORIES.map(c => ({ path: c.path, label: c.label, icon: c.Icon }));

  return (
    <nav className="bg-zinc-950/80 backdrop-blur-xl border-b border-zinc-800 sticky top-0 z-50 hidden md:block">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
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

          {/* Right Side */}
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
              <div className="absolute top-full right-0 mt-1 w-48 bg-zinc-900 rounded-lg shadow-xl border border-zinc-800 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                <Link
                  to="/profile"
                  className="flex items-center space-x-2 px-4 py-3 hover:bg-zinc-800 rounded-t-lg text-zinc-300 hover:text-zinc-100"
                >
                  <User className="w-4 h-4" />
                  <span className="text-sm">Profile</span>
                </Link>
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

          {/* Mobile Menu Button */}
          <button
            className="lg:hidden p-2 rounded-lg text-zinc-400 hover:bg-zinc-800"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-zinc-800 bg-zinc-950">
          <div className="px-4 py-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center space-x-3 px-3 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-zinc-800 text-orange-500'
                      : 'text-zinc-400 hover:bg-zinc-800'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.label}</span>
                </Link>
              );
            })}
            
            <div className="pt-2 pb-2">
              <p className="px-3 text-xs font-semibold text-zinc-600 uppercase tracking-wider mb-2">Categories</p>
              {categoryItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center space-x-3 px-3 py-2 rounded-lg text-zinc-400 hover:bg-zinc-800"
                  >
                    <Icon className="w-4 h-4 text-orange-500" />
                    <span className="text-sm">{item.label}</span>
                  </Link>
                );
              })}
            </div>
            
            <Link
              to="/add-recipe"
              onClick={() => setMobileMenuOpen(false)}
              className="block"
            >
              <Button className="w-full bg-orange-600 hover:bg-orange-700 text-white mt-3">
                <Plus className="w-5 h-5 mr-2" />
                Add Recipe
              </Button>
            </Link>
            
            <button
              onClick={() => {
                logout();
                setMobileMenuOpen(false);
              }}
              className="flex items-center space-x-3 px-3 py-3 rounded-lg text-zinc-400 hover:bg-zinc-800 w-full text-left mt-2"
            >
              <LogOut className="w-5 h-5" />
              <span className="font-medium">Logout</span>
            </button>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navigation;
