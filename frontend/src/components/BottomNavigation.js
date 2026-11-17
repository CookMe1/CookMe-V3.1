import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, BookOpen, Package, ShoppingCart, Camera, Upload, X, Check, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { toast } from 'sonner';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { validateImageQuality, getRejectMessage, compressImage } from '../utils/imageValidator';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const BottomNavigation = ({ showNav = true }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { loading, isAuthenticated } = useAuth();
  const { language } = useLanguage();
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const [showCameraModal, setShowCameraModal] = useState(false);
  const [showPantryModal, setShowPantryModal] = useState(false);
  const [detectedIngredients, setDetectedIngredients] = useState([]);
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [addingToPantry, setAddingToPantry] = useState(false);
  
  // Image analysis loading state
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisStatus, setAnalysisStatus] = useState('');
  const [previewImage, setPreviewImage] = useState(null);
  const [validationError, setValidationError] = useState(null);

  // Lets other pages (e.g. Pantry) open the same camera/scan flow
  useEffect(() => {
    const open = () => setShowCameraModal(true);
    window.addEventListener('cookme:open-camera', open);
    return () => window.removeEventListener('cookme:open-camera', open);
  }, []);

  // Don't show during loading or if not authenticated or explicitly hidden
  if (loading || !isAuthenticated || !showNav) return null;

  // Don't show on login page
  if (location.pathname === '/login' || location.pathname === '/') return null;

  const navItems = [
    { path: '/dashboard', label: 'Home', icon: Home },
    { path: '/recipes', label: 'Recipes', icon: BookOpen },
    { path: '/pantry', label: 'Pantry', icon: Package },
    { path: '/shopping-list', label: 'Shopping', icon: ShoppingCart }
  ];

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  const handleCameraClick = () => {
    setShowCameraModal(true);
  };

  const handleCameraCapture = () => {
    setShowCameraModal(false);
    cameraInputRef.current?.click();
  };

  const handleGalleryUpload = () => {
    setShowCameraModal(false);
    fileInputRef.current?.click();
  };

  const toggleIngredient = (ingredient) => {
    setSelectedIngredients(prev => 
      prev.includes(ingredient) 
        ? prev.filter(i => i !== ingredient)
        : [...prev, ingredient]
    );
  };

  const handleAddToPantry = async () => {
    if (selectedIngredients.length === 0) {
      toast.error('Please select at least one ingredient');
      return;
    }

    setAddingToPantry(true);
    const token = getToken();

    try {
      // Add each selected ingredient to pantry
      for (const ingredient of selectedIngredients) {
        await fetch(`${API_URL}/api/pantry`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            name: ingredient,
            quantity: 1,
            unit: 'piece',
            category: 'Other'
          })
        });
      }

      toast.success(`✅ Added ${selectedIngredients.length} ingredients to pantry!`);
      setShowPantryModal(false);
      setDetectedIngredients([]);
      setSelectedIngredients([]);
      navigate('/pantry');
    } catch (err) {
      toast.error('Failed to add ingredients to pantry');
    } finally {
      setAddingToPantry(false);
    }
  };

  const handleSkipPantry = () => {
    setShowPantryModal(false);
    toast.success('🥗 Showing recipe suggestions...');
    navigate('/recipes', {
      state: {
        suggestions: [],
        detectedIngredients: detectedIngredients
      }
    });
    setDetectedIngredients([]);
    setSelectedIngredients([]);
  };

  const handlePhotoCapture = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Show loading popup
    setAnalyzing(true);
    setAnalysisStatus('Checking image quality...');
    setValidationError(null);

    try {
      const token = getToken();
      
      // Convert to base64
      const reader = new FileReader();
      reader.readAsDataURL(file);
      
      reader.onload = async () => {
        const base64Image = reader.result;
        setPreviewImage(base64Image);
        
        try {
          // Step 1: Validate image quality
          setAnalysisStatus('Validating image quality...');
          const validation = await validateImageQuality(base64Image, token);
          
          if (!validation.valid) {
            // Image rejected
            const message = getRejectMessage(validation.reason);
            setValidationError(message);
            setAnalyzing(false);
            setPreviewImage(null);
            toast.error(message);
            e.target.value = '';
            return;
          }
          
          // Use compressed image from validation
          const compressedImage = validation.compressedImage || base64Image;
          setPreviewImage(compressedImage);
          
          // Step 2: Analyze with AI
          setAnalysisStatus('AI is analyzing your photo...');
          const response = await fetch(`${API_URL}/api/recipes/analyze-photo`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ image_data: compressedImage, language: language?.name || 'English' })
          });

          if (!response.ok) throw new Error('Analysis failed');

          const data = await response.json();

          if (data.type === 'recipe') {
            // Determine which image to use for the recipe card
            let recipeImage = null;
            
            // If it's a food photo, use the uploaded image
            if (data.is_food_photo || data.uploaded_image) {
              recipeImage = data.uploaded_image || compressedImage;
            } else {
              // Recipe card/text photo: no AI image (saves credits); the recipe shows the placeholder image
            }
            
            setAnalysisStatus('Saving recipe...');
            
            // Save the recipe
            const saveResponse = await fetch(`${API_URL}/api/recipes`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({
                title: data.title || 'Photo Recipe',
                description: data.description || 'Recipe from photo',
                prep_time: data.prep_time || '30 min',
                cook_time: data.cook_time || '30 min',
                servings: data.servings || 4,
                difficulty: data.difficulty || 'Medium',
                ingredients: data.ingredients || [],
                steps: data.steps || [],
                image: recipeImage || null,
                tags: ['Photo Import']
              })
            });

            if (saveResponse.ok) {
              setAnalyzing(false);
              setPreviewImage(null);
              toast.success(`✅ Recipe "${data.title}" saved!`);
              navigate('/recipes');
            }
          } else {
            // Ingredients detected - check if 3 or more
            const ingredients = data.ingredients || [];
            setAnalyzing(false);
            setPreviewImage(null);
            
            if (ingredients.length >= 3) {
              // Show pantry modal
              setDetectedIngredients(ingredients);
              setSelectedIngredients([...ingredients]); // Select all by default
              setShowPantryModal(true);
            } else {
              // Less than 3 ingredients, just show suggestions
              toast.success('🥗 Ingredients detected! Showing recipe suggestions...');
              navigate('/recipes', {
                state: {
                  suggestions: data.suggestions,
                  detectedIngredients: ingredients
                }
              });
            }
          }
        } catch (innerErr) {
          setAnalyzing(false);
          setPreviewImage(null);
          toast.error('Failed to analyze photo. Please try again.');
        }
      };
    } catch (err) {
      setAnalyzing(false);
      setPreviewImage(null);
      toast.error('Failed to analyze photo. Please try again.');
    }
    
    // Reset input
    e.target.value = '';
  };

  return (
    <>
      <div className="fixed bottom-[68px] left-1/2 -translate-x-1/2 z-50 md:hidden">
        {/* Hidden file inputs */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handlePhotoCapture}
          className="hidden"
          data-testid="gallery-input"
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handlePhotoCapture}
          className="hidden"
          data-testid="camera-input"
        />
        
        <nav
          className="flex items-center gap-1 px-3 py-2 rounded-2xl glass border border-zinc-800/50"
          data-testid="bottom-navigation"
        >
          {/* Left nav items */}
          {navItems.slice(0, 2).map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
                className={`flex flex-col items-center justify-center px-4 py-2 rounded-xl transition-all ${
                  isActive
                    ? 'bg-zinc-800 text-orange-500'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-[10px] font-medium mt-1">{item.label}</span>
              </Link>
            );
          })}

          {/* Center Camera Button - Large and Bold */}
          <button
            onClick={handleCameraClick}
            data-testid="nav-camera"
            className="flex items-center justify-center w-16 h-16 -mt-6 rounded-full bg-gradient-to-br from-orange-500 to-orange-600 text-white shadow-lg shadow-orange-500/40 hover:shadow-orange-500/60 hover:scale-105 transition-all animate-pulse-glow"
          >
            <Camera className="w-8 h-8" strokeWidth={2.5} />
          </button>

          {/* Right nav items */}
          {navItems.slice(2).map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;

            return (
              <Link
                key={item.path}
                to={item.path}
                data-testid={`nav-${item.label.toLowerCase()}`}
                className={`flex flex-col items-center justify-center px-4 py-2 rounded-xl transition-all ${
                  isActive
                    ? 'bg-zinc-800 text-orange-500'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-[10px] font-medium mt-1">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Image Analysis Loading Modal */}
      {analyzing && (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 z-[70]" data-testid="analyzing-modal">
          <Card className="w-full max-w-sm bg-zinc-900 border-zinc-700 shadow-2xl">
            <CardContent className="pt-8 pb-8">
              <div className="text-center">
                {/* Preview Image */}
                {previewImage && (
                  <div className="mb-6 relative">
                    <img 
                      src={previewImage} 
                      alt="Analyzing" 
                      className="w-32 h-32 mx-auto rounded-xl object-cover border-2 border-zinc-700"
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-32 h-32 rounded-xl border-4 border-orange-500/50 border-t-orange-500 animate-spin" style={{ animationDuration: '1.5s' }} />
                    </div>
                  </div>
                )}
                
                {/* Loading Animation */}
                <div className="flex items-center justify-center gap-3 mb-4">
                  <Sparkles className="w-6 h-6 text-orange-500 animate-pulse" />
                  <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                  <Sparkles className="w-6 h-6 text-orange-500 animate-pulse" />
                </div>
                
                {/* Status Text */}
                <h3 className="text-lg font-semibold text-zinc-100 mb-2">Analyzing Photo</h3>
                <p className="text-zinc-400 text-sm animate-pulse">
                  {analysisStatus}
                </p>
                
                {/* Progress dots */}
                <div className="flex justify-center gap-1 mt-4">
                  <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Camera/Gallery Selection Modal */}
      {showCameraModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[60]" data-testid="camera-modal">
          <Card className="w-full max-w-sm bg-zinc-900 border-zinc-700 shadow-2xl">
            <CardContent className="pt-6 pb-6">
              {/* Modal Header */}
              <div className="text-center mb-5">
                <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-orange-500/20 flex items-center justify-center">
                  <Camera className="w-7 h-7 text-orange-400" />
                </div>
                <h3 className="text-lg font-semibold text-zinc-100">Add Photo</h3>
                <p className="text-zinc-400 text-sm mt-1">
                  Do you want to take a photo with the camera?
                </p>
                <p className="text-zinc-500 text-xs mt-1">
                  Press Cancel to upload from gallery instead.
                </p>
              </div>
              
              {/* Action Buttons */}
              <div className="space-y-3">
                <Button 
                  onClick={handleCameraCapture}
                  className="w-full bg-orange-600 hover:bg-orange-700 h-12"
                  data-testid="camera-capture-btn"
                >
                  <Camera className="w-5 h-5 mr-2" />
                  Take Photo with Camera
                </Button>
                
                <Button 
                  onClick={handleGalleryUpload}
                  variant="outline" 
                  className="w-full border-zinc-600 hover:bg-zinc-800 h-12 text-zinc-300"
                  data-testid="gallery-upload-btn"
                >
                  <Upload className="w-5 h-5 mr-2" />
                  Upload from Gallery
                </Button>
                
                <Button 
                  onClick={() => setShowCameraModal(false)}
                  variant="ghost" 
                  className="w-full text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
                  data-testid="camera-modal-cancel"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Add to Pantry Modal */}
      {showPantryModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[60]" data-testid="pantry-modal">
          <Card className="w-full max-w-sm bg-zinc-900 border-zinc-700 shadow-2xl max-h-[80vh] overflow-hidden flex flex-col">
            <CardContent className="pt-6 pb-6 flex flex-col overflow-hidden">
              {/* Modal Header */}
              <div className="text-center mb-4">
                <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-green-500/20 flex items-center justify-center">
                  <Package className="w-7 h-7 text-green-400" />
                </div>
                <h3 className="text-lg font-semibold text-zinc-100">Ingredients Detected!</h3>
                <p className="text-zinc-400 text-sm mt-1">
                  We found {detectedIngredients.length} ingredients in your photo.
                </p>
                <p className="text-zinc-500 text-xs mt-1">
                  Would you like to add them to your pantry?
                </p>
              </div>
              
              {/* Ingredients List */}
              <div className="flex-1 overflow-y-auto mb-4 max-h-[200px]">
                <div className="space-y-2">
                  {detectedIngredients.map((ingredient, index) => (
                    <button
                      key={index}
                      onClick={() => toggleIngredient(ingredient)}
                      className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all ${
                        selectedIngredients.includes(ingredient)
                          ? 'bg-green-500/20 border-green-500/50 text-green-300'
                          : 'bg-zinc-800/50 border-zinc-700 text-zinc-400'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                        selectedIngredients.includes(ingredient)
                          ? 'bg-green-500 border-green-500'
                          : 'border-zinc-600'
                      }`}>
                        {selectedIngredients.includes(ingredient) && (
                          <Check className="w-3 h-3 text-white" />
                        )}
                      </div>
                      <span className="flex-1 text-left capitalize">{ingredient}</span>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="space-y-3">
                <Button 
                  onClick={handleAddToPantry}
                  disabled={addingToPantry || selectedIngredients.length === 0}
                  className="w-full bg-green-600 hover:bg-green-700 h-12 disabled:opacity-50"
                  data-testid="add-to-pantry-btn"
                >
                  {addingToPantry ? (
                    <>
                      <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <Package className="w-5 h-5 mr-2" />
                      Add {selectedIngredients.length} to Pantry
                    </>
                  )}
                </Button>
                
                <Button 
                  onClick={handleSkipPantry}
                  variant="outline" 
                  className="w-full border-zinc-600 hover:bg-zinc-800 h-12 text-zinc-300"
                  data-testid="skip-pantry-btn"
                >
                  Skip & Show Recipe Ideas
                </Button>
                
                <Button 
                  onClick={() => {
                    setShowPantryModal(false);
                    setDetectedIngredients([]);
                    setSelectedIngredients([]);
                  }}
                  variant="ghost" 
                  className="w-full text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
                  data-testid="pantry-modal-cancel"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
};

export default BottomNavigation;
