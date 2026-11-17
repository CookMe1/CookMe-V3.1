import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Trash2, AlertCircle, Package, Sparkles, Search, Minus, Loader2, X, ChevronDown, Globe, Edit3, Check, ChefHat, Clock, Users, Star, ExternalLink, Utensils, ShoppingCart, Mic, MicOff, Camera } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Unit types for different categories
const UNIT_TYPES = {
  weight: ['g', 'kg', 'oz', 'lb'],
  volume: ['ml', 'L', 'cup', 'tbsp', 'tsp', 'fl oz'],
  count: ['piece', 'pieces', 'whole', 'bunch', 'head', 'clove', 'slice', 'can', 'bottle', 'bag', 'box', 'pack'],
  other: ['pinch', 'dash', 'to taste']
};

// Category icons and colors
const CATEGORY_CONFIG = {
  'Produce': { icon: '🥬', color: 'from-green-600/20 to-emerald-600/20', border: 'border-green-600/30' },
  'Dairy': { icon: '🥛', color: 'from-blue-600/20 to-cyan-600/20', border: 'border-blue-600/30' },
  'Meat': { icon: '🥩', color: 'from-red-600/20 to-rose-600/20', border: 'border-red-600/30' },
  'Seafood': { icon: '🐟', color: 'from-cyan-600/20 to-teal-600/20', border: 'border-cyan-600/30' },
  'Grains': { icon: '🌾', color: 'from-amber-600/20 to-yellow-600/20', border: 'border-amber-600/30' },
  'Canned': { icon: '🥫', color: 'from-orange-600/20 to-red-600/20', border: 'border-orange-600/30' },
  'Spices': { icon: '🌶️', color: 'from-red-600/20 to-orange-600/20', border: 'border-red-600/30' },
  'Oils': { icon: '🫒', color: 'from-yellow-600/20 to-lime-600/20', border: 'border-yellow-600/30' },
  'Baking': { icon: '🧁', color: 'from-pink-600/20 to-rose-600/20', border: 'border-pink-600/30' },
  'Frozen': { icon: '❄️', color: 'from-sky-600/20 to-blue-600/20', border: 'border-sky-600/30' },
  'Beverages': { icon: '🧃', color: 'from-purple-600/20 to-violet-600/20', border: 'border-purple-600/30' },
  'Snacks': { icon: '🍿', color: 'from-yellow-600/20 to-orange-600/20', border: 'border-yellow-600/30' },
  'Condiments': { icon: '🧴', color: 'from-amber-600/20 to-orange-600/20', border: 'border-amber-600/30' },
  'Other': { icon: '📦', color: 'from-zinc-600/20 to-slate-600/20', border: 'border-zinc-600/30' }
};

