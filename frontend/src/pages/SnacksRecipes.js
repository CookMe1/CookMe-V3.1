import React from 'react';
import { Cookie } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const has = (r, re) => (r.tags || []).some((t) => re.test(String(t)));
const config = {
  type: 'snacks',
  title: 'Snacks',
  subtitle: 'Small bites for any time of day',
  Icon: Cookie,
  gradient: 'from-amber-800 via-yellow-700 to-orange-500',
  tipsTitle: '🍿 Snack tips',
  tips: [
    'Prepare snacks in batches so they are ready when you are hungry',
    'Pair something filling (nuts, yoghurt, cheese) with something fresh',
    'Store crunchy snacks in an airtight tin',
    'Check portion sizes: the nutrition shown is per serving',
  ],
  searchLabel: 'Search snacks...',
  emptyLabel: 'No snacks found',
  userMatch: (r) => has(r, /^snack$/i),
  chips: [{ label: 'All', test: () => true }],
};

const SnacksRecipes = () => <CategoryPage config={config} />;
export default SnacksRecipes;
