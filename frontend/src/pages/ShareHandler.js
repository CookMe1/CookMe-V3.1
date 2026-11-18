import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { 
  Share2, Loader2, Check, AlertCircle, Youtube, Globe, Facebook, Instagram,
  Save, ExternalLink, Camera, Upload, ClipboardPaste, X, Link, ChefHat, ImagePlus
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { toast } from 'sonner';
import { validateImageQuality, getRejectMessage, compressImage } from '../utils/imageValidator';
import { useLanguage } from '../context/LanguageContext';
import { saveReturnPath } from '../utils/returnPath';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ============================================================================
// HELPER: Resize image to fit app layout
// ============================================================================
const resizeImageForApp = async (imageUrl, maxWidth = 600, maxHeight = 400) => {
  return new Promise((resolve) => {
    if (!imageUrl) return resolve('');
    if (imageUrl.startsWith('data:')) return resolve(imageUrl);
    
    const img = new Image();
    img.crossOrigin = 'Anonymous';
    
    const timeout = setTimeout(() => resolve(imageUrl), 8000);
    
    img.onload = () => {
      clearTimeout(timeout);
      try {
        const canvas = document.createElement('canvas');
        let { width, height } = img;
        
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width = Math.round(width * ratio);
          height = Math.round(height * ratio);
        }
        
        canvas.width = width;
        canvas.height = height;
        canvas.getContext('2d').drawImage(img, 0, 0, width, height);
        resolve(canvas.toDataURL('image/jpeg', 0.85));
      } catch {
        resolve(imageUrl);
      }
    };
    
    img.onerror = () => {
      clearTimeout(timeout);
      resolve(imageUrl);
    };
    
    img.src = imageUrl;
  });
};

// ============================================================================
// HELPER: Parse text into recipe
// ============================================================================
const parseTextToRecipe = (text) => {
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  if (!lines.length) return null;
  
  const title = lines[0].replace(/^#+\s*/, '').slice(0, 100);
  const ingredients = [];
  const steps = [];
  
  const ingredientPatterns = [/^[-•*]\s+/, /^\d+[\.\)]\s+/, /^[\d½¼¾⅓⅔]+\s+/];
  
  lines.slice(1).forEach(line => {
    const isIngredient = ingredientPatterns.some(p => p.test(line));
    if (isIngredient) {
      const clean = line.replace(/^[-•*]\s+/, '').replace(/^\d+[\.\)]\s+/, '').trim();
      if (clean.length > 2) ingredients.push({ item: clean, amount: '', category: 'Other' });
    } else if (line.length > 15) {
      steps.push(line);
    }
  });
  
  return { title: title || 'Imported Recipe', ingredients, steps, description: steps[0] || '' };
};

// ============================================================================
// PLATFORM CONFIG
// ============================================================================
const PLATFORMS = {
  youtube: {
    match: url => /youtube\.com|youtu\.be/.test(url),
    icon: Youtube, color: 'text-red-500', bg: 'bg-red-500/10', name: 'YouTube',
    endpoint: '/api/recipes/extract-youtube', bodyKey: 'youtube_url'
  },
  facebook: {
    match: url => /facebook\.com|fb\.com|fb\.watch/.test(url),
    icon: Facebook, color: 'text-blue-500', bg: 'bg-blue-500/10', name: 'Facebook',
    endpoint: '/api/import-recipe-workflow', bodyKey: 'url', useWorkflow: true
  },
  instagram: {
    match: url => /instagram\.com|instagr\.am/.test(url),
    icon: Instagram, color: 'text-pink-500', bg: 'bg-pink-500/10', name: 'Instagram',
    endpoint: '/api/instagram/import', bodyKey: 'url', useInstagram: true
  },
  tiktok: {
    match: url => /tiktok\.com|vm\.tiktok\.com/.test(url),
    icon: Globe, color: 'text-cyan-400', bg: 'bg-cyan-400/10', name: 'TikTok',
    endpoint: '/api/recipes/extract-social', bodyKey: 'url', useSocial: true
  },
  pinterest: {
    match: url => /pinterest\.com|pin\.it/.test(url),
    icon: Globe, color: 'text-red-400', bg: 'bg-red-400/10', name: 'Pinterest',
    endpoint: '/api/recipes/extract-social', bodyKey: 'url', useSocial: true
  },
  twitter: {
    match: url => /twitter\.com|x\.com/.test(url),
    icon: Globe, color: 'text-sky-400', bg: 'bg-sky-400/10', name: 'Twitter/X',
    endpoint: '/api/recipes/extract-social', bodyKey: 'url', useSocial: true
  },
  reddit: {
    match: url => /reddit\.com|redd\.it/.test(url),
    icon: Globe, color: 'text-orange-400', bg: 'bg-orange-400/10', name: 'Reddit',
    endpoint: '/api/recipes/extract-social', bodyKey: 'url', useSocial: true
  },
  website: {
    match: () => true,
    icon: Globe, color: 'text-orange-500', bg: 'bg-orange-500/10', name: 'Website',
    endpoint: '/api/recipes/extract', bodyKey: 'recipe_url'
  }
};

