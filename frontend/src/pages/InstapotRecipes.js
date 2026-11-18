import React from 'react';
import { CookingPot } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const config = {
  type: 'instapot',
  title: 'One Pot',
  subtitle: 'One pan, one pot, less washing up',
  Icon: CookingPot,
  gradient: 'from-emerald-800 via-teal-700 to-lime-600',
  tipsTitle: '🍲 One-pot tips',
  tips: [
  'Brown meat and onions first to build flavour',
  'Layer ingredients so slow-cooking ones go in first',
  'Do not fill past the max line in a pressure cooker',
  'Let pressure release naturally for tender meat',
  ],
  searchLabel: 'Search one-pot recipes...',
  emptyLabel: 'No one-pot recipes found',
  userMatch: (r) => r.category === 'instapot' || (r.tags || []).some((t) => ['instant pot', 'one pot', 'pressure cooker', 'slow cooker', 'crockpot'].includes(String(t).toLowerCase())),
  chips: [
  { label: 'All', test: () => true },
  { label: 'One pot / pan', test: (r) => (r.tags || []).some((t) => String(t).toLowerCase() === 'one pot') },
  { label: 'Slow cooker', test: (r) => (r.tags || []).some((t) => /slow cooker|crockpot/i.test(String(t))) },
  { label: 'Instant Pot / pressure', test: (r) => (r.tags || []).some((t) => /instant pot|pressure cooker/i.test(String(t))) },
  ],
};

const InstapotRecipes = () => <CategoryPage config={config} />;

export default InstapotRecipes;
