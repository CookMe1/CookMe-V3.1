import React, { useState, useRef, useCallback } from 'react';
import { Camera, Link as LinkIcon, Upload, X, Sparkles, Youtube, Share2, Check, Crop, ImageIcon, Package, Loader2, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import ReactCrop from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';
import { validateImageQuality, getRejectMessage, compressImage } from '../utils/imageValidator';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Photo upload flow steps
const PHOTO_STEPS = {
  UPLOAD: 'upload',
  VALIDATING: 'validating',
  CROP: 'crop',
  CONFIRM_IMAGE: 'confirm_image',
  CONFIRM_SAVE: 'confirm_save',
  PROCESSING: 'processing',
  DONE: 'done',
  PANTRY_PROMPT: 'pantry_prompt'
};

const AddRecipe = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('manual');
  const [loading, setLoading] = useState(false);
  const [uploadedImages, setUploadedImages] = useState([]);
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const [showCameraModal, setShowCameraModal] = useState(false);

  // Photo upload flow state
  const [photoStep, setPhotoStep] = useState(PHOTO_STEPS.UPLOAD);
  const [originalImage, setOriginalImage] = useState(null);
  const [croppedImage, setCroppedImage] = useState(null);
  const [crop, setCrop] = useState({ unit: '%', width: 80, height: 80, x: 10, y: 10 });
  const [completedCrop, setCompletedCrop] = useState(null);
  const [parsedRecipe, setParsedRecipe] = useState(null);
  const imgRef = useRef(null);
  
  // Pantry prompt state
  const [detectedIngredients, setDetectedIngredients] = useState([]);
  const [selectedIngredients, setSelectedIngredients] = useState([]);
  const [addingToPantry, setAddingToPantry] = useState(false);

  // Filter options
  const [filterOptions, setFilterOptions] = useState({ categories: [], cuisines: [] });
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedCuisine, setSelectedCuisine] = useState('');

  // Manual recipe form
  const [manualRecipe, setManualRecipe] = useState({
    title: '',
    description: '',
    prepTime: '',
    cookTime: '',
    servings: '4',
    difficulty: 'Easy',
    ingredients: [{ item: '', amount: '' }],
    steps: [''],
    category: '',
    cuisine: ''
  });

  // URL inputs
  const [recipeUrl, setRecipeUrl] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  // Fetch filter options on mount
  React.useEffect(() => {
    fetchFilterOptions();
  }, []);

  const fetchFilterOptions = async () => {
    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/filters/options`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setFilterOptions(data);
      }
    } catch (err) {
      console.error('Failed to fetch filter options:', err);
    }
  };

  // Save recipe to database
  const saveRecipe = async (recipeData) => {
    const token = getToken();
    if (!token) {
      toast.error('Please login to save recipes');
      return null;
    }

    const response = await fetch(`${API_URL}/api/recipes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(recipeData)
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to save recipe');
    }

    return await response.json();
  };

  // Add image to recipe gallery
  const addToGallery = async (recipeId, imageData) => {
    const token = getToken();
    try {
      await fetch(`${API_URL}/api/recipes/${recipeId}/gallery`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ image_data: imageData })
      });
    } catch (err) {
      console.error('Failed to add image to gallery:', err);
    }
  };

  // Generate cropped image from canvas
  const getCroppedImg = useCallback(() => {
    if (!completedCrop || !imgRef.current) return null;

    const canvas = document.createElement('canvas');
    const image = imgRef.current;
    const scaleX = image.naturalWidth / image.width;
    const scaleY = image.naturalHeight / image.height;

    canvas.width = completedCrop.width * scaleX;
    canvas.height = completedCrop.height * scaleY;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(
      image,
      completedCrop.x * scaleX,
      completedCrop.y * scaleY,
      completedCrop.width * scaleX,
      completedCrop.height * scaleY,
      0,
      0,
      canvas.width,
      canvas.height
    );

    return canvas.toDataURL('image/jpeg', 0.9);
  }, [completedCrop]);

  // Handle URL extraction AND auto-save
  const handleExtractFromUrl = async () => {
    if (!recipeUrl) return;
    setLoading(true);

    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/extract`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ recipe_url: recipeUrl })
      });

      if (!response.ok) throw new Error('Failed to extract recipe');

      const data = await response.json();
      
      const savedRecipe = await saveRecipe({
        title: data.title || 'Imported Recipe',
        description: data.description || '',
        prep_time: data.prep_time || '30 min',
        cook_time: data.cook_time || '30 min',
        servings: parseInt(data.servings) || 4,
        difficulty: data.difficulty || 'Medium',
        ingredients: data.ingredients || [],
        steps: data.steps || [],
        image: data.image || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800',
        source_url: recipeUrl,
        tags: data.tags || [],
        category: selectedCategory,
        cuisine: selectedCuisine
      });

      if (savedRecipe) {
        toast.success(`"${data.title}" saved to your recipes!`);
        navigate('/recipes');
      }
    } catch (err) {
      toast.error(err.message || 'Failed to extract recipe. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle YouTube extraction AND auto-save
  const handleExtractFromYoutube = async () => {
    if (!youtubeUrl) return;
    setLoading(true);

    try {
      const token = getToken();
      const response = await fetch(`${API_URL}/api/recipes/extract-youtube`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ youtube_url: youtubeUrl })
      });

      if (!response.ok) throw new Error('Failed to extract recipe from video');

      const data = await response.json();
      
      const savedRecipe = await saveRecipe({
        title: data.title || 'YouTube Recipe',
        description: data.description || '',
        prep_time: data.prep_time || '30 min',
        cook_time: data.cook_time || '30 min',
        servings: parseInt(data.servings) || 4,
        difficulty: data.difficulty || 'Medium',
        ingredients: data.ingredients || [],
        steps: data.steps || [],
        image: data.image || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800',
        source_url: youtubeUrl,
        tags: ['YouTube', ...(data.tags || [])],
        category: selectedCategory,
        cuisine: selectedCuisine
      });

      if (savedRecipe) {
        toast.success(`"${data.title}" saved to your recipes!`);
        navigate('/recipes');
      }
    } catch (err) {
      toast.error(err.message || 'Failed to extract recipe from video.');
    } finally {
      setLoading(false);
    }
  };

  // State for validation error message
  const [validationError, setValidationError] = useState(null);

  // Handle photo upload - Step 1 (with validation)
  const handleImageUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
      const file = files[0];
      const reader = new FileReader();
      reader.onload = async () => {
        const imageData = reader.result;
        setOriginalImage(imageData);
        setPhotoStep(PHOTO_STEPS.VALIDATING);
        setValidationError(null);
        
        try {
          const token = getToken();
          const validation = await validateImageQuality(imageData, token);
          
          if (validation.valid) {
            // Image passes validation - compress and proceed to crop
            const compressed = validation.compressedImage || await compressImage(imageData);
            setOriginalImage(compressed);
            setPhotoStep(PHOTO_STEPS.CROP);
          } else {
            // Image rejected - show error and return to upload
            const message = getRejectMessage(validation.reason);
            setValidationError(message);
            toast.error(message);
            setPhotoStep(PHOTO_STEPS.UPLOAD);
            setOriginalImage(null);
          }
        } catch (error) {
          console.error('Validation error:', error);
          // On error, allow through but still compress
          const compressed = await compressImage(imageData);
          setOriginalImage(compressed);
          setPhotoStep(PHOTO_STEPS.CROP);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  // Confirm crop and proceed - Step 2
  const handleConfirmCrop = () => {
    const cropped = getCroppedImg();
    if (cropped) {
      setCroppedImage(cropped);
      setPhotoStep(PHOTO_STEPS.CONFIRM_IMAGE);
    } else {
      // Use original if no crop
      setCroppedImage(originalImage);
      setPhotoStep(PHOTO_STEPS.CONFIRM_IMAGE);
    }
  };

  // User confirms the image is clear - Step 3
  const handleImageClear = async () => {
    setPhotoStep(PHOTO_STEPS.CONFIRM_SAVE);
  };

  // User wants to re-upload
  const handleRetakePhoto = () => {
    setOriginalImage(null);
    setCroppedImage(null);
    setParsedRecipe(null);
    setPhotoStep(PHOTO_STEPS.UPLOAD);
    setCompletedCrop(null);
    setValidationError(null);
  };

  // User confirms to save recipe - Step 4
  const handleConfirmSave = async () => {
    setPhotoStep(PHOTO_STEPS.PROCESSING);
    setLoading(true);

    try {
      const token = getToken();
      
      // Analyze the photo with AI
      const response = await fetch(`${API_URL}/api/recipes/analyze-photo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ image_data: croppedImage })
      });

      if (!response.ok) throw new Error('Failed to analyze image');

      const data = await response.json();
      
      if (data.type === 'recipe') {
        // Save recipe with the cropped image as the primary image
        const savedRecipe = await saveRecipe({
          title: data.title || 'Photo Recipe',
          description: data.description || 'Recipe extracted from photo',
          prep_time: data.prep_time || '30 min',
          cook_time: data.cook_time || '30 min',
          servings: parseInt(data.servings) || 4,
          difficulty: data.difficulty || 'Medium',
          ingredients: data.ingredients || [],
          steps: data.steps || [],
          image: croppedImage, // Use the cropped image as primary
          tags: ['Photo Import'],
          category: selectedCategory,
          cuisine: selectedCuisine
        });

        if (savedRecipe) {
          // Also add the original image to the gallery
          await addToGallery(savedRecipe.recipe_id, croppedImage);
          
          setParsedRecipe(savedRecipe);
          setPhotoStep(PHOTO_STEPS.DONE);
          toast.success(`Recipe "${data.title}" saved!`);
          
          // Background AI refinement
          refineRecipeInBackground(savedRecipe.recipe_id, data);
        }
      } else {
        // It's ingredients - check if 3 or more
        const ingredients = data.ingredients || [];
        
        if (ingredients.length >= 3) {
          // Show pantry prompt
          setDetectedIngredients(ingredients);
          setSelectedIngredients([...ingredients]);
          setPhotoStep(PHOTO_STEPS.PANTRY_PROMPT);
        } else {
          // Less than 3, just show suggestions
          toast.success('Ingredients detected! Here are recipe suggestions.');
          navigate('/recipes', { 
            state: { 
              suggestions: data.suggestions,
              detectedIngredients: ingredients 
            } 
          });
        }
      }
    } catch (err) {
      toast.error('Failed to analyze photo. Please try again.');
      setPhotoStep(PHOTO_STEPS.CONFIRM_SAVE);
    } finally {
      setLoading(false);
    }
  };

  // Toggle ingredient selection for pantry
  const toggleIngredient = (ingredient) => {
    setSelectedIngredients(prev => 
      prev.includes(ingredient) 
        ? prev.filter(i => i !== ingredient)
        : [...prev, ingredient]
    );
  };

  // Add selected ingredients to pantry
  const handleAddToPantry = async () => {
    if (selectedIngredients.length === 0) {
      toast.error('Please select at least one ingredient');
      return;
    }

    setAddingToPantry(true);
    const token = getToken();

    try {
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
      navigate('/pantry');
    } catch (err) {
      toast.error('Failed to add ingredients to pantry');
    } finally {
      setAddingToPantry(false);
    }
  };

  // Skip pantry and show recipe suggestions
  const handleSkipPantry = () => {
    toast.success('🥗 Showing recipe suggestions...');
    navigate('/recipes', {
      state: {
        suggestions: [],
        detectedIngredients: detectedIngredients
      }
    });
  };

  // Background AI refinement - Step 5
  const refineRecipeInBackground = async (recipeId, initialData) => {
    // This runs in background to improve the recipe with more AI analysis
    try {
      const token = getToken();
      
      // Use AI to enhance the recipe details
      const enhanceResponse = await fetch(`${API_URL}/api/recipes/calculate-nutrition`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ingredients: initialData.ingredients || [],
          servings: initialData.servings || 4
        })
      });

      if (enhanceResponse.ok) {
        // Nutrition calculated in background - recipe will be updated on next view
      }
    } catch (err) {
    }
  };

  // Navigate to recipe after save
  const handleViewRecipe = () => {
    if (parsedRecipe) {
      navigate(`/recipe/${parsedRecipe.recipe_id}`);
    } else {
      navigate('/recipes');
    }
  };

  const addIngredient = () => {
    setManualRecipe({
      ...manualRecipe,
      ingredients: [...manualRecipe.ingredients, { item: '', amount: '' }]
    });
  };

  const addStep = () => {
    setManualRecipe({
      ...manualRecipe,
      steps: [...manualRecipe.steps, '']
    });
  };

  const updateIngredient = (index, field, value) => {
    const newIngredients = [...manualRecipe.ingredients];
    newIngredients[index] = { ...newIngredients[index], [field]: value };
    setManualRecipe({ ...manualRecipe, ingredients: newIngredients });
  };

  const updateStep = (index, value) => {
    const newSteps = [...manualRecipe.steps];
    newSteps[index] = value;
    setManualRecipe({ ...manualRecipe, steps: newSteps });
  };

  const removeIngredient = (index) => {
    if (manualRecipe.ingredients.length > 1) {
      setManualRecipe({
        ...manualRecipe,
        ingredients: manualRecipe.ingredients.filter((_, i) => i !== index)
      });
    }
  };

  const removeStep = (index) => {
    if (manualRecipe.steps.length > 1) {
      setManualRecipe({
        ...manualRecipe,
        steps: manualRecipe.steps.filter((_, i) => i !== index)
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!manualRecipe.title.trim()) {
      toast.error('Please enter a recipe title');
      return;
    }
    
    setLoading(true);

    try {
      const savedRecipe = await saveRecipe({
        title: manualRecipe.title,
        description: manualRecipe.description,
        prep_time: manualRecipe.prepTime || '30 min',
        cook_time: manualRecipe.cookTime || '30 min',
        servings: parseInt(manualRecipe.servings) || 4,
        difficulty: manualRecipe.difficulty,
        ingredients: manualRecipe.ingredients.filter(i => i.item),
        steps: manualRecipe.steps.filter(s => s),
        image: uploadedImages[0] || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800',
        tags: [],
        category: manualRecipe.category,
        cuisine: manualRecipe.cuisine
      });

      if (savedRecipe) {
        toast.success('Recipe saved successfully!');
        navigate('/recipes');
      }
    } catch (err) {
      toast.error(err.message || 'Failed to save recipe.');
    } finally {
      setLoading(false);
    }
  };

  // Handle share intent from other apps
  React.useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const sharedUrl = urlParams.get('url') || urlParams.get('text');
    if (sharedUrl) {
      setRecipeUrl(sharedUrl);
      setActiveTab('url');
    }
  }, []);

  // Render photo upload step content
  const renderPhotoContent = () => {
    switch (photoStep) {
      case PHOTO_STEPS.CROP:
        return (
          <div className="space-y-6">
            <div className="p-4 bg-zinc-800/50 rounded-xl text-center">
              <Crop className="w-8 h-8 text-orange-500 mx-auto mb-2" />
              <h3 className="font-semibold text-zinc-100 mb-1">Crop Your Image</h3>
              <p className="text-zinc-500 text-sm">Drag to select the food portion of your image</p>
            </div>

            <div className="flex justify-center">
              <ReactCrop
                crop={crop}
                onChange={(c) => setCrop(c)}
                onComplete={(c) => setCompletedCrop(c)}
                aspect={1}
                className="max-h-[400px]"
              >
                <img
                  ref={imgRef}
                  src={originalImage}
                  alt="Upload"
                  className="max-h-[400px] rounded-lg"
                />
              </ReactCrop>
            </div>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={handleRetakePhoto}
                className="flex-1 border-zinc-700 text-zinc-300"
              >
                <X className="w-4 h-4 mr-2" />
                Retake
              </Button>
              <Button
                onClick={handleConfirmCrop}
                className="flex-1 bg-orange-600 hover:bg-orange-700"
                data-testid="confirm-crop-btn"
              >
                <Check className="w-4 h-4 mr-2" />
                Confirm Crop
              </Button>
            </div>
          </div>
        );

      case PHOTO_STEPS.CONFIRM_IMAGE:
        return (
          <div className="space-y-6">
            <div className="p-4 bg-zinc-800/50 rounded-xl text-center">
              <ImageIcon className="w-8 h-8 text-orange-500 mx-auto mb-2" />
              <h3 className="font-semibold text-zinc-100 mb-1">Is This Image Clear?</h3>
              <p className="text-zinc-500 text-sm">Make sure the food is clearly visible</p>
            </div>

            <div className="flex justify-center">
              <img
                src={croppedImage}
                alt="Cropped"
                className="max-h-[300px] rounded-lg border-2 border-zinc-700"
              />
            </div>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={handleRetakePhoto}
                className="flex-1 border-zinc-700 text-zinc-300"
              >
                <X className="w-4 h-4 mr-2" />
                Retake Photo
              </Button>
              <Button
                onClick={handleImageClear}
                className="flex-1 bg-orange-600 hover:bg-orange-700"
                data-testid="confirm-clear-btn"
              >
                <Check className="w-4 h-4 mr-2" />
                Yes, It's Clear
              </Button>
            </div>
          </div>
        );

      case PHOTO_STEPS.CONFIRM_SAVE:
        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-br from-orange-600/20 to-rose-600/20 rounded-xl text-center border border-orange-600/30">
              <Sparkles className="w-8 h-8 text-orange-500 mx-auto mb-2" />
              <h3 className="font-semibold text-zinc-100 mb-1">Save This Recipe?</h3>
              <p className="text-zinc-500 text-sm">AI will analyze the image and extract recipe details</p>
            </div>

            <div className="flex justify-center">
              <img
                src={croppedImage}
                alt="Ready to save"
                className="max-h-[250px] rounded-lg border-2 border-orange-600/30"
              />
            </div>

            {/* Category & Cuisine Selection */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">Category</label>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                >
                  <option value="">Select category</option>
                  {filterOptions.categories.map(cat => (
                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">Cuisine</label>
                <select
                  value={selectedCuisine}
                  onChange={(e) => setSelectedCuisine(e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                >
                  <option value="">Select cuisine</option>
                  {filterOptions.cuisines.map(cui => (
                    <option key={cui.value} value={cui.value}>{cui.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={handleRetakePhoto}
                className="flex-1 border-zinc-700 text-zinc-300"
              >
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
              <Button
                onClick={handleConfirmSave}
                className="flex-1 bg-orange-600 hover:bg-orange-700"
                data-testid="confirm-save-photo-btn"
              >
                <Check className="w-4 h-4 mr-2" />
                Save Recipe
              </Button>
            </div>
          </div>
        );

      case PHOTO_STEPS.PROCESSING:
        return (
          <div className="space-y-6 text-center py-12">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 border-4 border-orange-600 border-t-transparent rounded-full animate-spin mb-4" />
              <h3 className="font-semibold text-zinc-100 mb-2">Analyzing Your Photo</h3>
              <p className="text-zinc-500 text-sm">AI is extracting recipe details...</p>
            </div>
            <img
              src={croppedImage}
              alt="Processing"
              className="max-h-[200px] mx-auto rounded-lg opacity-50"
            />
          </div>
        );

      case PHOTO_STEPS.PANTRY_PROMPT:
        return (
          <div className="space-y-6">
            <div className="p-4 bg-gradient-to-br from-green-600/20 to-emerald-600/20 rounded-xl text-center border border-green-600/30">
              <Package className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <h3 className="font-semibold text-zinc-100 text-lg mb-1">Ingredients Detected!</h3>
              <p className="text-zinc-400 text-sm">
                We found {detectedIngredients.length} ingredients in your photo.
              </p>
              <p className="text-zinc-500 text-xs mt-1">
                Would you like to add them to your pantry?
              </p>
            </div>

            {/* Ingredients List */}
            <div className="max-h-[250px] overflow-y-auto space-y-2">
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
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 ${
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
                className="w-full border-zinc-600 hover:bg-zinc-800 text-zinc-300"
                data-testid="skip-pantry-btn"
              >
                Skip & Show Recipe Ideas
              </Button>
              
              <Button 
                onClick={handleRetakePhoto}
                variant="ghost" 
                className="w-full text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50"
              >
                <X className="w-4 h-4 mr-2" />
                Cancel
              </Button>
            </div>
          </div>
        );

      case PHOTO_STEPS.DONE:
        return (
          <div className="space-y-6 text-center py-8">
            <div className="w-20 h-20 bg-green-600/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-10 h-10 text-green-500" />
            </div>
            <h3 className="font-semibold text-zinc-100 text-xl">Recipe Saved!</h3>
            <p className="text-zinc-400">
              {parsedRecipe?.title || 'Your recipe'} has been added to your collection
            </p>

            <div className="flex justify-center">
              <img
                src={croppedImage}
                alt="Saved"
                className="max-h-[200px] rounded-lg border-2 border-green-600/30"
              />
            </div>

            <div className="flex gap-3 justify-center">
              <Button
                variant="outline"
                onClick={handleRetakePhoto}
                className="border-zinc-700 text-zinc-300"
              >
                Add Another
              </Button>
              <Button
                onClick={handleViewRecipe}
                className="bg-orange-600 hover:bg-orange-700"
                data-testid="view-recipe-btn"
              >
                View Recipe
              </Button>
            </div>
          </div>
        );

      default: // UPLOAD or VALIDATING
        return (
          <div className="space-y-6">
            {/* Show validating state */}
            {photoStep === PHOTO_STEPS.VALIDATING ? (
              <div className="p-6 bg-gradient-to-br from-orange-600/20 to-rose-600/20 rounded-xl text-center border border-orange-600/30">
                <Loader2 className="w-16 h-16 text-orange-500 mx-auto mb-4 animate-spin" />
                <h3 className="font-semibold text-zinc-100 text-xl mb-2">Checking Image Quality</h3>
                <p className="text-zinc-400 mb-4">
                  Validating your image for best AI analysis results...
                </p>
              </div>
            ) : (
              <>
                <div className="p-6 bg-gradient-to-br from-orange-600/20 to-rose-600/20 rounded-xl text-center border border-orange-600/30">
                  <Camera className="w-16 h-16 text-orange-500 mx-auto mb-4" />
                  <h3 className="font-semibold text-zinc-100 text-xl mb-2">Smart Photo Import</h3>
                  <p className="text-zinc-400 mb-4">
                    Take a photo of a <strong>recipe</strong> to add it, or photo of <strong>ingredients</strong> to get dish suggestions
                  </p>
                </div>

                {/* Validation error message */}
                {validationError && (
                  <div className="p-4 bg-red-900/30 border border-red-600/50 rounded-xl flex items-center gap-3">
                    <AlertCircle className="w-6 h-6 text-red-400 flex-shrink-0" />
                    <div>
                      <p className="text-red-300 font-medium">Image Rejected</p>
                      <p className="text-red-400/80 text-sm">{validationError}</p>
                    </div>
                  </div>
                )}
              </>
            )}

            <div 
              className={`border-2 border-dashed border-zinc-700 rounded-xl p-8 text-center hover:border-orange-600 transition-colors cursor-pointer ${photoStep === PHOTO_STEPS.VALIDATING ? 'opacity-50 pointer-events-none' : ''}`}
              onClick={() => photoStep !== PHOTO_STEPS.VALIDATING && setShowCameraModal(true)}
            >
              <Camera className="w-12 h-12 text-zinc-500 mx-auto mb-4" />
              <p className="text-zinc-400 mb-4">Tap to take photo or upload image</p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
                data-testid="gallery-input"
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleImageUpload}
                className="hidden"
                data-testid="camera-input"
              />
              <Button 
                type="button" 
                variant="outline" 
                className="border-orange-600 text-orange-500 hover:bg-orange-600/10"
                disabled={photoStep === PHOTO_STEPS.VALIDATING}
              >
                <Camera className="w-5 h-5 mr-2" />
                Choose Photo Source
              </Button>
            </div>

            {/* Camera/Gallery Selection Modal */}
            {showCameraModal && (
              <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[60]" data-testid="camera-modal">
                <div className="w-full max-w-sm bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl p-6">
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
                      onClick={() => {
                        setShowCameraModal(false);
                        cameraInputRef.current?.click();
                      }}
                      className="w-full bg-orange-600 hover:bg-orange-700 h-12"
                      data-testid="camera-capture-btn"
                    >
                      <Camera className="w-5 h-5 mr-2" />
                      Take Photo with Camera
                    </Button>
                    
                    <Button 
                      onClick={() => {
                        setShowCameraModal(false);
                        fileInputRef.current?.click();
                      }}
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
                </div>
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 pb-24 md:pb-0">
      {/* Header */}
      <div className="relative h-[25vh] min-h-[200px]">
        <img
          src="https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1920&h=600&fit=crop"
          alt="Add Recipe"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 gradient-overlay" />

        <div className="absolute bottom-0 left-0 right-0 p-8 md:p-12">
          <div className="max-w-4xl mx-auto">
            <h1 className="font-display text-4xl md:text-5xl font-bold text-zinc-100">
              Add New Recipe
            </h1>
            <p className="text-zinc-400 mt-2">Import from URL, YouTube, photo, or create manually</p>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 md:px-8 py-8">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-4 bg-zinc-800 mb-6">
                <TabsTrigger value="manual" className="data-[state=active]:bg-zinc-700 data-[state=active]:text-orange-500">
                  Manual
                </TabsTrigger>
                <TabsTrigger value="url" className="data-[state=active]:bg-zinc-700 data-[state=active]:text-orange-500">
                  From URL
                </TabsTrigger>
                <TabsTrigger value="youtube" className="data-[state=active]:bg-zinc-700 data-[state=active]:text-orange-500">
                  YouTube
                </TabsTrigger>
                <TabsTrigger value="photo" className="data-[state=active]:bg-zinc-700 data-[state=active]:text-orange-500">
                  Photo
                </TabsTrigger>
              </TabsList>

              {/* Manual Entry */}
              <TabsContent value="manual">
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-2">Title *</label>
                    <Input
                      value={manualRecipe.title}
                      onChange={(e) => setManualRecipe({ ...manualRecipe, title: e.target.value })}
                      placeholder="Recipe name"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      required
                      data-testid="recipe-title-input"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-2">Description</label>
                    <Textarea
                      value={manualRecipe.description}
                      onChange={(e) => setManualRecipe({ ...manualRecipe, description: e.target.value })}
                      placeholder="Brief description of your recipe"
                      className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      rows={3}
                    />
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Prep Time</label>
                      <Input
                        value={manualRecipe.prepTime}
                        onChange={(e) => setManualRecipe({ ...manualRecipe, prepTime: e.target.value })}
                        placeholder="15 min"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Cook Time</label>
                      <Input
                        value={manualRecipe.cookTime}
                        onChange={(e) => setManualRecipe({ ...manualRecipe, cookTime: e.target.value })}
                        placeholder="30 min"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Servings</label>
                      <Input
                        type="number"
                        value={manualRecipe.servings}
                        onChange={(e) => setManualRecipe({ ...manualRecipe, servings: e.target.value })}
                        placeholder="4"
                        className="bg-zinc-950 border-zinc-800 text-zinc-100"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Difficulty</label>
                      <select
                        value={manualRecipe.difficulty}
                        onChange={(e) => setManualRecipe({ ...manualRecipe, difficulty: e.target.value })}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                      >
                        <option>Easy</option>
                        <option>Medium</option>
                        <option>Hard</option>
                      </select>
                    </div>
                  </div>

                  {/* Category & Cuisine */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Category</label>
                      <select
                        value={manualRecipe.category}
                        onChange={(e) => setManualRecipe({ ...manualRecipe, category: e.target.value })}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                      >
                        <option value="">Select category</option>
                        {filterOptions.categories.map(cat => (
                          <option key={cat.value} value={cat.value}>{cat.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Cuisine / Country</label>
                      <select
                        value={manualRecipe.cuisine}
                        onChange={(e) => setManualRecipe({ ...manualRecipe, cuisine: e.target.value })}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                      >
                        <option value="">Select cuisine</option>
                        {filterOptions.cuisines.map(cui => (
                          <option key={cui.value} value={cui.value}>{cui.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-2">Ingredients</label>
                    <div className="space-y-2">
                      {manualRecipe.ingredients.map((ingredient, index) => (
                        <div key={index} className="flex gap-2">
                          <Input
                            value={ingredient.item}
                            onChange={(e) => updateIngredient(index, 'item', e.target.value)}
                            placeholder="Ingredient name"
                            className="flex-1 bg-zinc-950 border-zinc-800 text-zinc-100"
                          />
                          <Input
                            value={ingredient.amount}
                            onChange={(e) => updateIngredient(index, 'amount', e.target.value)}
                            placeholder="Amount"
                            className="w-32 bg-zinc-950 border-zinc-800 text-zinc-100"
                          />
                          <button
                            type="button"
                            onClick={() => removeIngredient(index)}
                            className="p-2 text-zinc-500 hover:text-red-500"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        </div>
                      ))}
                      <Button type="button" variant="outline" onClick={addIngredient} className="border-zinc-700 text-zinc-300">
                        + Add Ingredient
                      </Button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-2">Instructions</label>
                    <div className="space-y-2">
                      {manualRecipe.steps.map((step, index) => (
                        <div key={index} className="flex gap-2 items-start">
                          <span className="w-8 h-8 rounded-full bg-orange-600 flex items-center justify-center text-sm font-bold text-white flex-shrink-0 mt-2">
                            {index + 1}
                          </span>
                          <Textarea
                            value={step}
                            onChange={(e) => updateStep(index, e.target.value)}
                            placeholder={`Step ${index + 1}`}
                            className="flex-1 bg-zinc-950 border-zinc-800 text-zinc-100"
                            rows={2}
                          />
                          <button
                            type="button"
                            onClick={() => removeStep(index)}
                            className="p-2 text-zinc-500 hover:text-red-500 mt-2"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        </div>
                      ))}
                      <Button type="button" variant="outline" onClick={addStep} className="border-zinc-700 text-zinc-300">
                        + Add Step
                      </Button>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-orange-600 hover:bg-orange-700 text-white btn-glow"
                    data-testid="save-recipe-btn"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <span className="animate-spin">⏳</span> Saving...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <Check className="w-5 h-5" /> Save Recipe
                      </span>
                    )}
                  </Button>
                </form>
              </TabsContent>

              {/* From URL */}
              <TabsContent value="url">
                <div className="space-y-6">
                  <div className="p-6 bg-zinc-800/50 rounded-xl text-center">
                    <Share2 className="w-12 h-12 text-orange-500 mx-auto mb-4" />
                    <h3 className="font-semibold text-zinc-100 mb-2">Import from Any Website</h3>
                    <p className="text-zinc-500 text-sm mb-4">
                      Paste a recipe URL and we'll extract all the details automatically
                    </p>
                  </div>

                  {/* Category & Cuisine for URL import */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Category</label>
                      <select
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                      >
                        <option value="">Select category</option>
                        {filterOptions.categories.map(cat => (
                          <option key={cat.value} value={cat.value}>{cat.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Cuisine</label>
                      <select
                        value={selectedCuisine}
                        onChange={(e) => setSelectedCuisine(e.target.value)}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                      >
                        <option value="">Select cuisine</option>
                        {filterOptions.cuisines.map(cui => (
                          <option key={cui.value} value={cui.value}>{cui.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-2">
                      Recipe URL
                    </label>
                    <div className="flex gap-2">
                      <div className="flex-1 relative">
                        <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
                        <Input
                          value={recipeUrl}
                          onChange={(e) => setRecipeUrl(e.target.value)}
                          placeholder="https://example.com/recipe"
                          className="pl-10 bg-zinc-950 border-zinc-800 text-zinc-100"
                          data-testid="url-input"
                        />
                      </div>
                      <Button
                        onClick={handleExtractFromUrl}
                        disabled={loading || !recipeUrl}
                        className="bg-orange-600 hover:bg-orange-700 min-w-[140px]"
                        data-testid="extract-url-btn"
                      >
                        {loading ? (
                          <span className="animate-spin">⏳</span>
                        ) : (
                          <>
                            <Sparkles className="w-5 h-5 mr-2" />
                            Import & Save
                          </>
                        )}
                      </Button>
                    </div>
                    <p className="text-sm text-zinc-600 mt-2">
                      Works with most recipe websites, food blogs, and social media
                    </p>
                  </div>
                </div>
              </TabsContent>

              {/* YouTube */}
              <TabsContent value="youtube">
                <div className="space-y-6">
                  <div className="p-6 bg-zinc-800/50 rounded-xl text-center">
                    <Youtube className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h3 className="font-semibold text-zinc-100 mb-2">Extract from YouTube</h3>
                    <p className="text-zinc-500 text-sm">
                      AI will analyze the cooking video and extract the recipe
                    </p>
                  </div>

                  {/* Category & Cuisine for YouTube import */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Category</label>
                      <select
                        value={selectedCategory}
                        onChange={(e) => setSelectedCategory(e.target.value)}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                      >
                        <option value="">Select category</option>
                        {filterOptions.categories.map(cat => (
                          <option key={cat.value} value={cat.value}>{cat.label}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-zinc-300 mb-2">Cuisine</label>
                      <select
                        value={selectedCuisine}
                        onChange={(e) => setSelectedCuisine(e.target.value)}
                        className="w-full px-3 py-2 bg-zinc-950 border border-zinc-800 rounded-lg text-zinc-100"
                      >
                        <option value="">Select cuisine</option>
                        {filterOptions.cuisines.map(cui => (
                          <option key={cui.value} value={cui.value}>{cui.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-zinc-300 mb-2">
                      YouTube Video URL
                    </label>
                    <div className="flex gap-2">
                      <div className="flex-1 relative">
                        <Youtube className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
                        <Input
                          value={youtubeUrl}
                          onChange={(e) => setYoutubeUrl(e.target.value)}
                          placeholder="https://youtube.com/watch?v=..."
                          className="pl-10 bg-zinc-950 border-zinc-800 text-zinc-100"
                          data-testid="youtube-url-input"
                        />
                      </div>
                      <Button
                        onClick={handleExtractFromYoutube}
                        disabled={loading || !youtubeUrl}
                        className="bg-red-600 hover:bg-red-700 min-w-[140px]"
                        data-testid="extract-youtube-btn"
                      >
                        {loading ? (
                          <span className="animate-spin">⏳</span>
                        ) : (
                          <>
                            <Sparkles className="w-5 h-5 mr-2" />
                            Import & Save
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* From Photo */}
              <TabsContent value="photo">
                {renderPhotoContent()}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AddRecipe;
