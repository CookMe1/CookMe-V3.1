import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import NewRecipesPopup from './components/NewRecipesPopup';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { Toaster } from './components/ui/sonner';
import Navigation from './components/Navigation';
import BottomNavigation from './components/BottomNavigation';
// eslint-disable-next-line no-unused-vars
import Auth0Bridge from './components/Auth0Bridge';
// eslint-disable-next-line no-unused-vars
import AdBanner from './components/AdBanner';
import ProtectedRoute from './components/ProtectedRoute';
import LanguagePicker from './components/LanguagePicker';
import DietaryDefaultsPrompt from './components/DietaryDefaultsPrompt';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
const ShareHandler = React.lazy(() => import('./pages/ShareHandler'));
const Dashboard = React.lazy(() => import('./pages/Dashboard'));
const Recipes = React.lazy(() => import('./pages/Recipes'));
const RecipeDetail = React.lazy(() => import('./pages/RecipeDetail'));
const AddRecipe = React.lazy(() => import('./pages/AddRecipe'));
const EditRecipe = React.lazy(() => import('./pages/EditRecipe'));
const Terms = React.lazy(() => import('./pages/Legal').then(m => ({ default: m.Terms })));
const Privacy = React.lazy(() => import('./pages/Legal').then(m => ({ default: m.Privacy })));
const Admin = React.lazy(() => import('./pages/Admin'));
const MealPlanner = React.lazy(() => import('./pages/MealPlanner'));
const ShoppingList = React.lazy(() => import('./pages/ShoppingList'));
const Pantry = React.lazy(() => import('./pages/Pantry'));
const Social = React.lazy(() => import('./pages/Social'));
const Profile = React.lazy(() => import('./pages/Profile'));
const BudgetRecipes = React.lazy(() => import('./pages/BudgetRecipes'));
const StudentRecipes = React.lazy(() => import('./pages/StudentRecipes'));
const AirFryerRecipes = React.lazy(() => import('./pages/AirFryerRecipes'));
const DrinksRecipes = React.lazy(() => import('./pages/DrinksRecipes'));
const SaucesRecipes = React.lazy(() => import('./pages/SaucesRecipes'));
const SnacksRecipes = React.lazy(() => import('./pages/SnacksRecipes'));
const LatestRecipes = React.lazy(() => import('./pages/LatestRecipes'));
const SearchRecipes = React.lazy(() => import('./pages/SearchRecipes'));
const InstapotRecipes = React.lazy(() => import('./pages/InstapotRecipes'));
const QuickRecipes = React.lazy(() => import('./pages/QuickRecipes'));
const Cookbooks = React.lazy(() => import('./pages/Cookbooks'));

// Show language picker on first launch, then dietary defaults prompt if relevant
// eslint-disable-next-line no-unused-vars
const FirstLaunchFlow = () => {
  const { isAuthenticated } = useAuth();
  const { dietaryDefaults } = useLanguage();
  const [step, setStep] = React.useState(null); // null | 'language' | 'dietary'

  React.useEffect(() => {
    if (!isAuthenticated) return;
    const hasLanguage  = !!localStorage.getItem('cookme_language');
    const hasDietary   = !!localStorage.getItem('cookme_dietary_prefs');
    if (!hasLanguage) {
      setStep('language');
    } else if (!hasDietary) {
      const hasSuggestions =
        dietaryDefaults.suggestHalal ||
        dietaryDefaults.suggestVegetarian ||
        dietaryDefaults.suggestKosher;
      if (hasSuggestions) setStep('dietary');
    }
  }, [isAuthenticated, dietaryDefaults]);

  if (step === 'language') {
    return (
      <LanguagePicker
        isModal={true}
        onDismiss={() => {
          const hasDietary = !!localStorage.getItem('cookme_dietary_prefs');
          if (!hasDietary) {
            const hasSuggestions =
              dietaryDefaults.suggestHalal ||
              dietaryDefaults.suggestVegetarian ||
              dietaryDefaults.suggestKosher;
            setStep(hasSuggestions ? 'dietary' : null);
          } else {
            setStep(null);
          }
        }}
      />
    );
  }

  if (step === 'dietary') {
    return <DietaryDefaultsPrompt onDismiss={() => setStep(null)} />;
  }

  return null;
};

function AppRouter() {
  const location = useLocation();

  // Check for auth callback synchronously
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <React.Suspense fallback={<div className="min-h-[60vh] flex items-center justify-center text-zinc-500" data-testid="page-loading">Loading…</div>}>
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/auth/facebook/callback" element={<AuthCallback />} />
      <Route path="/auth/twitter/callback" element={<AuthCallback />} />
      <Route path="/auth/apple/callback" element={<AuthCallback />} />

      {/* Share Handler */}
      <Route path="/share" element={
        <ProtectedRoute>
          <ShareHandler />
        </ProtectedRoute>
      } />

      {/* Protected Routes */}
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Navigation />
          <Dashboard />
        </ProtectedRoute>
      } />

      <Route path="/recipes" element={
        <ProtectedRoute>
          <Navigation />
          <Recipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/recipe/:id" element={
        <ProtectedRoute>
          <Navigation />
          <RecipeDetail />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/recipe/:id/edit" element={
        <ProtectedRoute>
          <Navigation />
          <EditRecipe />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/admin" element={
        <ProtectedRoute>
          <Navigation />
          <Admin />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/add-recipe" element={
        <ProtectedRoute>
          <Navigation />
          <AddRecipe />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/meal-planner" element={
        <ProtectedRoute>
          <Navigation />
          <MealPlanner />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/shopping-list" element={
        <ProtectedRoute>
          <Navigation />
          <ShoppingList />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/pantry" element={
        <ProtectedRoute>
          <Navigation />
          <Pantry />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/social" element={
        <ProtectedRoute>
          <Navigation />
          <Social />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/profile" element={
        <ProtectedRoute>
          <Navigation />
          <Profile />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/profile/:userId" element={
        <ProtectedRoute>
          <Navigation />
          <Profile />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      {/* Category Routes */}
      <Route path="/budget" element={
        <ProtectedRoute>
          <Navigation />
          <BudgetRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/student" element={
        <ProtectedRoute>
          <Navigation />
          <StudentRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/instapot" element={
        <ProtectedRoute>
          <Navigation />
          <InstapotRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/search" element={
        <ProtectedRoute>
          <Navigation />
          <SearchRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/airfryer" element={
        <ProtectedRoute>
          <Navigation />
          <AirFryerRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/drinks" element={
        <ProtectedRoute>
          <Navigation />
          <DrinksRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/sauces" element={
        <ProtectedRoute>
          <Navigation />
          <SaucesRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/snacks" element={
        <ProtectedRoute>
          <Navigation />
          <SnacksRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/latest" element={
        <ProtectedRoute>
          <Navigation />
          <LatestRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/quick" element={
        <ProtectedRoute>
          <Navigation />
          <QuickRecipes />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      <Route path="/cookbooks" element={
        <ProtectedRoute>
          <Navigation />
          <Cookbooks />
          <BottomNavigation />
        </ProtectedRoute>
      } />

      {/* Redirect root to dashboard */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
    </React.Suspense>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Auth0Bridge>
        <LanguageProvider>
          <AppProvider>
            <div className="App min-h-screen bg-[#09090b]">
              <AppRouter />
              <NewRecipesPopup />
              {/* First-launch language/dietary prompt switched off for now: <FirstLaunchFlow /> */}
              <Toaster />
              {/* Ad banner switched off for now: <AdBanner /> */}
            </div>
          </AppProvider>
        </LanguageProvider>
        </Auth0Bridge>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
