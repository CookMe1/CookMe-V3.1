import React from 'react';
import { Droplets } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const has = (r, re) => (r.tags || []).some((t) => re.test(String(t)));
const config = {
  type: 'sauces',
  title: 'Sauces & Dressings',
  subtitle: 'Sauces, dressings, dips, marinades and spreads',
  Icon: Droplets,
  gradient: 'from-rose-800 via-red-700 to-orange-600',
  tipsTitle: '🥣 Sauce tips',
  tips: [
    'Make a double batch: most sauces and dressings keep in the fridge for days',
    'Whisk dressings with the oil added slowly so they stay creamy',
    'Marinate meat in the fridge, never on the counter',
    'Thin a sauce that is too thick with a little water or stock',
  ],
  searchLabel: 'Search sauces and dressings...',
  emptyLabel: 'No sauces found',
  userMatch: (r) => has(r, /^(sauce|dressing|dip|marinade|spread)$/i),
  chips: [
    { label: 'All', test: () => true },
    { label: 'Dressings', test: (r) => has(r, /^dressing$/i) },
    { label: 'Dips', test: (r) => has(r, /^dip$/i) },
    { label: 'Marinades', test: (r) => has(r, /^marinade$/i) },
    { label: 'Spreads', test: (r) => has(r, /^spread$/i) },
  ],
};

const SaucesRecipes = () => <CategoryPage config={config} />;
export default SaucesRecipes;
