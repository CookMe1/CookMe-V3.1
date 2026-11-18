import React from 'react';
import { GraduationCap } from 'lucide-react';
import CategoryPage from '../components/CategoryPage';

const config = {
  type: 'student',
  title: 'Student Meals',
  subtitle: 'Simple recipes with few ingredients',
  Icon: GraduationCap,
  gradient: 'from-indigo-800 via-violet-700 to-fuchsia-600',
  tipsTitle: '🎓 Student tips',
  tips: [
  'Under 10 ingredients each: short shopping list',
  'One pan, one pot: very little washing up',
  'Cook a big batch and keep leftovers for lunch',
  'Frozen veg and tins are cheap and keep well',
  ],
  searchLabel: 'Search student recipes...',
  emptyLabel: 'No student recipes found',
  userMatch: (r) => r.category === 'student' || (r.tags || []).some((t) => String(t).toLowerCase() === 'student'),
  chips: [
  { label: 'All', test: () => true },
  { label: 'Vegetarian', test: (r) => (r.tags || []).some((t) => /vegetarian|vegan/i.test(String(t))) },
  { label: 'With meat', test: (r) => !(r.tags || []).some((t) => /vegetarian|vegan/i.test(String(t))) },
  ],
};

const StudentRecipes = () => <CategoryPage config={config} />;

export default StudentRecipes;