const detectPlatform = (url) => {
  if (!url) return PLATFORMS.website;
  for (const [key, cfg] of Object.entries(PLATFORMS)) {
    if (cfg.match(url)) return { ...cfg, key };
  }
  return { ...PLATFORMS.website, key: 'website' };
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================
const ShareHandler = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { translateRecipe, language } = useLanguage();
  
  // State
  const [mode, setMode] = useState('input'); // input, loading, success, error
  const [url, setUrl] = useState('');
  const [platform, setPlatform] = useState(null);
  const [recipe, setRecipe] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [showCamera, setShowCamera] = useState(false);
  const [showPasteBox, setShowPasteBox] = useState(false);
  const [parsingText, setParsingText] = useState(false);
  
  const fileRef = useRef(null);
  const cameraRef = useRef(null);
  
  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  // ============================================================================
  // PARSE PASTED TEXT WITH AI
  // ============================================================================
  const parseFromPastedText = async () => {
    if (!pasteText.trim()) {
      toast.error('Please paste some recipe text first');
      return;
    }
    
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }
    
    setParsingText(true);
    
    try {
      const response = await fetch(`${API_URL}/api/import-recipe-workflow`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ text: pasteText })
      });
      
      const responseClone = response.clone();
      
      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        const text = await responseClone.text();
        console.error('Parse JSON error:', jsonError, 'Response:', text);
        throw new Error('Invalid response from server');
      }
      
      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Failed to parse recipe');
      }
      
      if (data.recipe) {
        const recipeData = data.recipe;
        
        // Parse ingredients for workflow format
        let ingredients = recipeData.ingredients || [];
        if (ingredients.length > 0 && typeof ingredients[0] === 'string') {
          ingredients = ingredients.map(ing => ({ item: ing, amount: '', category: 'Other' }));
        }

        let pastedRecipe = {
          title: recipeData.title || 'Imported Recipe',
          description: recipeData.description || '',
          instructions: recipeData.instructions || '',
          ingredients: ingredients,
          steps: recipeData.steps || [],
          prep_time: recipeData.prep_time || '30 min',
          cook_time: recipeData.cook_time || '30 min',
          servings: recipeData.servings || 4,
          confidence: recipeData.confidence || 'medium',
          confidence_score: recipeData.confidence_score || 0.7,
          needs_user_input: recipeData.confidence_score < 0.5,
          source: 'Pasted Text (AI Parsed)'
        };

        // Auto-translate if user's language is not English
        if (language.code !== 'en') {
          toast.info(`Translating to ${language.name}...`, { duration: 2000 });
          pastedRecipe = await translateRecipe(pastedRecipe);
        }

        setRecipe(prev => ({ ...prev, ...pastedRecipe }));
        setShowPasteBox(false);
        setPasteText('');
        toast.success(`Recipe parsed${language.code !== 'en' ? ` & translated to ${language.name}` : ''}! Found ${ingredients.length} ingredients and ${recipeData.steps?.length || 0} steps`);
      } else {
        throw new Error('No recipe data returned');
      }
      
    } catch (err) {
      console.error('Parse error:', err);
      toast.error(err.message || 'Failed to parse recipe text');
    } finally {
      setParsingText(false);
    }
  };

  // ============================================================================
  // EXTRACT FROM URL
  // ============================================================================
  const extractFromUrl = useCallback(async (inputUrl) => {
    const targetUrl = inputUrl || url;
    if (!targetUrl.trim()) {
      toast.error('Please enter a URL');
      return;
    }
    
    const token = getToken();
    if (!token) {
      saveReturnPath(`/share?url=${encodeURIComponent(targetUrl)}`);
      navigate('/login', { state: { returnTo: `/share?url=${encodeURIComponent(targetUrl)}` } });
      return;
    }
    
    const detected = detectPlatform(targetUrl);
    setPlatform(detected);
    setMode('loading');
    setError('');
    
    try {
      // Build request body based on endpoint type
      let body;
      if (detected.useInstagram) {
        body = { url: targetUrl };
      } else if (detected.useSocial) {
        // TikTok, Pinterest, Twitter/X, Reddit — all use extract-social
        body = { url: targetUrl, platform: detected.key };
      } else if (detected.useWorkflow) {
        body = { url: targetUrl, text: '' };
      } else {
        body = { [detected.bodyKey]: targetUrl };
        if (detected.endpoint.includes('extract-social')) {
          body.platform = detected.key;
        }
      }
      
      const response = await fetch(`${API_URL}${detected.endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });
      
      // Clone response before reading to avoid "body stream already read" error
      const responseClone = response.clone();
      
      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        // If JSON parsing fails, try to get text from clone
        const text = await responseClone.text();
        console.error('JSON parse error:', jsonError, 'Response text:', text);
        throw new Error('Invalid response from server');
      }
      
      if (!response.ok) {
        throw new Error(data.detail || data.error || 'Failed to extract recipe');
      }
      
      // Handle new workflow response format
      let recipeData;
      if (detected.useWorkflow && data.recipe) {
        recipeData = data.recipe;
        
        // Show appropriate toast based on node reached and confidence
        if (recipeData.needs_user_input && recipeData.user_message) {
          toast.info(recipeData.user_message, { duration: 5000 });
        } else if (recipeData.external_url_found) {
          try {
            const domain = new URL(recipeData.external_url_found).hostname.replace('www.', '');
            toast.success(`Found recipe from ${domain}`, { duration: 3000 });
          } catch {
            toast.success('Found external recipe link!', { duration: 3000 });
          }
        } else if (recipeData.is_video) {
          toast.info('Video detected - extracted from captions', { duration: 3000 });
        }
        
        // Show confidence indicator
        if (recipeData.confidence_score !== undefined && recipeData.confidence_score < 0.5) {
          toast.warning('Low confidence extraction - please review carefully', { duration: 4000 });
        }
      } else {
        recipeData = data;
      }
      
      // ── Duplicate recipe detection ─────────────────────────────────────────
      // Backend fingerprints recipes by domain+title — if this URL was already
      // imported by this user, flag it so they can navigate to the existing one
      if (recipeData._duplicate && recipeData._existing_recipe_id) {
        toast.warning(
          <div>
            <p className="font-medium">You already have this recipe</p>
            <a
              href={`/recipe/${recipeData._existing_recipe_id}`}
              className="text-orange-400 underline text-sm"
            >
              View existing recipe →
            </a>
          </div>,
          { duration: 8000 }
        );
      }

      // Resize image
      const imageUrl = recipeData.image_url || recipeData.imageUrl || recipeData.image || '';
      const resizedImage = await resizeImageForApp(imageUrl, 600, 400);
      
      // Parse ingredients for workflow format
      let ingredients = recipeData.ingredients || [];
      if (ingredients.length > 0 && typeof ingredients[0] === 'object' && ingredients[0].item) {
        // Already in correct format
      } else if (ingredients.length > 0 && typeof ingredients[0] === 'string') {
        ingredients = ingredients.map(ing => ({ item: ing, amount: '', category: 'Other' }));
      }
      
      let builtRecipe = {
        title: recipeData.title || 'Imported Recipe',
        description: recipeData.description || '',
        instructions: recipeData.instructions || '',
        ingredients: ingredients,
        steps: recipeData.steps || [],
        image: resizedImage,
        source_url: recipeData.source_url || targetUrl,
        source: recipeData.source_attribution || detected.name,
        prep_time: recipeData.prep_time || '30 min',
        cook_time: recipeData.cook_time || '30 min',
        servings: recipeData.servings || 4,
        difficulty: recipeData.difficulty || 'Medium',
        tags: [...(recipeData.tags || []), 'Imported'],
        confidence: recipeData.confidence || 'high',
        confidence_score: recipeData.confidence_score || 1.0,
        needs_user_input: recipeData.needs_user_input || false,
        is_video: recipeData.is_video || false,
        thumbnail_url: recipeData.thumbnail_url || '',
        external_url_found: recipeData.external_url_found || null
      };

      // Auto-translate if user's language is not English
      if (language.code !== 'en') {
        toast.info(`Translating to ${language.name}...`, { duration: 2000 });
        builtRecipe = await translateRecipe(builtRecipe);
      }

      setRecipe(builtRecipe);
      setMode('success');
      
      // Show appropriate message based on confidence
      if (recipeData.confidence === 'user-assisted') {
        toast.info('Please review and edit the recipe details');
      } else if (recipeData.confidence === 'medium') {
        toast.success('Recipe extracted - please verify the details');
      } else {
        toast.success(language.code !== 'en' ? `Recipe extracted & translated to ${language.name}!` : 'Recipe extracted!');
      }
      
    } catch (err) {
      console.error('Extract error:', err);
      setError(err.message || 'Failed to extract recipe');
      setMode('error');
      toast.error(err.message || 'Extraction failed');
    }
  }, [url, navigate]);

  // ============================================================================
  // HANDLE IMAGE UPLOAD (with validation)
  // ============================================================================
  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }
    
    setMode('loading');
    setShowCamera(false);
    
    try {
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          // Step 1: Validate image quality
          const validation = await validateImageQuality(reader.result, token);
          
          if (!validation.valid) {
            // Image rejected
            const message = getRejectMessage(validation.reason);
            setError(message);
            setMode('error');
            toast.error(message);
            e.target.value = '';
            return;
          }
          
          // Use compressed image from validation
          const compressedImage = validation.compressedImage || reader.result;
          
          // Step 2: Resize for app layout  
          const resized = await resizeImageForApp(compressedImage, 600, 400);
          
          // Step 3: Analyze with AI
          const response = await fetch(`${API_URL}/api/recipes/analyze-photo`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ image_data: resized })
          });
          
          const responseClone = response.clone();
          
          let data;
          try {
            data = await response.json();
          } catch (jsonError) {
            const text = await responseClone.text();
            console.error('Photo analysis JSON error:', jsonError, 'Response:', text);
            throw new Error('Invalid response from server');
          }
          
          if (!response.ok) throw new Error(data.detail || 'Analysis failed');
          
          let photoRecipe = {
            title: data.title || 'Recipe from Photo',
            description: data.description || '',
            ingredients: data.ingredients?.map(i => 
              typeof i === 'string' ? { item: i, amount: '', category: 'Other' } : i
            ) || [],
            steps: data.steps || [],
            image: resized,
            source: 'Photo',
            prep_time: data.prep_time || '30 min',
            cook_time: data.cook_time || '30 min',
            servings: data.servings || 4,
            difficulty: data.difficulty || 'Medium',
            tags: ['Photo Import']
          };

          // Auto-translate if user's language is not English
          if (language.code !== 'en') {
            toast.info(`Translating to ${language.name}...`, { duration: 2000 });
            photoRecipe = await translateRecipe(photoRecipe);
          }

          setRecipe(photoRecipe);
          setMode('success');
          toast.success(language.code !== 'en' ? `Recipe extracted & translated to ${language.name}!` : 'Recipe extracted from photo!');
        } catch (innerErr) {
          setError(innerErr.message);
          setMode('error');
          toast.error(innerErr.message || 'Failed to analyze image');
        }
      };
      reader.readAsDataURL(file);
    } catch (err) {
      setError(err.message);
      setMode('error');
      toast.error('Failed to analyze image');
    }
    
    e.target.value = '';
  };

  // ============================================================================
  // HANDLE PASTE TEXT
  // ============================================================================
  const handlePasteSubmit = async () => {
    if (!pasteText.trim()) {
      toast.error('Please paste recipe text');
      return;
    }
    
    const parsed = parseTextToRecipe(pasteText);
    if (!parsed) {
      toast.error('Could not parse recipe');
      return;
    }

    let pasteRecipe = {
      ...parsed,
      image: '',
      source: 'Pasted',
      prep_time: '30 min',
      cook_time: '30 min',
      servings: 4,
      difficulty: 'Medium',
      tags: ['Pasted Import']
    };

    // Auto-translate if user's language is not English
    if (language.code !== 'en') {
      toast.info(`Translating to ${language.name}...`, { duration: 2000 });
      pasteRecipe = await translateRecipe(pasteRecipe);
    }

    setRecipe(pasteRecipe);
    setMode('success');
    toast.success(language.code !== 'en' ? `Recipe parsed & translated to ${language.name}!` : 'Recipe parsed!');
  };

  // ============================================================================
  // SAVE RECIPE
  // ============================================================================
  const saveRecipe = async () => {
    if (!recipe) return;
    
    const token = getToken();
    if (!token) {
      navigate('/login');
      return;
    }
    
    setSaving(true);
    
    try {
      const response = await fetch(`${API_URL}/api/recipes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(recipe)
      });
      
      const responseClone = response.clone();
      
      let saved;
      try {
        saved = await response.json();
      } catch (jsonError) {
        const text = await responseClone.text();
        console.error('Save JSON parse error:', jsonError, 'Response:', text);
        throw new Error('Invalid response from server');
      }
      
      if (!response.ok) {
        throw new Error(saved.detail || 'Failed to save');
      }
      
      toast.success('Recipe saved!');
      navigate(`/recipe/${saved.recipe_id}`);
      
    } catch (err) {
      toast.error('Failed to save recipe');
    } finally {
      setSaving(false);
    }
  };

  // ============================================================================
  // INITIAL LOAD FROM URL PARAMS
  // ============================================================================
  const handledShare = useRef('');
  useEffect(() => {
    // Apps put the link in different places: "url", "text" (Facebook, WhatsApp, Instagram), or "title".
    const fields = ['url', 'text', 'title'].map(k => searchParams.get(k) || '');
    const key = fields.join('|');
    if (!key.replace(/\|/g, '') || handledShare.current === key) return;
    handledShare.current = key; // run once per share, even though extractFromUrl changes identity

    let extractedUrl = '';
    for (const f of fields) {
      const m = f.match(/https?:\/\/[^\s\])}>"'<]+/);
      if (m) { extractedUrl = m[0].replace(/[)\]}>.,;!?]+$/, ''); break; }
    }
    if (!extractedUrl) {
      const m = fields.join(' ').match(/\b(?:www\.)[^\s]+\.[a-z]{2,}[^\s]*/i);
      if (m) extractedUrl = 'https://' + m[0];
    }

    if (extractedUrl) {
      setUrl(extractedUrl);
      extractFromUrl(extractedUrl);
    } else {
      // No link at all: the app shared plain recipe text, so open the paste box with it filled in.
      const plain = (fields[1] || fields[0]).trim();
      if (plain) { setPasteText(plain); setShowPasteBox(true); }
    }
  }, [searchParams, extractFromUrl]);

  // Platform icon
  const PlatformIcon = platform?.icon || Globe;

  // ============================================================================
  // RENDER: INPUT MODE
  // ============================================================================
  if (mode === 'input') {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 pb-6">
            {/* Header */}
            <div className="text-center mb-6">
              <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center">
                <Share2 className="w-7 h-7 text-white" />
              </div>
              <h1 className="text-xl font-bold">Import Recipe</h1>
              <p className="text-zinc-500 text-sm">From URL, photo, or text</p>
            </div>
            
            {/* URL Input */}
            <div className="space-y-4">
              <div>
                <label className="text-sm text-zinc-400 mb-1 block">Recipe URL</label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <input
                      type="url"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://facebook.com/..."
                      className="w-full pl-10 pr-3 py-2.5 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-orange-500"
                      onKeyDown={(e) => e.key === 'Enter' && extractFromUrl()}
                    />
                  </div>
                  <Button 
                    onClick={() => extractFromUrl()}
                    className="bg-orange-600 hover:bg-orange-700 px-4"
                  >
                    Import
                  </Button>
                </div>
                <p className="text-xs text-zinc-600 mt-1">Supports Facebook, Instagram, YouTube, and recipe websites</p>
              </div>
              
              {/* Divider */}
              <div className="flex items-center gap-3 my-4">
                <div className="flex-1 h-px bg-zinc-800" />
                <span className="text-zinc-600 text-xs">OR</span>
                <div className="flex-1 h-px bg-zinc-800" />
              </div>
              
              {/* Photo Upload Button */}
              <button
                onClick={() => setShowCamera(true)}
                className="w-full flex items-center gap-3 p-3 bg-zinc-800/50 hover:bg-zinc-800 rounded-lg border border-zinc-700 transition group"
                data-testid="photo-upload-btn"
              >
                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center group-hover:bg-blue-500/30 transition">
                  <Camera className="w-5 h-5 text-blue-400" />
                </div>
                <div className="text-left flex-1">
                  <p className="text-zinc-200 font-medium text-sm">Take Photo or Upload</p>
                  <p className="text-zinc-500 text-xs">Capture recipe card or upload image</p>
                </div>
                <Upload className="w-4 h-4 text-zinc-500 group-hover:text-zinc-400" />
              </button>
              
              {/* Hidden file inputs for camera and gallery */}
              <input 
                ref={fileRef} 
                type="file" 
                accept="image/*" 
                className="hidden" 
                onChange={handleImageUpload} 
                data-testid="gallery-file-input"
              />
              <input 
                ref={cameraRef} 
                type="file" 
                accept="image/*" 
                capture="environment" 
                className="hidden" 
                onChange={handleImageUpload} 
                data-testid="camera-file-input"
              />
              
              {/* Paste Text */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <ClipboardPaste className="w-4 h-4 text-purple-400" />
                  <span className="text-sm text-zinc-400">Paste recipe text</span>
                </div>
                <textarea
                  value={pasteText}
                  onChange={(e) => setPasteText(e.target.value)}
                  placeholder="Paste recipe text here..."
                  className="w-full h-24 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 text-sm placeholder-zinc-500 resize-none focus:outline-none focus:border-purple-500"
                />
                <Button 
                  onClick={handlePasteSubmit}
                  disabled={!pasteText.trim()}
                  className="w-full mt-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
                >
                  Parse Text
                </Button>
              </div>
            </div>
            
            <Button 
              variant="outline" 
              className="w-full mt-4 border-zinc-700 text-zinc-400"
              onClick={() => navigate('/recipes')}
            >
              Cancel
            </Button>
          </CardContent>
        </Card>
        
        {/* Camera/Gallery Selection Modal */}
        {showCamera && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50" data-testid="camera-modal">
            <Card className="w-full max-w-sm bg-zinc-900 border-zinc-700 shadow-2xl">
              <CardContent className="pt-6 pb-6">
                {/* Modal Header */}
                <div className="text-center mb-5">
                  <div className="w-14 h-14 mx-auto mb-3 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <Camera className="w-7 h-7 text-blue-400" />
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
                      cameraRef.current?.click();
                    }} 
                    className="w-full bg-blue-600 hover:bg-blue-700 h-12"
                    data-testid="camera-capture-btn"
                  >
                    <Camera className="w-5 h-5 mr-2" />
                    Take Photo with Camera
                  </Button>
                  
                  <Button 
                    onClick={() => {
                      fileRef.current?.click();
                    }} 
                    variant="outline" 
                    className="w-full border-zinc-600 hover:bg-zinc-800 h-12 text-zinc-300"
                    data-testid="gallery-upload-btn"
                  >
                    <Upload className="w-5 h-5 mr-2" />
                    Upload from Gallery
                  </Button>
                  
                  <Button 
                    onClick={() => setShowCamera(false)} 
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
      </div>
    );
  }

  // ============================================================================
  // RENDER: LOADING
  // ============================================================================
  if (mode === 'loading') {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-zinc-900 border-zinc-800">
          <CardContent className="pt-8 pb-8">
            <div className="text-center">
              <Loader2 className="w-12 h-12 mx-auto mb-4 text-orange-500 animate-spin" />
              <p className="text-zinc-300 font-medium">Extracting recipe...</p>
              {platform && (
                <div className={`inline-flex items-center gap-2 mt-2 px-3 py-1 ${platform.bg} rounded-full`}>
                  <PlatformIcon className={`w-4 h-4 ${platform.color}`} />
                  <span className={`text-sm ${platform.color}`}>{platform.name}</span>
                </div>
              )}
              <p className="text-zinc-500 text-sm mt-2">This may take a few seconds</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ============================================================================
  // RENDER: ERROR
  // ============================================================================
  if (mode === 'error') {
    return (
      <div className="min-h-screen bg-[#09090b] text-zinc-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 pb-6">
            <div className="text-center mb-6">
              <AlertCircle className="w-12 h-12 mx-auto mb-3 text-red-500" />
              <h2 className="text-lg font-semibold text-zinc-100">Import Failed</h2>
              <p className="text-zinc-400 text-sm mt-1">{error}</p>
            </div>
            
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1 border-zinc-700" onClick={() => setMode('input')}>
                Try Again
              </Button>
              <Button className="flex-1 bg-orange-600 hover:bg-orange-700" onClick={() => navigate('/recipes')}>
                Go to Recipes
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ============================================================================
  // RENDER: SUCCESS - Recipe Preview
  // ============================================================================
  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 p-4">
      <div className="max-w-2xl mx-auto">
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6 pb-6">
            {/* Success Header */}
            <div className="flex items-center gap-2 mb-4">
              {recipe?.confidence === 'user-assisted' ? (
                <AlertCircle className="w-5 h-5 text-yellow-500" />
              ) : (
                <Check className="w-5 h-5 text-green-500" />
              )}
              <span className={`font-medium ${recipe?.confidence === 'user-assisted' ? 'text-yellow-500' : 'text-green-500'}`}>
                {recipe?.confidence === 'user-assisted' ? 'Review Required' : 
                 recipe?.confidence === 'medium' ? 'Recipe Extracted - Please Verify' : 'Recipe Extracted!'}
              </span>
              {platform && (
                <span className={`ml-auto text-sm ${platform.color}`}>{platform.name}</span>
              )}
            </div>
            
            {/* Video indicator */}
            {recipe?.is_video && (
              <div className="mb-4 p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                <p className="text-sm text-purple-300 flex items-center gap-2">
                  <Youtube className="w-4 h-4 flex-shrink-0" />
                  <span>This is a video post. Recipe extracted from captions and metadata.</span>
                </p>
              </div>
            )}
            
            {/* User assistance message + Paste Box for manual entry */}
            {recipe?.needs_user_input && (
              <div className="mb-4 space-y-3">
                <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <p className="text-sm text-yellow-300 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>This content couldn't be automatically extracted. You can paste the recipe text below and we'll parse it for you.</span>
                  </p>
                </div>
                
                {/* Paste Recipe Text Button/Box */}
                {!showPasteBox ? (
                  <button
                    onClick={() => setShowPasteBox(true)}
                    className="w-full flex items-center gap-3 p-3 bg-orange-500/10 hover:bg-orange-500/20 rounded-lg border border-orange-500/30 transition group"
                    data-testid="paste-recipe-btn"
                  >
                    <div className="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center group-hover:bg-orange-500/30 transition">
                      <ClipboardPaste className="w-5 h-5 text-orange-400" />
                    </div>
                    <div className="text-left flex-1">
                      <p className="text-orange-300 font-medium text-sm">Paste Recipe Text</p>
                      <p className="text-orange-400/70 text-xs">Copy from Facebook and paste here - AI will extract the details</p>
                    </div>
                  </button>
                ) : (
                  <div className="space-y-3 p-4 bg-zinc-800/50 rounded-lg border border-zinc-700">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-zinc-300 font-medium flex items-center gap-2">
                        <ClipboardPaste className="w-4 h-4 text-orange-400" />
                        Paste Recipe Text
                      </label>
                      <button 
                        onClick={() => { setShowPasteBox(false); setPasteText(''); }}
                        className="text-zinc-500 hover:text-zinc-300 p-1"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                    <textarea
                      value={pasteText}
                      onChange={(e) => setPasteText(e.target.value)}
                      placeholder="Paste the entire recipe post here...&#10;&#10;Example:&#10;Garlic Butter Chicken&#10;&#10;Ingredients:&#10;- 4 chicken breasts&#10;- 4 tbsp butter&#10;- 6 cloves garlic&#10;&#10;Instructions:&#10;1. Season chicken with salt...&#10;2. Melt butter in pan..."
                      className="w-full h-48 px-3 py-2 bg-zinc-900 border border-zinc-600 rounded-lg text-zinc-100 placeholder-zinc-500 text-sm focus:outline-none focus:border-orange-500 resize-none"
                      data-testid="paste-recipe-textarea"
                    />
                    <div className="flex gap-2">
                      <Button
                        onClick={parseFromPastedText}
                        disabled={parsingText || !pasteText.trim()}
                        className="flex-1 bg-orange-600 hover:bg-orange-700 disabled:opacity-50"
                        data-testid="parse-recipe-btn"
                      >
                        {parsingText ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Parsing...
                          </>
                        ) : (
                          <>
                            <ChefHat className="w-4 h-4 mr-2" />
                            Parse Recipe with AI
                          </>
                        )}
                      </Button>
                      <Button
                        onClick={() => { setShowPasteBox(false); setPasteText(''); }}
                        variant="outline"
                        className="border-zinc-600 text-zinc-400 hover:bg-zinc-800"
                      >
                        Cancel
                      </Button>
                    </div>
                    <p className="text-xs text-zinc-500">
                      AI will extract the title, ingredients, quantities, and cooking steps automatically.
                    </p>
                  </div>
                )}
              </div>
            )}
            
            {/* Confidence badge and extraction source */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {recipe?.confidence && recipe.confidence !== 'high' && (
                <span className={`text-xs px-2 py-1 rounded ${
                  recipe.confidence === 'user-assisted' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {recipe.confidence === 'user-assisted' ? 'Manual Entry' : 'AI Extracted'}
                </span>
              )}
              {recipe?.confidence_score !== undefined && recipe.confidence_score < 1.0 && (
                <span className="text-xs px-2 py-1 rounded bg-zinc-700 text-zinc-400">
                  Confidence: {Math.round(recipe.confidence_score * 100)}%
                </span>
              )}
              {recipe?.external_url_found && (
                <span className="text-xs px-2 py-1 rounded bg-green-500/20 text-green-400">
                  External Recipe Found
                </span>
              )}

              {recipe?.source && (
                <span className="text-xs text-zinc-500">from {recipe.source}</span>
              )}
            </div>
            
            {/* Recipe Image */}
            {recipe?.image && (
              <div className="relative mb-4 rounded-xl overflow-hidden">
                <img loading="lazy" decoding="async" 
                  src={recipe.image} 
                  alt={recipe.title}
                  className="w-full h-48 object-cover"
                  onError={(e) => e.target.style.display = 'none'}
                />
                {recipe.source && !recipe?.needs_user_input && (
                  <span className="absolute top-2 left-2 px-2 py-1 bg-black/60 rounded text-xs">
                    {recipe.source}
                  </span>
                )}
              </div>
            )}
            
            {/* Title */}
            <h1 className="text-xl font-bold text-zinc-100 mb-2">{recipe?.title}</h1>
            
            {/* Description */}
            {recipe?.description && (
              <p className="text-zinc-400 text-sm mb-4 line-clamp-3">{recipe.description}</p>
            )}
            
            {/* Meta Info */}
            <div className="flex flex-wrap gap-2 mb-4 text-xs">
              {recipe?.prep_time && (
                <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">Prep: {recipe.prep_time}</span>
              )}
              {recipe?.cook_time && (
                <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">Cook: {recipe.cook_time}</span>
              )}
              {recipe?.servings && (
                <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">Serves: {recipe.servings}</span>
              )}
              {recipe?.difficulty && (
                <span className="px-2 py-1 bg-zinc-800 rounded text-zinc-400">{recipe.difficulty}</span>
              )}
            </div>
            
            {/* Ingredients */}
            {recipe?.ingredients?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-zinc-300 mb-2 flex items-center gap-2">
                  <ChefHat className="w-4 h-4" />
                  Ingredients ({recipe.ingredients.length})
                </h3>
                <ul className="space-y-1 max-h-40 overflow-y-auto">
                  {recipe.ingredients.map((ing, i) => (
                    <li key={i} className="text-sm text-zinc-400 flex items-start gap-2">
                      <span className="text-orange-500 mt-1">•</span>
                      <span>{ing.amount && `${ing.amount} `}{ing.item || ing}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* Instructions Preview */}
            {(recipe?.steps?.length > 0 || recipe?.instructions) && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-zinc-300 mb-2">Instructions</h3>
                {recipe.steps?.length > 0 ? (
                  <ol className="space-y-2 text-sm text-zinc-400 max-h-40 overflow-y-auto">
                    {recipe.steps.slice(0, 5).map((step, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-orange-500 font-medium">{i + 1}.</span>
                        <span className="line-clamp-2">{step}</span>
                      </li>
                    ))}
                    {recipe.steps.length > 5 && (
                      <li className="text-zinc-500">+{recipe.steps.length - 5} more steps...</li>
                    )}
                  </ol>
                ) : (
                  <p className="text-sm text-zinc-400 line-clamp-4">{recipe.instructions}</p>
                )}
              </div>
            )}
            
            {/* Source Link */}
            {recipe?.source_url && (
              <a 
                href={recipe.source_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-orange-500 hover:text-orange-400 mb-4"
              >
                <ExternalLink className="w-3 h-3" />
                View original
              </a>
            )}
            
            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t border-zinc-800">
              <Button 
                variant="outline" 
                className="flex-1 border-zinc-700 text-zinc-300"
                onClick={() => { setRecipe(null); setMode('input'); }}
              >
                Import Another
              </Button>
              <Button 
                className="flex-1 bg-orange-600 hover:bg-orange-700"
                onClick={saveRecipe}
                disabled={saving}
                data-testid="save-shared-recipe"
              >
                {saving ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Saving...</>
                ) : (
                  <><Save className="w-4 h-4 mr-2" />Save Recipe</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ShareHandler;
