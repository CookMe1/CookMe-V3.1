import { DollarSign, GraduationCap, Zap, Clock, Flame } from 'lucide-react';

// Single source of truth: used by the top "Categories" dropdown AND the dashboard "Browse Categories".
export const CATEGORIES = [
  { path: '/student',  label: 'Student',   emoji: '🎓', desc: 'Quick & Easy',          Icon: GraduationCap },
  { path: '/quick',    label: '30 Mins',   emoji: '⚡', desc: 'Fast Cooking',          Icon: Clock },
  { path: '/instapot', label: 'One Pot',   emoji: '🍲', desc: 'Instant Pot & One Pot', Icon: Zap },
  { path: '/budget',   label: 'Budget',    emoji: '💰', desc: 'Cost Effective',        Icon: DollarSign },
  { path: '/airfryer', label: 'Air Fryer', emoji: '🍟', desc: 'Crispy & Healthy',      Icon: Flame },
];
