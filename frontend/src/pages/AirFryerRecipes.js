import React from 'react';
import { Flame } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const config = {
  type: 'airfryer',
  title: 'Air Fryer',
  subtitle: 'Crispy results with little or no oil',
  Icon: Flame,
  gradient: 'from-red-700 via-orange-600 to-amber-500',
  tipsTitle: '🔥 Air fryer tips',
  tips: [
  'Preheat for 3 minutes for a crisper finish',
  'Shake the basket or turn food halfway through',
  'Do not overcrowd: one layer cooks best',
  'Oven recipes: use about 20°C lower and a quarter less time',
  ],
  searchLabel: 'Search air fryer recipes...',
  emptyLabel: 'No air fryer recipes found',
  userMatch: (r) => r.category === 'airfryer' || (r.tags || []).some((t) => ['air fryer', 'airfryer'].includes(String(t).toLowerCase())),
  chips: [
  { label: 'All', test: () => true },
  { label: 'Made for air fryers', test: (r) => !r.air_fryer_convertible },
  { label: 'Convert from oven', test: (r) => !!r.air_fryer_convertible },
  ],
};

const AirFryerRecipes = () => <CategoryPage config={config} />;

export default AirFryerRecipes;
