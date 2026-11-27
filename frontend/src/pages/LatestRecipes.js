import React from 'react';
import { Sparkles } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const config = {
  type: 'latest',
  endpoint: '/api/recipes/latest',
  hideMine: true,
  title: 'Latest additions',
  subtitle: 'Brand-new recipes. They stay here for two weeks, then join the main library',
  Icon: Sparkles,
  gradient: 'from-violet-800 via-fuchsia-700 to-pink-600',
  tipsTitle: '✨ How this works',
  tips: [
    'We add a handful of new recipes every day',
    'New recipes show here first, newest at the top',
    'After about two weeks they move into the main library',
    'Save any you like and they stay in your collection',
  ],
  searchLabel: 'Search the latest additions...',
  emptyLabel: 'No new recipes right now. Check back tomorrow',
  userMatch: () => false,
  chips: [{ label: 'All', test: () => true }],
};

const LatestRecipes = () => <CategoryPage config={config} />;
export default LatestRecipes;
