import React from 'react';
import { Wallet } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const config = {
  type: 'budget',
  title: 'Budget Friendly',
  subtitle: 'Good food that costs less',
  Icon: Wallet,
  gradient: 'from-yellow-700 via-amber-600 to-orange-500',
  tipsTitle: '💷 Budget tips',
  tips: [
  'Plan the week so one shop covers every meal',
  'Cook once, eat twice: batch cook and freeze portions',
  'Swap expensive cuts for thighs, mince or beans',
  'Use what is in your pantry first',
  ],
  searchLabel: 'Search budget recipes...',
  emptyLabel: 'No budget recipes found',
  userMatch: (r) => r.category === 'budget' || (r.tags || []).some((t) => ['budget', 'cheap'].includes(String(t).toLowerCase())),
  chips: [
  { label: 'All', test: () => true },
  { label: 'Vegetarian', test: (r) => (r.tags || []).some((t) => /vegetarian|vegan/i.test(String(t))) },
  { label: 'With meat', test: (r) => !(r.tags || []).some((t) => /vegetarian|vegan/i.test(String(t))) },
  ],
};

const BudgetRecipes = () => <CategoryPage config={config} />;

export default BudgetRecipes;
