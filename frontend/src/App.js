import React from 'react';
import './App.css';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
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
import ShareHandler from './pages/ShareHandler';
import Dashboard from './pages/Dashboard';
import Recipes from './pages/Recipes';
import RecipeDetail from './pages/RecipeDetail';
import AddRecipe from './pages/AddRecipe';
import EditRecipe from './pages/EditRecipe';
import MealPlanner from './pages/MealPlanner';
import ShoppingList from './pages/ShoppingList';
import Pantry from './pages/Pantry';
import Social from './pages/Social';
import Profile from './pages/Profile';
import BudgetRecipes from './pages/BudgetRecipes';
import StudentRecipes from './pages/StudentRecipes';
import AirFryerRecipes from './pages/AirFryerRecipes';
import SearchRecipes from './pages/SearchRecipes';
import InstapotRecipes from './pages/InstapotRecipes';
import QuickRecipes from './pages/QuickRecipes';
import Cookbooks from './pages/Cookbooks';

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
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
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