// Common ingredients with enhanced data - COMPREHENSIVE DATABASE
const COMMON_INGREDIENTS = [
  // ===================== PRODUCE - Vegetables =====================
  { name: 'Tomatoes', category: 'Produce', defaultUnit: 'piece', aliases: ['tomato', 'roma tomato', 'cherry tomatoes', 'tomates'] },
  { name: 'Onions', category: 'Produce', defaultUnit: 'piece', aliases: ['onion', 'yellow onion', 'red onion', 'white onion', 'oignon', 'cebolla'] },
  { name: 'Garlic', category: 'Produce', defaultUnit: 'clove', aliases: ['garlic cloves', 'ail', 'ajo', 'knoblauch'] },
  { name: 'Potatoes', category: 'Produce', defaultUnit: 'piece', aliases: ['potato', 'russet potato', 'pomme de terre', 'patata', 'kartoffel'] },
  { name: 'Carrots', category: 'Produce', defaultUnit: 'piece', aliases: ['carrot', 'carotte', 'zanahoria', 'karotte'] },
  { name: 'Celery', category: 'Produce', defaultUnit: 'bunch', aliases: ['celery stalk', 'céleri'] },
  { name: 'Bell Peppers', category: 'Produce', defaultUnit: 'piece', aliases: ['bell pepper', 'capsicum', 'sweet pepper', 'poivron', 'pimiento'] },
  { name: 'Lettuce', category: 'Produce', defaultUnit: 'head', aliases: ['romaine', 'iceberg lettuce', 'laitue', 'lechuga'] },
  { name: 'Spinach', category: 'Produce', defaultUnit: 'bunch', aliases: ['baby spinach', 'épinards', 'espinaca'] },
  { name: 'Broccoli', category: 'Produce', defaultUnit: 'head', aliases: ['broccoli florets', 'brocoli'] },
  { name: 'Mushrooms', category: 'Produce', defaultUnit: 'g', aliases: ['mushroom', 'champignons', 'button mushrooms', 'cremini', 'shiitake', 'portobello'] },
  { name: 'Cucumber', category: 'Produce', defaultUnit: 'piece', aliases: ['cucumbers', 'concombre', 'pepino', 'gurke'] },
  { name: 'Zucchini', category: 'Produce', defaultUnit: 'piece', aliases: ['courgette', 'calabacín'] },
  { name: 'Eggplant', category: 'Produce', defaultUnit: 'piece', aliases: ['aubergine', 'berenjena'] },
  { name: 'Cabbage', category: 'Produce', defaultUnit: 'head', aliases: ['green cabbage', 'red cabbage', 'chou', 'col', 'kohl'] },
  { name: 'Cauliflower', category: 'Produce', defaultUnit: 'head', aliases: ['chou-fleur', 'coliflor'] },
  { name: 'Green Beans', category: 'Produce', defaultUnit: 'g', aliases: ['string beans', 'haricots verts', 'judías verdes'] },
  { name: 'Peas', category: 'Produce', defaultUnit: 'g', aliases: ['green peas', 'petits pois', 'guisantes'] },
  { name: 'Corn', category: 'Produce', defaultUnit: 'piece', aliases: ['sweet corn', 'maïs', 'maíz', 'mais'] },
  { name: 'Asparagus', category: 'Produce', defaultUnit: 'bunch', aliases: ['asperges', 'espárragos', 'spargel'] },
  { name: 'Kale', category: 'Produce', defaultUnit: 'bunch', aliases: ['chou frisé', 'col rizada'] },
  { name: 'Leeks', category: 'Produce', defaultUnit: 'piece', aliases: ['leek', 'poireau', 'puerro'] },
  { name: 'Radishes', category: 'Produce', defaultUnit: 'bunch', aliases: ['radish', 'radis', 'rábano'] },
  { name: 'Beets', category: 'Produce', defaultUnit: 'piece', aliases: ['beetroot', 'betterave', 'remolacha'] },
  { name: 'Sweet Potato', category: 'Produce', defaultUnit: 'piece', aliases: ['yam', 'patate douce', 'batata', 'süßkartoffel'] },
  { name: 'Pumpkin', category: 'Produce', defaultUnit: 'piece', aliases: ['squash', 'citrouille', 'calabaza', 'kürbis'] },
  { name: 'Butternut Squash', category: 'Produce', defaultUnit: 'piece', aliases: ['courge butternut'] },
  // ===================== PRODUCE - Fruits =====================
  { name: 'Lemons', category: 'Produce', defaultUnit: 'piece', aliases: ['lemon', 'citron', 'limón', 'zitrone'] },
  { name: 'Limes', category: 'Produce', defaultUnit: 'piece', aliases: ['lime', 'citron vert', 'lima', 'limette'] },
  { name: 'Oranges', category: 'Produce', defaultUnit: 'piece', aliases: ['orange', 'naranja', 'apfelsine'] },
  { name: 'Apples', category: 'Produce', defaultUnit: 'piece', aliases: ['apple', 'pomme', 'manzana', 'apfel'] },
  { name: 'Bananas', category: 'Produce', defaultUnit: 'piece', aliases: ['banana', 'banane', 'plátano'] },
  { name: 'Avocado', category: 'Produce', defaultUnit: 'piece', aliases: ['avocados', 'avocat', 'aguacate'] },
  { name: 'Berries', category: 'Produce', defaultUnit: 'g', aliases: ['strawberries', 'blueberries', 'raspberries', 'fraises', 'fresas', 'baies'] },
  { name: 'Grapes', category: 'Produce', defaultUnit: 'g', aliases: ['grape', 'raisins', 'uvas', 'trauben'] },
  { name: 'Mango', category: 'Produce', defaultUnit: 'piece', aliases: ['mangoes', 'mangue'] },
  { name: 'Pineapple', category: 'Produce', defaultUnit: 'piece', aliases: ['ananas', 'piña'] },
  { name: 'Peaches', category: 'Produce', defaultUnit: 'piece', aliases: ['peach', 'pêche', 'melocotón', 'pfirsich'] },
  { name: 'Pears', category: 'Produce', defaultUnit: 'piece', aliases: ['pear', 'poire', 'pera', 'birne'] },
  // ===================== PRODUCE - Herbs =====================
  { name: 'Ginger', category: 'Produce', defaultUnit: 'piece', aliases: ['fresh ginger', 'gingembre', 'jengibre', 'ingwer'] },
  { name: 'Fresh Basil', category: 'Produce', defaultUnit: 'bunch', aliases: ['basil', 'basilic', 'albahaca', 'basilikum'] },
  { name: 'Fresh Cilantro', category: 'Produce', defaultUnit: 'bunch', aliases: ['cilantro', 'coriander', 'coriandre', 'cilantro', 'koriander'] },
  { name: 'Fresh Parsley', category: 'Produce', defaultUnit: 'bunch', aliases: ['parsley', 'persil', 'perejil', 'petersilie'] },
  { name: 'Fresh Mint', category: 'Produce', defaultUnit: 'bunch', aliases: ['mint', 'menthe', 'menta', 'minze'] },
  { name: 'Fresh Rosemary', category: 'Produce', defaultUnit: 'bunch', aliases: ['rosemary', 'romarin', 'romero', 'rosmarin'] },
  { name: 'Fresh Thyme', category: 'Produce', defaultUnit: 'bunch', aliases: ['thyme', 'thym', 'tomillo', 'thymian'] },
  { name: 'Green Onions', category: 'Produce', defaultUnit: 'bunch', aliases: ['scallions', 'spring onions', 'oignons verts', 'cebolleta'] },
  { name: 'Shallots', category: 'Produce', defaultUnit: 'piece', aliases: ['shallot', 'échalote', 'chalota'] },
  { name: 'Chives', category: 'Produce', defaultUnit: 'bunch', aliases: ['ciboulette', 'cebollino'] },
  { name: 'Lemongrass', category: 'Produce', defaultUnit: 'piece', aliases: ['citronnelle', 'hierba limón'] },
  // ===================== DAIRY =====================
  { name: 'Milk', category: 'Dairy', defaultUnit: 'L', aliases: ['whole milk', 'skim milk', 'lait', 'leche', 'milch'] },
  { name: 'Butter', category: 'Dairy', defaultUnit: 'g', aliases: ['unsalted butter', 'salted butter', 'beurre', 'mantequilla', 'butter'] },
  { name: 'Eggs', category: 'Dairy', defaultUnit: 'piece', aliases: ['egg', 'oeufs', 'huevos', 'eier'] },
  { name: 'Cheese', category: 'Dairy', defaultUnit: 'g', aliases: ['fromage', 'queso', 'käse'] },
  { name: 'Cheddar Cheese', category: 'Dairy', defaultUnit: 'g', aliases: ['cheddar', 'fromage cheddar'] },
  { name: 'Parmesan', category: 'Dairy', defaultUnit: 'g', aliases: ['parmigiano', 'parmesan cheese', 'parmesano'] },
  { name: 'Mozzarella', category: 'Dairy', defaultUnit: 'g', aliases: ['mozzarella cheese', 'fresh mozzarella'] },
  { name: 'Feta Cheese', category: 'Dairy', defaultUnit: 'g', aliases: ['feta', 'fromage feta'] },
  { name: 'Cream Cheese', category: 'Dairy', defaultUnit: 'g', aliases: ['fromage à la crème', 'queso crema'] },
  { name: 'Cream', category: 'Dairy', defaultUnit: 'ml', aliases: ['heavy cream', 'whipping cream', 'crème', 'nata', 'sahne'] },
  { name: 'Sour Cream', category: 'Dairy', defaultUnit: 'g', aliases: ['crème fraîche', 'crema agria'] },
  { name: 'Greek Yogurt', category: 'Dairy', defaultUnit: 'g', aliases: ['yogurt', 'plain yogurt', 'yaourt', 'yogur'] },
  { name: 'Cottage Cheese', category: 'Dairy', defaultUnit: 'g', aliases: ['fromage cottage', 'requesón'] },
  { name: 'Ricotta', category: 'Dairy', defaultUnit: 'g', aliases: ['ricotta cheese'] },
  // ===================== MEAT =====================
  { name: 'Chicken Breast', category: 'Meat', defaultUnit: 'g', aliases: ['chicken', 'poulet', 'pollo', 'hähnchen', 'blanc de poulet'] },
  { name: 'Chicken Thighs', category: 'Meat', defaultUnit: 'g', aliases: ['chicken thigh', 'cuisses de poulet', 'muslos de pollo'] },
  { name: 'Ground Beef', category: 'Meat', defaultUnit: 'g', aliases: ['minced beef', 'beef mince', 'boeuf haché', 'carne molida', 'hackfleisch'] },
  { name: 'Beef Steak', category: 'Meat', defaultUnit: 'g', aliases: ['steak', 'sirloin', 'ribeye', 'bifteck', 'bistec'] },
  { name: 'Pork Chops', category: 'Meat', defaultUnit: 'g', aliases: ['pork', 'côtelettes de porc', 'chuletas de cerdo'] },
  { name: 'Ground Pork', category: 'Meat', defaultUnit: 'g', aliases: ['minced pork', 'porc haché', 'cerdo molido'] },
  { name: 'Bacon', category: 'Meat', defaultUnit: 'g', aliases: ['lardons', 'tocino', 'speck'] },
  { name: 'Ham', category: 'Meat', defaultUnit: 'g', aliases: ['jambon', 'jamón', 'schinken'] },
  { name: 'Sausage', category: 'Meat', defaultUnit: 'g', aliases: ['sausages', 'saucisse', 'salchicha', 'wurst'] },
  { name: 'Turkey', category: 'Meat', defaultUnit: 'g', aliases: ['turkey breast', 'dinde', 'pavo', 'truthahn'] },
  { name: 'Lamb', category: 'Meat', defaultUnit: 'g', aliases: ['lamb chops', 'agneau', 'cordero', 'lamm'] },
  { name: 'Duck', category: 'Meat', defaultUnit: 'g', aliases: ['duck breast', 'canard', 'pato', 'ente'] },
  { name: 'Prosciutto', category: 'Meat', defaultUnit: 'g', aliases: ['jambon cru', 'jamón serrano'] },
  { name: 'Pancetta', category: 'Meat', defaultUnit: 'g', aliases: ['italian bacon'] },
  // ===================== SEAFOOD =====================
  { name: 'Salmon', category: 'Seafood', defaultUnit: 'g', aliases: ['salmon fillet', 'saumon', 'salmón', 'lachs'] },
  { name: 'Shrimp', category: 'Seafood', defaultUnit: 'g', aliases: ['prawns', 'crevettes', 'camarones', 'garnelen'] },
  { name: 'Tuna', category: 'Seafood', defaultUnit: 'g', aliases: ['tuna steak', 'thon', 'atún'] },
  { name: 'Cod', category: 'Seafood', defaultUnit: 'g', aliases: ['cod fillet', 'cabillaud', 'bacalao', 'kabeljau'] },
  { name: 'Tilapia', category: 'Seafood', defaultUnit: 'g', aliases: ['tilapia fillet'] },
  { name: 'Mussels', category: 'Seafood', defaultUnit: 'g', aliases: ['moules', 'mejillones', 'miesmuscheln'] },
  { name: 'Clams', category: 'Seafood', defaultUnit: 'g', aliases: ['palourdes', 'almejas'] },
  { name: 'Scallops', category: 'Seafood', defaultUnit: 'g', aliases: ['coquilles', 'vieiras'] },
  { name: 'Crab', category: 'Seafood', defaultUnit: 'g', aliases: ['crab meat', 'crabe', 'cangrejo', 'krabbe'] },
  { name: 'Lobster', category: 'Seafood', defaultUnit: 'g', aliases: ['homard', 'langosta', 'hummer'] },
  { name: 'Calamari', category: 'Seafood', defaultUnit: 'g', aliases: ['squid', 'calamar', 'tintenfisch'] },
  { name: 'Anchovies', category: 'Seafood', defaultUnit: 'g', aliases: ['anchois', 'anchoas', 'sardellen'] },
  // ===================== GRAINS & PASTA =====================
  { name: 'Rice', category: 'Grains', defaultUnit: 'g', aliases: ['white rice', 'basmati', 'jasmine rice', 'riz', 'arroz', 'reis'] },
  { name: 'Brown Rice', category: 'Grains', defaultUnit: 'g', aliases: ['riz brun', 'arroz integral'] },
  { name: 'Pasta', category: 'Grains', defaultUnit: 'g', aliases: ['spaghetti', 'penne', 'fettuccine', 'pâtes', 'nudeln'] },
  { name: 'Noodles', category: 'Grains', defaultUnit: 'g', aliases: ['egg noodles', 'rice noodles', 'nouilles', 'fideos'] },
  { name: 'Bread', category: 'Grains', defaultUnit: 'piece', aliases: ['loaf', 'pain', 'pan', 'brot'] },
  { name: 'Breadcrumbs', category: 'Grains', defaultUnit: 'g', aliases: ['panko', 'chapelure', 'pan rallado'] },
  { name: 'Quinoa', category: 'Grains', defaultUnit: 'g', aliases: ['quinua'] },
  { name: 'Couscous', category: 'Grains', defaultUnit: 'g', aliases: ['semoule'] },
  { name: 'Oats', category: 'Grains', defaultUnit: 'g', aliases: ['rolled oats', 'oatmeal', 'flocons d\'avoine', 'avena', 'haferflocken'] },
  { name: 'Barley', category: 'Grains', defaultUnit: 'g', aliases: ['orge', 'cebada', 'gerste'] },
  { name: 'Tortillas', category: 'Grains', defaultUnit: 'piece', aliases: ['flour tortillas', 'corn tortillas'] },
  { name: 'Pita Bread', category: 'Grains', defaultUnit: 'piece', aliases: ['pita', 'pain pita'] },
  // ===================== CANNED GOODS =====================
  { name: 'Tomato Sauce', category: 'Canned', defaultUnit: 'can', aliases: ['tomato puree', 'sauce tomate', 'salsa de tomate'] },
  { name: 'Diced Tomatoes', category: 'Canned', defaultUnit: 'can', aliases: ['canned tomatoes', 'tomates en dés', 'tomates picados'] },
  { name: 'Tomato Paste', category: 'Canned', defaultUnit: 'can', aliases: ['concentré de tomate', 'pasta de tomate'] },
  { name: 'Coconut Milk', category: 'Canned', defaultUnit: 'can', aliases: ['lait de coco', 'leche de coco', 'kokosmilch'] },
  { name: 'Chickpeas', category: 'Canned', defaultUnit: 'can', aliases: ['garbanzo beans', 'pois chiches', 'garbanzos', 'kichererbsen'] },
  { name: 'Black Beans', category: 'Canned', defaultUnit: 'can', aliases: ['haricots noirs', 'frijoles negros', 'schwarze bohnen'] },
  { name: 'Kidney Beans', category: 'Canned', defaultUnit: 'can', aliases: ['haricots rouges', 'frijoles rojos'] },
  { name: 'Cannellini Beans', category: 'Canned', defaultUnit: 'can', aliases: ['white beans', 'haricots blancs'] },
  { name: 'Lentils', category: 'Canned', defaultUnit: 'can', aliases: ['lentilles', 'lentejas', 'linsen'] },
  { name: 'Corn', category: 'Canned', defaultUnit: 'can', aliases: ['canned corn', 'maïs en conserve', 'maíz'] },
  { name: 'Chicken Broth', category: 'Canned', defaultUnit: 'can', aliases: ['chicken stock', 'bouillon de poulet', 'caldo de pollo'] },
  { name: 'Beef Broth', category: 'Canned', defaultUnit: 'can', aliases: ['beef stock', 'bouillon de boeuf', 'caldo de res'] },
  { name: 'Vegetable Broth', category: 'Canned', defaultUnit: 'can', aliases: ['vegetable stock', 'bouillon de légumes', 'caldo de verduras'] },
  { name: 'Canned Tuna', category: 'Canned', defaultUnit: 'can', aliases: ['thon en conserve', 'atún enlatado'] },
  // ===================== SPICES & SEASONINGS =====================
  { name: 'Salt', category: 'Spices', defaultUnit: 'g', aliases: ['sea salt', 'kosher salt', 'sel', 'sal', 'salz'] },
  { name: 'Black Pepper', category: 'Spices', defaultUnit: 'g', aliases: ['pepper', 'ground pepper', 'poivre', 'pimienta', 'pfeffer'] },
  { name: 'Paprika', category: 'Spices', defaultUnit: 'g', aliases: ['smoked paprika', 'pimentón'] },
  { name: 'Cumin', category: 'Spices', defaultUnit: 'g', aliases: ['ground cumin', 'cumin seeds', 'comino', 'kreuzkümmel'] },
  { name: 'Coriander', category: 'Spices', defaultUnit: 'g', aliases: ['ground coriander', 'coriandre moulue', 'cilantro molido'] },
  { name: 'Turmeric', category: 'Spices', defaultUnit: 'g', aliases: ['curcuma', 'cúrcuma', 'kurkuma'] },
  { name: 'Cayenne Pepper', category: 'Spices', defaultUnit: 'g', aliases: ['cayenne', 'piment de cayenne'] },
  { name: 'Chili Powder', category: 'Spices', defaultUnit: 'g', aliases: ['chile powder', 'chile en polvo'] },
  { name: 'Oregano', category: 'Spices', defaultUnit: 'g', aliases: ['dried oregano', 'orégano'] },
  { name: 'Basil', category: 'Spices', defaultUnit: 'g', aliases: ['dried basil', 'basilic séché', 'albahaca seca'] },
  { name: 'Thyme', category: 'Spices', defaultUnit: 'g', aliases: ['dried thyme', 'thym séché', 'tomillo'] },
  { name: 'Rosemary', category: 'Spices', defaultUnit: 'g', aliases: ['dried rosemary', 'romarin séché', 'romero'] },
  { name: 'Cinnamon', category: 'Spices', defaultUnit: 'g', aliases: ['ground cinnamon', 'cannelle', 'canela', 'zimt'] },
  { name: 'Nutmeg', category: 'Spices', defaultUnit: 'g', aliases: ['ground nutmeg', 'muscade', 'nuez moscada', 'muskatnuss'] },
  { name: 'Ginger Powder', category: 'Spices', defaultUnit: 'g', aliases: ['ground ginger', 'gingembre moulu', 'jengibre molido'] },
  { name: 'Garlic Powder', category: 'Spices', defaultUnit: 'g', aliases: ['ail en poudre', 'ajo en polvo', 'knoblauchpulver'] },
  { name: 'Onion Powder', category: 'Spices', defaultUnit: 'g', aliases: ['oignon en poudre', 'cebolla en polvo'] },
  { name: 'Bay Leaves', category: 'Spices', defaultUnit: 'piece', aliases: ['laurel leaves', 'feuilles de laurier', 'hojas de laurel'] },
  { name: 'Italian Seasoning', category: 'Spices', defaultUnit: 'g', aliases: ['herbes de provence'] },
  { name: 'Curry Powder', category: 'Spices', defaultUnit: 'g', aliases: ['curry', 'poudre de curry'] },
  { name: 'Garam Masala', category: 'Spices', defaultUnit: 'g', aliases: ['masala'] },
  { name: 'Chinese Five Spice', category: 'Spices', defaultUnit: 'g', aliases: ['five spice', 'cinq épices'] },
  { name: 'Red Pepper Flakes', category: 'Spices', defaultUnit: 'g', aliases: ['crushed red pepper', 'flocons de piment'] },
  // ===================== OILS =====================
  { name: 'Olive Oil', category: 'Oils', defaultUnit: 'ml', aliases: ['extra virgin olive oil', 'huile d\'olive', 'aceite de oliva', 'olivenöl'] },
  { name: 'Vegetable Oil', category: 'Oils', defaultUnit: 'ml', aliases: ['huile végétale', 'aceite vegetal'] },
  { name: 'Canola Oil', category: 'Oils', defaultUnit: 'ml', aliases: ['huile de canola', 'aceite de canola'] },
  { name: 'Coconut Oil', category: 'Oils', defaultUnit: 'ml', aliases: ['huile de coco', 'aceite de coco', 'kokosöl'] },
  { name: 'Sesame Oil', category: 'Oils', defaultUnit: 'ml', aliases: ['huile de sésame', 'aceite de sésamo'] },
  { name: 'Avocado Oil', category: 'Oils', defaultUnit: 'ml', aliases: ['huile d\'avocat', 'aceite de aguacate'] },
  // ===================== CONDIMENTS =====================
  { name: 'Soy Sauce', category: 'Condiments', defaultUnit: 'ml', aliases: ['sauce soja', 'salsa de soja', 'sojasauce'] },
  { name: 'Fish Sauce', category: 'Condiments', defaultUnit: 'ml', aliases: ['nuoc mam', 'sauce de poisson', 'salsa de pescado'] },
  { name: 'Worcestershire Sauce', category: 'Condiments', defaultUnit: 'ml', aliases: ['sauce worcestershire'] },
  { name: 'Hot Sauce', category: 'Condiments', defaultUnit: 'ml', aliases: ['tabasco', 'sriracha', 'sauce piquante', 'salsa picante'] },
  { name: 'Ketchup', category: 'Condiments', defaultUnit: 'ml', aliases: ['catsup', 'sauce tomate'] },
  { name: 'Mustard', category: 'Condiments', defaultUnit: 'ml', aliases: ['dijon mustard', 'moutarde', 'mostaza', 'senf'] },
  { name: 'Mayonnaise', category: 'Condiments', defaultUnit: 'ml', aliases: ['mayo', 'mayonesa'] },
  { name: 'Vinegar', category: 'Condiments', defaultUnit: 'ml', aliases: ['white vinegar', 'vinaigre', 'vinagre', 'essig'] },
  { name: 'Balsamic Vinegar', category: 'Condiments', defaultUnit: 'ml', aliases: ['vinaigre balsamique', 'vinagre balsámico'] },
  { name: 'Apple Cider Vinegar', category: 'Condiments', defaultUnit: 'ml', aliases: ['vinaigre de cidre', 'vinagre de manzana'] },
  { name: 'Rice Vinegar', category: 'Condiments', defaultUnit: 'ml', aliases: ['rice wine vinegar', 'vinaigre de riz'] },
  { name: 'Honey', category: 'Condiments', defaultUnit: 'g', aliases: ['miel', 'honig'] },
  { name: 'Maple Syrup', category: 'Condiments', defaultUnit: 'ml', aliases: ['sirop d\'érable', 'jarabe de arce', 'ahornsirup'] },
  { name: 'Tahini', category: 'Condiments', defaultUnit: 'g', aliases: ['sesame paste'] },
  { name: 'Peanut Butter', category: 'Condiments', defaultUnit: 'g', aliases: ['beurre de cacahuète', 'mantequilla de maní', 'erdnussbutter'] },
  { name: 'Miso Paste', category: 'Condiments', defaultUnit: 'g', aliases: ['miso', 'pâte de miso'] },
  { name: 'Hoisin Sauce', category: 'Condiments', defaultUnit: 'ml', aliases: ['sauce hoisin'] },
  { name: 'Oyster Sauce', category: 'Condiments', defaultUnit: 'ml', aliases: ['sauce aux huîtres'] },
  // ===================== BAKING =====================
  { name: 'Flour', category: 'Baking', defaultUnit: 'g', aliases: ['all-purpose flour', 'plain flour', 'farine', 'harina', 'mehl'] },
  { name: 'Sugar', category: 'Baking', defaultUnit: 'g', aliases: ['white sugar', 'granulated sugar', 'sucre', 'azúcar', 'zucker'] },
  { name: 'Brown Sugar', category: 'Baking', defaultUnit: 'g', aliases: ['cassonade', 'azúcar moreno', 'brauner zucker'] },
  { name: 'Powdered Sugar', category: 'Baking', defaultUnit: 'g', aliases: ['icing sugar', 'confectioners sugar', 'sucre glace', 'azúcar glas'] },
  { name: 'Baking Powder', category: 'Baking', defaultUnit: 'g', aliases: ['levure chimique', 'polvo de hornear', 'backpulver'] },
  { name: 'Baking Soda', category: 'Baking', defaultUnit: 'g', aliases: ['bicarbonate of soda', 'bicarbonate', 'bicarbonato'] },
  { name: 'Yeast', category: 'Baking', defaultUnit: 'g', aliases: ['active dry yeast', 'instant yeast', 'levure', 'levadura', 'hefe'] },
  { name: 'Vanilla Extract', category: 'Baking', defaultUnit: 'ml', aliases: ['vanilla', 'extrait de vanille', 'extracto de vainilla'] },
  { name: 'Cocoa Powder', category: 'Baking', defaultUnit: 'g', aliases: ['cacao', 'poudre de cacao', 'cacao en polvo', 'kakaopulver'] },
  { name: 'Chocolate Chips', category: 'Baking', defaultUnit: 'g', aliases: ['pépites de chocolat', 'chispas de chocolate'] },
  { name: 'Cornstarch', category: 'Baking', defaultUnit: 'g', aliases: ['corn starch', 'maïzena', 'maicena', 'speisestärke'] },
  { name: 'Almond Flour', category: 'Baking', defaultUnit: 'g', aliases: ['ground almonds', 'farine d\'amande', 'harina de almendra'] },
  // ===================== NUTS & SEEDS =====================
  { name: 'Almonds', category: 'Snacks', defaultUnit: 'g', aliases: ['amandes', 'almendras', 'mandeln'] },
  { name: 'Walnuts', category: 'Snacks', defaultUnit: 'g', aliases: ['noix', 'nueces', 'walnüsse'] },
  { name: 'Cashews', category: 'Snacks', defaultUnit: 'g', aliases: ['noix de cajou', 'anacardos', 'cashewnüsse'] },
  { name: 'Peanuts', category: 'Snacks', defaultUnit: 'g', aliases: ['cacahuètes', 'cacahuetes', 'erdnüsse'] },
  { name: 'Pine Nuts', category: 'Snacks', defaultUnit: 'g', aliases: ['pignons', 'piñones', 'pinienkerne'] },
  { name: 'Sesame Seeds', category: 'Snacks', defaultUnit: 'g', aliases: ['graines de sésame', 'semillas de sésamo'] },
  { name: 'Sunflower Seeds', category: 'Snacks', defaultUnit: 'g', aliases: ['graines de tournesol', 'semillas de girasol'] },
  { name: 'Chia Seeds', category: 'Snacks', defaultUnit: 'g', aliases: ['graines de chia', 'semillas de chía'] },
  { name: 'Flax Seeds', category: 'Snacks', defaultUnit: 'g', aliases: ['linseed', 'graines de lin', 'semillas de lino'] },
  // ===================== TOFU & PLANT PROTEINS =====================
  { name: 'Tofu', category: 'Other', defaultUnit: 'g', aliases: ['firm tofu', 'silken tofu', 'bean curd'] },
  { name: 'Tempeh', category: 'Other', defaultUnit: 'g', aliases: [] },
  { name: 'Seitan', category: 'Other', defaultUnit: 'g', aliases: ['wheat gluten'] },
];

