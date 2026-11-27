import React from 'react';
import { GlassWater } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const has = (r, re) => (r.tags || []).some((t) => re.test(String(t)));
const config = {
  type: 'drinks',
  title: 'Drinks',
  subtitle: 'Smoothies, teas, cocktails and homemade drinks',
  Icon: GlassWater,
  gradient: 'from-sky-800 via-cyan-700 to-teal-600',
  tipsTitle: '🥤 Drink tips',
  tips: [
    'Use plenty of ice for smoothies and shakes, it keeps them thick and cold',
    'Taste before sweetening: ripe fruit often needs less sugar',
    'Steep tea with water just off the boil for a smoother flavour',
    'Alcoholic drinks are for adults only. Please drink responsibly',
  ],
  searchLabel: 'Search drinks...',
  emptyLabel: 'No drinks found',
  userMatch: (r) => has(r, /^(drink|smoothie|cocktail)$/i),
  chips: [
    { label: 'All', test: () => true },
    { label: 'Smoothies', test: (r) => has(r, /^smoothie$/i) },
    { label: 'Tea', test: (r) => has(r, /^tea$/i) },
    { label: 'Juices', test: (r) => has(r, /^juice$/i) },
    { label: 'No alcohol', test: (r) => !has(r, /^alcoholic$/i) },
    { label: 'Alcoholic', test: (r) => has(r, /^alcoholic$/i) },
  ],
};

const DrinksRecipes = () => <CategoryPage config={config} />;
export default DrinksRecipes;
