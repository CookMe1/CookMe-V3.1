import React from 'react';
import { Timer } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const config = {
  type: 'quick',
  title: '30 Minute Meals',
  subtitle: 'On the table fast',
  Icon: Timer,
  gradient: 'from-sky-800 via-cyan-700 to-teal-500',
  tipsTitle: '⏱️ Speed tips',
  tips: [
  'Read the whole recipe and prep everything first',
  'Chop small: smaller pieces cook faster',
  'Boil the kettle for pasta and rice water',
  'Use a wide pan so food cooks quickly',
  ],
  searchLabel: 'Search quick recipes...',
  emptyLabel: 'No quick recipes found',
  userMatch: (r) => r.category === 'quick' || (r.tags || []).some((t) => String(t).toLowerCase() === 'quick'),
  chips: [
  { label: 'All', test: () => true },
  { label: 'Vegetarian', test: (r) => (r.tags || []).some((t) => /vegetarian|vegan/i.test(String(t))) },
  { label: 'With meat', test: (r) => !(r.tags || []).some((t) => /vegetarian|vegan/i.test(String(t))) },
  ],
};

const QuickRecipes = () => <CategoryPage config={config} />;

export default QuickRecipes;