// Build a map of all ingredient names and aliases for fast lookup
const INGREDIENT_MAP = new Map();
COMMON_INGREDIENTS.forEach(ing => {
  const lowerName = ing.name.toLowerCase();
  INGREDIENT_MAP.set(lowerName, ing);
  if (ing.aliases) {
    ing.aliases.forEach(alias => {
      INGREDIENT_MAP.set(alias.toLowerCase(), ing);
    });
  }
});

// Parse amount string into quantity and unit
const parseAmount = (amount) => {
  if (!amount) return { quantity: 1, unit: 'piece' };
  const match = amount.match(/^(\d+\.?\d*)\s*(.*)$/);
  if (match) {
    return { quantity: parseFloat(match[1]) || 1, unit: match[2] || 'piece' };
  }
  return { quantity: parseInt(amount) || 1, unit: 'piece' };
};

// Auto-categorize ingredient - uses comprehensive database with aliases
const categorizeIngredient = (name) => {
  if (!name) return 'Other';
  const lowerName = name.toLowerCase().trim();
  
  // First check exact match in our comprehensive map (includes aliases)
  const found = INGREDIENT_MAP.get(lowerName);
  if (found) return found.category;
  
  // Check if any ingredient name/alias is contained in the input
  for (const [key, ing] of INGREDIENT_MAP) {
    if (lowerName.includes(key) || key.includes(lowerName)) {
      return ing.category;
    }
  }
  
  // Fallback to keyword-based categorization (more comprehensive)
  // Meat
  if (/chicken|beef|pork|lamb|turkey|bacon|sausage|ham|steak|mince|ground|meat|veal|duck|goose|venison|rabbit|prosciutto|pancetta|chorizo|salami|pepperoni|bratwurst|kielbasa/.test(lowerName)) return 'Meat';
  
  // Seafood
  if (/salmon|tuna|shrimp|prawn|fish|crab|lobster|cod|tilapia|halibut|trout|bass|mussels|clams|oysters|scallops|squid|calamari|octopus|anchov|sardine|mackerel|haddock|sole|flounder|snapper/.test(lowerName)) return 'Seafood';
  
  // Dairy
  if (/milk|cheese|yogurt|cream|butter|egg|cheddar|mozzarella|parmesan|feta|ricotta|brie|camembert|gouda|gruyere|cottage|mascarpone|queso|fromage|lait|leche|milch|beurre|mantequilla|oeuf|huevo|ei/.test(lowerName)) return 'Dairy';
  
  // Grains
  if (/rice|pasta|bread|flour|oat|quinoa|noodle|spaghetti|penne|fettuccine|linguine|macaroni|couscous|barley|bulgur|farro|polenta|cornmeal|tortilla|pita|naan|baguette|croissant|bagel|riz|arroz|pan|brot|nudel/.test(lowerName)) return 'Grains';
  
  // Produce - Vegetables
  if (/tomato|onion|garlic|pepper|lettuce|spinach|carrot|potato|broccoli|mushroom|cucumber|celery|zucchini|eggplant|aubergine|cabbage|cauliflower|asparagus|bean|pea|corn|squash|pumpkin|beet|radish|turnip|parsnip|leek|shallot|kale|chard|arugula|endive|artichoke|okra|tomate|oignon|ail|carotte|pomme de terre|cebolla|zanahoria|patata/.test(lowerName)) return 'Produce';
  
  // Produce - Fruits
  if (/apple|banana|orange|lemon|lime|berry|grape|mango|pineapple|peach|pear|plum|cherry|melon|watermelon|kiwi|papaya|coconut|fig|date|pomegranate|avocado|grapefruit|tangerine|mandarin|clementine|pomme|banane|naranja|limón|fraise|fresa|uva/.test(lowerName)) return 'Produce';
  
  // Produce - Herbs
  if (/basil|cilantro|coriander|parsley|mint|rosemary|thyme|oregano|sage|dill|chive|tarragon|bay leaf|lemongrass|ginger|basilic|persil|menthe|romarin|thym|albahaca|perejil|menta/.test(lowerName)) return 'Produce';
  
  // Spices
  if (/salt|pepper|cumin|paprika|turmeric|cinnamon|nutmeg|cayenne|chili|curry|garam|masala|cardamom|clove|allspice|coriander|fennel|anise|saffron|sumac|za'atar|sel|sal|salz|poivre|pimienta|pfeffer|épice|especia|gewürz/.test(lowerName)) return 'Spices';
  
  // Oils
  if (/oil|huile|aceite|öl|olive|vegetable|canola|sunflower|sesame|coconut oil|avocado oil|peanut oil|corn oil|grapeseed/.test(lowerName)) return 'Oils';
  
  // Condiments
  if (/sauce|vinegar|ketchup|mustard|mayo|soy|fish sauce|worcestershire|hot sauce|sriracha|tabasco|salsa|relish|chutney|pesto|hummus|tahini|miso|hoisin|teriyaki|barbecue|vinaigre|vinagre|moutarde|mostaza/.test(lowerName)) return 'Condiments';
  
  // Baking
  if (/sugar|flour|baking|vanilla|cocoa|chocolate|yeast|extract|syrup|molasses|honey|sucre|azúcar|zucker|farine|harina|mehl|levure|levadura|hefe/.test(lowerName)) return 'Baking';
  
  // Canned
  if (/can|canned|broth|stock|bean|chickpea|lentil|conserve|enlatado|konserve|bouillon|caldo/.test(lowerName)) return 'Canned';
  
  // Frozen
  if (/frozen|ice|glace|helado|eis|congelado|surgelé/.test(lowerName)) return 'Frozen';
  
  // Nuts & Seeds (categorized as Snacks)
  if (/nut|seed|almond|walnut|cashew|peanut|pistachio|pecan|hazelnut|macadamia|pine nut|sesame|sunflower|pumpkin seed|chia|flax|noix|nuez|nuss|graine|semilla/.test(lowerName)) return 'Snacks';
  
  // Beverages
  if (/juice|coffee|tea|water|soda|wine|beer|milk|smoothie|jus|café|thé|agua|wasser/.test(lowerName)) return 'Beverages';
  
  return 'Other';
};

const Pantry = () => {
  const navigate = useNavigate();
  const [pantry, setPantry] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [editQuantity, setEditQuantity] = useState(1);
  const [editUnit, setEditUnit] = useState('piece');
  const [editName, setEditName] = useState('');
  const [showUnitDropdown, setShowUnitDropdown] = useState(false);
  const [saving, setSaving] = useState(false);
  const [voiceListening, setVoiceListening] = useState(false);
  const voiceRecogRef = useRef(null);
  
  // Translation state
  const [translating, setTranslating] = useState(false);
  const [translationResult, setTranslationResult] = useState(null);
  const [showTranslationDropdown, setShowTranslationDropdown] = useState(false);
  const [addTranslating, setAddTranslating] = useState(false);
  const [addTranslationResult, setAddTranslationResult] = useState(null);
  
  // Meal suggestion state
  const [showMealSuggestions, setShowMealSuggestions] = useState(false);
  const [loadingMealSuggestions, setLoadingMealSuggestions] = useState(false);
  const [mealSuggestions, setMealSuggestions] = useState(null);
  const [matchType, setMatchType] = useState('most'); // 'all', 'most', 'some'
  const [extraIngredients, setExtraIngredients] = useState(2);
  
  // Pending deletions for undo
  const [pendingDeletions, setPendingDeletions] = useState({});
  const deleteTimeoutsRef = useRef({});

  const inputRef = useRef(null);
  const dropdownRef = useRef(null);
  const unitDropdownRef = useRef(null);
  const translationDropdownRef = useRef(null);

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      Object.values(deleteTimeoutsRef.current).forEach(timeout => clearTimeout(timeout));
    };
  }, []);

  // Fetch pantry items from backend
  const fetchPantry = useCallback(async () => {
    const token = getToken();
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/pantry`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        const categorizedData = data.map(item => ({
          ...item,
          category: item.category && item.category !== 'Other' ? item.category : categorizeIngredient(item.name)
        }));
        setPantry(categorizedData);
      }
    } catch (err) {
      console.error('Failed to fetch pantry:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPantry();
  }, [fetchPantry]);

  // Translate ingredient via API
  const translateIngredient = async (name) => {
    const token = getToken();
    if (!token) return null;

    try {
      const response = await fetch(`${API_URL}/api/recipes/translate-ingredient`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name })
      });

      if (response.ok) {
        return await response.json();
      }
    } catch (err) {
      console.error('Translation failed:', err);
    }
    return null;
  };

  // Handle translation for new ingredient being added
  const handleTranslateForAdd = async () => {
    if (!searchQuery.trim() || searchQuery.length < 2) return;
    
    setAddTranslating(true);
    const result = await translateIngredient(searchQuery.trim());
    setAddTranslationResult(result);
    setAddTranslating(false);
  };

  // Handle translation in item detail modal
  const handleTranslateInModal = async () => {
    if (!editName.trim()) return;
    
    setTranslating(true);
    const result = await translateIngredient(editName.trim());
    setTranslationResult(result);
    setShowTranslationDropdown(true);
    setTranslating(false);
  };

  // Filter suggestions based on search query - includes alias search
  useEffect(() => {
    if (searchQuery.length >= 1) {
      const query = searchQuery.toLowerCase();
      
      // Search through ingredients including aliases
      const filtered = COMMON_INGREDIENTS.filter(item => {
        // Skip if already in pantry
        if (pantry.some(p => p.name.toLowerCase() === item.name.toLowerCase())) {
          return false;
        }
        
        // Check main name
        if (item.name.toLowerCase().includes(query)) {
          return true;
        }
        
        // Check aliases
        if (item.aliases && item.aliases.some(alias => alias.toLowerCase().includes(query))) {
          return true;
        }
        
        return false;
      }).slice(0, 8);  // Show up to 8 suggestions
      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0 || searchQuery.length >= 2);
      
      // Auto-translate if query looks non-English (contains non-ASCII or doesn't match any suggestions)
      const hasNonAscii = /[^\x00-\x7F]/.test(searchQuery);
      const noExactMatch = !INGREDIENT_MAP.has(query);
      if ((hasNonAscii || (noExactMatch && filtered.length === 0)) && searchQuery.length >= 2) {
        handleTranslateForAdd();
      } else {
        setAddTranslationResult(null);
      }
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
      setAddTranslationResult(null);
    }
  }, [searchQuery, pantry]);

  // Click outside handlers
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target) &&
          inputRef.current && !inputRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
      if (unitDropdownRef.current && !unitDropdownRef.current.contains(event.target)) {
        setShowUnitDropdown(false);
      }
      if (translationDropdownRef.current && !translationDropdownRef.current.contains(event.target)) {
        setShowTranslationDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Open item detail modal
  const openItemDetail = (item) => {
    const { quantity, unit } = parseAmount(item.amount);
    setSelectedItem(item);
    setEditQuantity(quantity);
    setEditUnit(unit || 'piece');
    setEditName(item.name);
    setShowUnitDropdown(false);
    setTranslationResult(null);
    setShowTranslationDropdown(false);
  };

  // Close modal
  const closeModal = () => {
    setSelectedItem(null);
    setEditQuantity(1);
    setEditUnit('piece');
    setEditName('');
    setTranslationResult(null);
    setShowTranslationDropdown(false);
  };

  // Save item changes including name
  const saveItemChanges = async () => {
    if (!selectedItem) return;
    
    setSaving(true);
    const token = getToken();
    const newAmount = `${editQuantity} ${editUnit}`;
    const newCategory = categorizeIngredient(editName);
    
    // Optimistic update
    setPantry(prev => prev.map(item => 
      item.item_id === selectedItem.item_id 
        ? { ...item, amount: newAmount, name: editName, category: newCategory } 
        : item
    ));

    try {
      const response = await fetch(`${API_URL}/api/pantry/${selectedItem.item_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ 
          amount: newAmount,
          name: editName,
          category: newCategory
        })
      });

      if (response.ok) {
        toast.success('Item updated');
        closeModal();
      } else {
        fetchPantry();
        toast.error('Failed to update item');
      }
    } catch (err) {
      fetchPantry();
      toast.error('Failed to update item');
    } finally {
      setSaving(false);
    }
  };

  // Add item to pantry via API
  const handleAddItem = async (item) => {
    const token = getToken();
    if (!token) return;

    const category = item.category || categorizeIngredient(item.name);

    try {
      const response = await fetch(`${API_URL}/api/pantry`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          name: item.name,
          category: category,
          amount: `1 ${item.defaultUnit || 'piece'}`,
          in_stock: true
        })
      });

      if (response.ok) {
        const newItem = await response.json();
        newItem.category = category;
        setPantry(prev => [...prev, newItem]);
        toast.success(`${item.name} added to pantry`);
      }
    } catch (err) {
      toast.error('Failed to add item');
    }

    setSearchQuery('');
    setShowSuggestions(false);
    setAddTranslationResult(null);
  };

  const handleAddCustomItem = async () => {
    if (!searchQuery.trim()) return;
    
    await handleAddItem({
      name: searchQuery.trim(),
      category: categorizeIngredient(searchQuery.trim()),
      defaultUnit: 'piece'
    });
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      if (suggestions.length > 0) {
        handleAddItem(suggestions[0]);
      } else {
        handleAddCustomItem();
      }
    }
  };

  // Voice input handler for pantry
  const handleVoiceInput = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { toast.error('Voice not supported in this browser'); return; }
    if (voiceListening) { voiceRecogRef.current?.stop(); return; }
    const rec = new SR();
    rec.lang = 'en-US';
    rec.interimResults = false;
    rec.onstart = () => setVoiceListening(true);
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      setSearchQuery(text);
      setVoiceListening(false);
    };
    rec.onerror = () => setVoiceListening(false);
    rec.onend = () => setVoiceListening(false);
    voiceRecogRef.current = rec;
    rec.start();
  };

  // Delete item with 10-second undo
  const handleDeleteItem = async (itemId, e) => {
    if (e) e.stopPropagation();
    
    const token = getToken();
    if (!token) return;

    // Find the item before removing
    const itemToDelete = pantry.find(item => item.item_id === itemId);
    if (!itemToDelete) return;

    // Hide from UI immediately
    setPantry(prev => prev.filter(item => item.item_id !== itemId));
    setPendingDeletions(prev => ({ ...prev, [itemId]: itemToDelete }));
    
    if (selectedItem?.item_id === itemId) {
      closeModal();
    }

    // Clear any existing timeout for this item
    if (deleteTimeoutsRef.current[itemId]) {
      clearTimeout(deleteTimeoutsRef.current[itemId]);
    }

    // Show toast with undo button
    toast.success(
      <div className="flex items-center justify-between w-full gap-3">
        <span>{itemToDelete.name} removed</span>
        <button
          onClick={() => handleUndoDelete(itemId)}
          className="px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white rounded-md text-sm font-medium transition-colors"
        >
          Undo
        </button>
      </div>,
      {
        duration: 10000,
        id: `delete-${itemId}`,
      }
    );

    // Set timeout to actually delete after 10 seconds
    deleteTimeoutsRef.current[itemId] = setTimeout(async () => {
      try {
        const response = await fetch(`${API_URL}/api/pantry/${itemId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
          // Restore item on error
          handleUndoDelete(itemId);
          toast.error('Failed to remove item');
        }
      } catch (err) {
        handleUndoDelete(itemId);
        toast.error('Failed to remove item');
      } finally {
        // Clean up pending deletion
        setPendingDeletions(prev => {
          const updated = { ...prev };
          delete updated[itemId];
          return updated;
        });
        delete deleteTimeoutsRef.current[itemId];
      }
    }, 10000);
  };

  // Undo delete
  const handleUndoDelete = (itemId) => {
    // Clear the deletion timeout
    if (deleteTimeoutsRef.current[itemId]) {
      clearTimeout(deleteTimeoutsRef.current[itemId]);
      delete deleteTimeoutsRef.current[itemId];
    }

    // Restore the item from pending deletions
    const itemToRestore = pendingDeletions[itemId];
    if (itemToRestore) {
      setPantry(prev => [...prev, itemToRestore]);
      setPendingDeletions(prev => {
        const updated = { ...prev };
        delete updated[itemId];
        return updated;
      });
      toast.dismiss(`delete-${itemId}`);
      toast.success(`${itemToRestore.name} restored`);
    }
  };

  // Quick quantity update
  const quickUpdateQuantity = async (item, delta, e) => {
    if (e) e.stopPropagation();
    
    const token = getToken();
    const { quantity, unit } = parseAmount(item.amount);
    const newQuantity = Math.max(0, quantity + delta);
    
    if (newQuantity === 0) {
      handleDeleteItem(item.item_id);
      return;
    }
    
    const newAmount = `${newQuantity} ${unit}`;
    
    setPantry(prev => prev.map(i => 
      i.item_id === item.item_id ? { ...i, amount: newAmount } : i
    ));

    try {
      await fetch(`${API_URL}/api/pantry/${item.item_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ amount: newAmount })
      });
    } catch (err) {
      fetchPantry();
    }
  };

  // Fetch meal suggestions based on pantry
  const fetchMealSuggestions = async () => {
    const token = getToken();
    if (!token) return;
    
    if (pantry.length === 0) {
      toast.error('Add some ingredients to your pantry first!');
      return;
    }
    
    setLoadingMealSuggestions(true);
    setShowMealSuggestions(true);
    setMealSuggestions(null);
    
    try {
      const response = await fetch(`${API_URL}/api/pantry/suggest-meal`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          match_type: matchType,
          extra_ingredients: extraIngredients
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setMealSuggestions(data);
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to get suggestions');
      }
    } catch (err) {
      console.error('Failed to fetch meal suggestions:', err);
      toast.error('Failed to get meal suggestions');
    } finally {
      setLoadingMealSuggestions(false);
    }
  };

  // Navigate to recipe detail
  const handleViewRecipe = (recipe) => {
    if (recipe.source === 'saved' && recipe.recipe_id) {
      navigate(`/recipe/${recipe.recipe_id}`);
    }
  };

  // Save AI suggestion as a new recipe
  const saveAiSuggestion = async (suggestion) => {
    const token = getToken();
    if (!token) return;
    
    try {
      const response = await fetch(`${API_URL}/api/recipes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          title: suggestion.title,
          description: suggestion.description,
          prep_time: suggestion.prep_time || '15 min',
          cook_time: suggestion.cook_time || '30 min',
          servings: suggestion.servings || 4,
          difficulty: suggestion.difficulty || 'Medium',
          ingredients: suggestion.ingredients || [],
          steps: suggestion.steps || [],
          tags: [...(suggestion.tags || []), 'AI Suggested', 'Pantry Recipe']
        })
      });
      
      if (response.ok) {
        const newRecipe = await response.json();
        toast.success('Recipe saved to your collection!');
        navigate(`/recipe/${newRecipe.recipe_id}`);
      } else {
        toast.error('Failed to save recipe');
      }
    } catch (err) {
      toast.error('Failed to save recipe');
    }
  };

  // Add missing ingredients to shopping list
  const addMissingToShoppingList = async (missingIngredients) => {
    const token = getToken();
    if (!token || !missingIngredients?.length) return;
    
    try {
      const response = await fetch(`${API_URL}/api/shopping-list/add-items`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ items: missingIngredients })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.added_count > 0) {
          toast.success(
            <div className="flex items-center gap-2">
              <ShoppingCart className="w-4 h-4" />
              <span>{data.added_count} items added to shopping list!</span>
            </div>,
            {
              action: {
                label: 'View List',
                onClick: () => navigate('/shopping-list')
              }
            }
          );
        } else {
          toast.info('Items already in shopping list');
        }
      } else {
        toast.error('Failed to add items');
      }
    } catch (err) {
      toast.error('Failed to add to shopping list');
    }
  };

  // Group items by category
  const categoryOrder = ['Produce', 'Dairy', 'Meat', 'Seafood', 'Grains', 'Canned', 'Spices', 'Condiments', 'Oils', 'Baking', 'Frozen', 'Beverages', 'Snacks', 'Other'];
  const categories = [...new Set(pantry.map(item => item.category))].sort((a, b) => {
    const aIndex = categoryOrder.indexOf(a);
    const bIndex = categoryOrder.indexOf(b);
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
  });
  
  const lowStockItems = pantry.filter(item => !item.in_stock);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Hero Header */}
      <div className="relative h-[25vh] min-h-[200px]">
        <img 
          src="https://images.unsplash.com/photo-1490818387583-1baba5e638af?w=1920&h=600&fit=crop"
          alt="Pantry"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-overlay" />
        
        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-6xl mx-auto">
            <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">
              My Pantry
            </h1>
            <p className="text-zinc-400 mt-2">Track ingredients • Supports all languages</p>
            <button
              type="button"
              onClick={() => window.dispatchEvent(new Event('cookme:open-camera'))}
              className="mt-4 inline-flex items-center gap-2 px-4 h-11 rounded-lg bg-orange-600 hover:bg-orange-700 text-white font-medium"
              data-testid="pantry-scan-btn"
            >
              <Camera className="w-4 h-4" /> Scan ingredients
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Low Stock Alert */}
        {lowStockItems.length > 0 && (
          <Card className="mb-6 bg-orange-600/10 border-orange-600/30">
            <CardContent className="pt-6">
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-5 h-5 text-orange-500 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-orange-400 mb-1">Low Stock Items</h3>
                  <p className="text-zinc-400">
                    {lowStockItems.map(item => item.name).join(', ')}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Search & Add with Translation */}
        <Card className="mb-6 bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6">
            <div className="relative">
              <div className="flex items-center gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
                  <Input
                    ref={inputRef}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={handleKeyPress}
                    onFocus={() => searchQuery.length >= 1 && setShowSuggestions(true)}
                    placeholder="Type in any language to add ingredients..."
                    className="pl-10 bg-zinc-950 border-zinc-800 text-zinc-100 placeholder:text-zinc-600 focus:border-orange-600 h-12 text-base"
                    data-testid="pantry-search-input"
                  />
                  
                  {/* Translation indicator */}
                  {addTranslating && (
                    <div className="absolute right-3 top-1/2 -translate-y-1/2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                    </div>
                  )}
                  
                  {/* Suggestions Dropdown with Translation */}
                  {showSuggestions && (suggestions.length > 0 || searchQuery.length >= 2 || addTranslationResult) && (
                    <div 
                      ref={dropdownRef}
                      className="absolute top-full left-0 right-0 mt-2 bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl z-50 max-h-96 overflow-y-auto"
                    >
                      {/* Translation Results */}
                      {addTranslationResult && (
                        <div className="border-b border-zinc-700">
                          <div className="px-4 py-2 bg-blue-600/10 flex items-center gap-2">
                            <Globe className="w-4 h-4 text-blue-400" />
                            <span className="text-xs text-blue-400 font-medium">
                              Detected: {addTranslationResult.detected_language}
                            </span>
                          </div>
                          
                          {/* Best translation */}
                          <button
                            onClick={() => handleAddItem({
                              name: addTranslationResult.english_name,
                              category: addTranslationResult.category,
                              defaultUnit: 'piece'
                            })}
                            className="w-full px-4 py-3 flex items-center justify-between hover:bg-zinc-800 transition-colors text-left bg-blue-600/5"
                          >
                            <div className="flex items-center gap-3">
                              <Check className="w-4 h-4 text-blue-500" />
                              <div>
                                <span className="text-zinc-100 font-medium">{addTranslationResult.english_name}</span>
                                <span className="text-zinc-500 text-xs ml-2">Best translation</span>
                              </div>
                            </div>
                            <span className="text-xs px-2 py-1 bg-blue-600/20 text-blue-400 rounded-full">
                              {addTranslationResult.category}
                            </span>
                          </button>
                          
                          {/* Alternative names */}
                          {addTranslationResult.alternatives?.length > 0 && (
                            <>
                              <div className="px-4 py-1.5 text-xs text-zinc-500 bg-zinc-800/50">
                                Alternative names:
                              </div>
                              {addTranslationResult.alternatives.slice(0, 3).map((alt, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => handleAddItem({
                                    name: alt,
                                    category: addTranslationResult.category,
                                    defaultUnit: 'piece'
                                  })}
                                  className="w-full px-4 py-2 flex items-center gap-3 hover:bg-zinc-800 transition-colors text-left text-zinc-400"
                                >
                                  <Plus className="w-3 h-3 text-zinc-500" />
                                  <span>{alt}</span>
                                </button>
                              ))}
                            </>
                          )}
                        </div>
                      )}
                      
                      {/* Regular suggestions */}
                      {suggestions.map((item, index) => (
                        <button
                          key={index}
                          onClick={() => handleAddItem(item)}
                          className="w-full px-4 py-3 flex items-center justify-between hover:bg-zinc-800 transition-colors text-left border-b border-zinc-800/50 last:border-0"
                        >
                          <div className="flex items-center gap-3">
                            <span className="text-lg">{CATEGORY_CONFIG[item.category]?.icon || '📦'}</span>
                            <span className="text-zinc-100">{item.name}</span>
                          </div>
                          <span className="text-xs px-2 py-1 bg-zinc-800 text-zinc-400 rounded-full">
                            {item.category}
                          </span>
                        </button>
                      ))}
                      
                      {/* Add custom item */}
                      {searchQuery.length >= 2 && !suggestions.some(s => s.name.toLowerCase() === searchQuery.toLowerCase()) && (
                        <button
                          onClick={handleAddCustomItem}
                          className="w-full px-4 py-3 flex items-center gap-3 hover:bg-zinc-800 transition-colors text-left bg-orange-600/10"
                        >
                          <Plus className="w-4 h-4 text-orange-500" />
                          <span className="text-zinc-100">Add "{searchQuery}" as entered</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
                
                <Button 
                  variant="outline" 
                  className="border-orange-600/50 text-orange-400 hover:bg-orange-600/10 h-12 hidden sm:flex"
                  onClick={() => setShowMealSuggestions(true)}
                  data-testid="suggest-meal-btn"
                >
                  <ChefHat className="w-5 h-5 mr-2" />
                  Suggest a Meal
                </Button>
              </div>
              
              <p className="text-zinc-500 text-sm mt-2 flex items-center gap-2">
                <Globe className="w-4 h-4" />
                Type in any language • Auto-translates to English
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Mobile Suggest Meal Button */}
        <div className="sm:hidden mb-6">
          <Button 
            className="w-full bg-orange-600 hover:bg-orange-700 h-12"
            onClick={() => setShowMealSuggestions(true)}
            data-testid="suggest-meal-btn-mobile"
          >
            <ChefHat className="w-5 h-5 mr-2" />
            Suggest a Meal
          </Button>
        </div>

        {/* Meal Suggestions Section */}
        {showMealSuggestions && (
          <Card className="mb-6 bg-zinc-900 border-zinc-800" data-testid="meal-suggestions-section">
            <CardHeader className="pb-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xl text-zinc-100 flex items-center gap-2">
                  <ChefHat className="w-6 h-6 text-orange-500" />
                  Meal Suggestions
                </CardTitle>
                <button 
                  onClick={() => {
                    setShowMealSuggestions(false);
                    setMealSuggestions(null);
                  }}
                  className="text-zinc-500 hover:text-zinc-300 p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </CardHeader>
            <CardContent>
              {/* Filter Options */}
              <div className="mb-6 p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
                <h4 className="text-sm font-medium text-zinc-300 mb-3">Matching Criteria</h4>
                
                {/* Match Type Selection */}
                <div className="mb-4">
                  <label className="text-xs text-zinc-500 mb-2 block">Ingredient Match</label>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { value: 'all', label: 'All ingredients available', desc: 'Only show recipes with all ingredients in pantry' },
                      { value: 'most', label: 'Most ingredients (70%+)', desc: 'Show recipes where most ingredients are available' },
                      { value: 'some', label: 'Any match', desc: 'Show recipes using any pantry items' }
                    ].map(option => (
                      <button
                        key={option.value}
                        onClick={() => setMatchType(option.value)}
                        className={`px-3 py-2 rounded-lg text-sm transition-all ${
                          matchType === option.value
                            ? 'bg-orange-600 text-white'
                            : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                        }`}
                        title={option.desc}
                        data-testid={`match-type-${option.value}`}
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Extra Ingredients Slider */}
                <div className="mb-4">
                  <label className="text-xs text-zinc-500 mb-2 block">
                    Additional ingredients I'm willing to buy: <span className="text-orange-400 font-medium">{extraIngredients}</span>
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="0"
                      max="10"
                      value={extraIngredients}
                      onChange={(e) => setExtraIngredients(parseInt(e.target.value))}
                      className="flex-1 h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer accent-orange-500"
                      data-testid="extra-ingredients-slider"
                    />
                    <span className="text-zinc-400 text-sm w-8 text-center">{extraIngredients}</span>
                  </div>
                </div>
                
                {/* Search Button */}
                <Button 
                  onClick={fetchMealSuggestions}
                  disabled={loadingMealSuggestions || pantry.length === 0}
                  className="w-full bg-orange-600 hover:bg-orange-700"
                  data-testid="find-recipes-btn"
                >
                  {loadingMealSuggestions ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Finding recipes...
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4 mr-2" />
                      Find Recipes
                    </>
                  )}
                </Button>
              </div>
              
              {/* Results */}
              {mealSuggestions && (
                <div className="space-y-6">
                  {/* Saved Recipe Matches */}
                  {mealSuggestions.saved_recipe_matches?.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-zinc-400 mb-3 flex items-center gap-2">
                        <Star className="w-4 h-4 text-yellow-500" />
                        From Your Saved Recipes
                      </h4>
                      <div className="space-y-3">
                        {mealSuggestions.saved_recipe_matches.map((recipe, idx) => (
                          <div 
                            key={recipe.recipe_id || idx}
                            className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700 hover:border-zinc-600 transition-colors cursor-pointer"
                            onClick={() => handleViewRecipe(recipe)}
                            data-testid={`saved-recipe-${idx}`}
                          >
                            <div className="flex gap-4">
                              {recipe.image && (
                                <img 
                                  src={recipe.image} 
                                  alt={recipe.title}
                                  className="w-20 h-20 rounded-lg object-cover flex-shrink-0"
                                />
                              )}
                              <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-2">
                                  <h5 className="font-medium text-zinc-100 truncate">{recipe.title}</h5>
                                  <span className={`text-xs px-2 py-1 rounded-full flex-shrink-0 ${
                                    recipe.match_percentage >= 90 ? 'bg-green-600/20 text-green-400' :
                                    recipe.match_percentage >= 70 ? 'bg-yellow-600/20 text-yellow-400' :
                                    'bg-orange-600/20 text-orange-400'
                                  }`}>
                                    {recipe.match_percentage}% match
                                  </span>
                                </div>
                                <p className="text-sm text-zinc-500 line-clamp-2 mt-1">{recipe.description}</p>
                                <div className="flex items-center gap-4 mt-2 text-xs text-zinc-500">
                                  <span className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {recipe.prep_time} + {recipe.cook_time}
                                  </span>
                                  <span className="flex items-center gap-1">
                                    <Users className="w-3 h-3" />
                                    {recipe.servings} servings
                                  </span>
                                  {recipe.missing_ingredients > 0 && (
                                    <span className="text-orange-400">
                                      +{recipe.missing_ingredients} ingredients needed
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* AI Suggestions */}
                  {mealSuggestions.ai_suggestions?.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-zinc-400 mb-3 flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-purple-400" />
                        AI-Generated Recipe Ideas
                      </h4>
                      <div className="space-y-4">
                        {mealSuggestions.ai_suggestions.map((suggestion, idx) => (
                          <div 
                            key={idx}
                            className="p-4 bg-gradient-to-br from-purple-900/20 to-zinc-800/50 rounded-lg border border-purple-600/30"
                            data-testid={`ai-suggestion-${idx}`}
                          >
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <h5 className="font-medium text-zinc-100">{suggestion.title}</h5>
                              <Button
                                size="sm"
                                variant="outline"
                                className="border-purple-600/50 text-purple-400 hover:bg-purple-600/10 text-xs"
                                onClick={() => saveAiSuggestion(suggestion)}
                                data-testid={`save-ai-suggestion-${idx}`}
                              >
                                <Plus className="w-3 h-3 mr-1" />
                                Save Recipe
                              </Button>
                            </div>
                            <p className="text-sm text-zinc-400 mb-3">{suggestion.description}</p>
                            
                            <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 mb-3">
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {suggestion.prep_time} prep
                              </span>
                              <span className="flex items-center gap-1">
                                <Utensils className="w-3 h-3" />
                                {suggestion.cook_time} cook
                              </span>
                              <span className="flex items-center gap-1">
                                <Users className="w-3 h-3" />
                                {suggestion.servings} servings
                              </span>
                              <span className={`px-2 py-0.5 rounded ${
                                suggestion.difficulty === 'Easy' ? 'bg-green-600/20 text-green-400' :
                                suggestion.difficulty === 'Medium' ? 'bg-yellow-600/20 text-yellow-400' :
                                'bg-red-600/20 text-red-400'
                              }`}>
                                {suggestion.difficulty}
                              </span>
                            </div>
                            
                            {/* Ingredients breakdown */}
                            <div className="grid grid-cols-2 gap-3 text-xs">
                              {suggestion.matched_ingredients?.length > 0 && (
                                <div className="p-2 bg-green-900/20 rounded border border-green-600/20">
                                  <span className="text-green-400 font-medium block mb-1">✓ You have:</span>
                                  <span className="text-zinc-400">{suggestion.matched_ingredients.join(', ')}</span>
                                </div>
                              )}
                              {suggestion.additional_ingredients_needed?.length > 0 && (
                                <div className="p-2 bg-orange-900/20 rounded border border-orange-600/20">
                                  <div className="flex items-start justify-between gap-2 mb-1">
                                    <span className="text-orange-400 font-medium">+ Need to buy:</span>
                                    <button
                                      onClick={() => addMissingToShoppingList(suggestion.additional_ingredients_needed)}
                                      className="flex items-center gap-1 text-orange-400 hover:text-orange-300 transition-colors"
                                      title="Add to shopping list"
                                      data-testid={`add-to-shopping-${idx}`}
                                    >
                                      <ShoppingCart className="w-3 h-3" />
                                      <span>Add all</span>
                                    </button>
                                  </div>
                                  <span className="text-zinc-400">{suggestion.additional_ingredients_needed.join(', ')}</span>
                                </div>
                              )}
                            </div>
                            
                            {/* Preview steps */}
                            {suggestion.steps?.length > 0 && (
                              <details className="mt-3">
                                <summary className="text-xs text-zinc-500 cursor-pointer hover:text-zinc-300">
                                  View recipe steps ({suggestion.steps.length} steps)
                                </summary>
                                <ol className="mt-2 space-y-1 text-xs text-zinc-400 list-decimal list-inside">
                                  {suggestion.steps.slice(0, 5).map((step, stepIdx) => (
                                    <li key={stepIdx} className="line-clamp-1">{step}</li>
                                  ))}
                                  {suggestion.steps.length > 5 && (
                                    <li className="text-zinc-500">...and {suggestion.steps.length - 5} more steps</li>
                                  )}
                                </ol>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* No results */}
                  {(!mealSuggestions.saved_recipe_matches?.length && !mealSuggestions.ai_suggestions?.length) && (
                    <div className="text-center py-8">
                      <Package className="w-12 h-12 mx-auto text-zinc-600 mb-3" />
                      <p className="text-zinc-400">No matching recipes found</p>
                      <p className="text-zinc-600 text-sm mt-1">Try adjusting your matching criteria or adding more ingredients</p>
                    </div>
                  )}
                </div>
              )}
              
              {/* Empty state before search */}
              {!mealSuggestions && !loadingMealSuggestions && (
                <div className="text-center py-6 text-zinc-500">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 text-zinc-600" />
                  <p>Select your preferences and click "Find Recipes" to get personalized meal suggestions</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Pantry Items by Category */}
        {categories.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {categories.map((category) => {
              const items = pantry.filter(item => item.category === category);
              const config = CATEGORY_CONFIG[category] || CATEGORY_CONFIG['Other'];
              
              return (
                <Card key={category} className={`bg-gradient-to-br ${config.color} ${config.border} border`}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg text-zinc-100 flex items-center gap-2">
                      <span className="text-xl">{config.icon}</span>
                      {category} ({items.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-2">
                      {items.map((item) => {
                        const { quantity, unit } = parseAmount(item.amount);
                        return (
                          <div
                            key={item.item_id}
                            onClick={() => openItemDetail(item)}
                            className={`w-full p-3 rounded-lg border transition-all text-left hover:scale-[1.02] cursor-pointer ${
                              item.in_stock 
                                ? 'bg-zinc-900/80 border-zinc-700/50 hover:border-zinc-600' 
                                : 'bg-red-900/30 border-red-600/30 hover:border-red-500/50'
                            }`}
                            data-testid={`pantry-item-${item.item_id}`}
                            role="button"
                            tabIndex={0}
                            onKeyDown={(e) => e.key === 'Enter' && openItemDetail(item)}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1 min-w-0">
                                <h4 className="font-medium text-zinc-100 truncate">{item.name}</h4>
                                <p className="text-xs text-zinc-500 mt-0.5">
                                  {quantity} {unit}
                                  {!item.in_stock && <span className="text-red-400 ml-2">• Low Stock</span>}
                                </p>
                              </div>
                              
                              <div className="flex items-center gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
                                <button
                                  onClick={(e) => quickUpdateQuantity(item, -1, e)}
                                  className="w-7 h-7 flex items-center justify-center rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
                                >
                                  <Minus className="w-3 h-3" />
                                </button>
                                <span className="w-6 text-center text-sm font-medium text-zinc-300">
                                  {quantity}
                                </span>
                                <button
                                  onClick={(e) => quickUpdateQuantity(item, 1, e)}
                                  className="w-7 h-7 flex items-center justify-center rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-colors"
                                >
                                  <Plus className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-zinc-800 flex items-center justify-center">
              <Package className="w-8 h-8 text-zinc-600" />
            </div>
            <p className="text-zinc-400 text-lg">Your pantry is empty</p>
            <p className="text-zinc-600 mt-2">Type in any language to add ingredients</p>
          </div>
        )}
      </div>

      {/* Item Detail Modal with Name Editing & Translation */}
      {selectedItem && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[60]" data-testid="item-detail-modal">
          <Card className="w-full max-w-md bg-zinc-900 border-zinc-700 shadow-2xl max-h-[90vh] overflow-y-auto">
            <CardContent className="pt-6 pb-6">
              {/* Header */}
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">
                    {CATEGORY_CONFIG[selectedItem.category]?.icon || '📦'}
                  </span>
                  <div>
                    <span className="text-xs px-2 py-0.5 bg-zinc-800 text-zinc-400 rounded-full">
                      {categorizeIngredient(editName)}
                    </span>
                  </div>
                </div>
                <button 
                  onClick={closeModal}
                  className="text-zinc-500 hover:text-zinc-300 p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              {/* Editable Name */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Ingredient Name
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Edit3 className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4" />
                    <Input
                      value={editName}
                      onChange={(e) => {
                        setEditName(e.target.value);
                        setTranslationResult(null);
                        setShowTranslationDropdown(false);
                      }}
                      className="pl-10 bg-zinc-800 border-zinc-700 text-zinc-100"
                      placeholder="Enter ingredient name"
                    />
                  </div>
                  <Button
                    onClick={handleTranslateInModal}
                    disabled={translating}
                    variant="outline"
                    className="border-blue-600/50 text-blue-400 hover:bg-blue-600/10"
                    title="Translate & get suggestions"
                  >
                    {translating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Globe className="w-4 h-4" />
                    )}
                  </Button>
                </div>
                
                {/* Translation suggestions dropdown */}
                {showTranslationDropdown && translationResult && (
                  <div 
                    ref={translationDropdownRef}
                    className="mt-2 bg-zinc-800 border border-zinc-700 rounded-lg overflow-hidden"
                  >
                    <div className="px-3 py-2 bg-blue-600/10 flex items-center gap-2 border-b border-zinc-700">
                      <Globe className="w-4 h-4 text-blue-400" />
                      <span className="text-xs text-blue-400">
                        {translationResult.detected_language !== 'English' 
                          ? `Translated from ${translationResult.detected_language}`
                          : 'Spelling suggestions'}
                      </span>
                    </div>
                    
                    {/* Best translation */}
                    <button
                      onClick={() => {
                        setEditName(translationResult.english_name);
                        setShowTranslationDropdown(false);
                      }}
                      className="w-full px-4 py-2 flex items-center gap-3 hover:bg-zinc-700 text-left"
                    >
                      <Check className="w-4 h-4 text-green-500" />
                      <span className="text-zinc-100">{translationResult.english_name}</span>
                      <span className="text-xs text-green-400 ml-auto">Best</span>
                    </button>
                    
                    {/* Alternatives */}
                    {translationResult.alternatives?.map((alt, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setEditName(alt);
                          setShowTranslationDropdown(false);
                        }}
                        className="w-full px-4 py-2 flex items-center gap-3 hover:bg-zinc-700 text-left text-zinc-400 border-t border-zinc-700/50"
                      >
                        <span className="w-4" />
                        <span>{alt}</span>
                      </button>
                    ))}
                    
                    {/* Description */}
                    {translationResult.description && (
                      <div className="px-4 py-2 text-xs text-zinc-500 bg-zinc-900/50 border-t border-zinc-700">
                        {translationResult.description}
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              {/* Quantity & Unit */}
              <div className="mb-6">
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Quantity & Unit
                </label>
                <div className="flex gap-3">
                  <div className="flex items-center bg-zinc-800 rounded-lg border border-zinc-700">
                    <button
                      onClick={() => setEditQuantity(Math.max(0.5, editQuantity - 1))}
                      className="px-3 py-2 text-zinc-400 hover:text-zinc-200 transition-colors"
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <input
                      type="number"
                      value={editQuantity}
                      onChange={(e) => setEditQuantity(parseFloat(e.target.value) || 0)}
                      className="w-16 text-center bg-transparent text-zinc-100 text-lg font-medium focus:outline-none"
                      min="0"
                      step="0.5"
                    />
                    <button
                      onClick={() => setEditQuantity(editQuantity + 1)}
                      className="px-3 py-2 text-zinc-400 hover:text-zinc-200 transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                  
                  {/* Unit Dropdown */}
                  <div className="relative flex-1" ref={unitDropdownRef}>
                    <button
                      onClick={() => setShowUnitDropdown(!showUnitDropdown)}
                      className="w-full px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg flex items-center justify-between text-zinc-100 hover:border-zinc-600 transition-colors"
                    >
                      <span>{editUnit}</span>
                      <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform ${showUnitDropdown ? 'rotate-180' : ''}`} />
                    </button>
                    
                    {showUnitDropdown && (
                      <div className="absolute top-full left-0 right-0 mt-2 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-50 max-h-60 overflow-y-auto">
                        {Object.entries(UNIT_TYPES).map(([group, units]) => (
                          <div key={group}>
                            <div className="px-3 py-1.5 text-xs font-semibold text-zinc-500 uppercase bg-zinc-900/50">
                              {group}
                            </div>
                            {units.map((unit) => (
                              <button
                                key={unit}
                                onClick={() => {
                                  setEditUnit(unit);
                                  setShowUnitDropdown(false);
                                }}
                                className={`w-full px-4 py-2 text-left hover:bg-zinc-700 transition-colors ${
                                  editUnit === unit ? 'text-orange-400 bg-orange-500/10' : 'text-zinc-300'
                                }`}
                              >
                                {unit}
                              </button>
                            ))}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  onClick={() => handleDeleteItem(selectedItem.item_id)}
                  variant="outline"
                  className="flex-1 border-red-600/50 text-red-400 hover:bg-red-600/10"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Delete
                </Button>
                <Button
                  onClick={saveItemChanges}
                  disabled={saving}
                  className="flex-1 bg-orange-600 hover:bg-orange-700"
                >
                  {saving ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : null}
                  Save Changes
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Pantry;
