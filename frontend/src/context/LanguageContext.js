import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const LanguageContext = createContext();

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
};

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Localisation defaults by language code (mirrors backend localisation.py)
// Used immediately on first render without an API call
const CURRENCY_MAP = {
  en: { symbol: '£', code: 'GBP' },
  es: { symbol: '€', code: 'EUR' },
  fr: { symbol: '€', code: 'EUR' },
  de: { symbol: '€', code: 'EUR' },
  it: { symbol: '€', code: 'EUR' },
  pt: { symbol: '€', code: 'EUR' },
  nl: { symbol: '€', code: 'EUR' },
  pl: { symbol: 'zł', code: 'PLN' },
  ru: { symbol: '₽', code: 'RUB' },
  zh: { symbol: '¥', code: 'CNY' },
  ja: { symbol: '¥', code: 'JPY' },
  ko: { symbol: '₩', code: 'KRW' },
  ar: { symbol: '﷼', code: 'SAR' },
  hi: { symbol: '₹', code: 'INR' },
  tr: { symbol: '₺', code: 'TRY' },
  sv: { symbol: 'kr', code: 'SEK' },
  da: { symbol: 'kr', code: 'DKK' },
  no: { symbol: 'kr', code: 'NOK' },
  fi: { symbol: '€', code: 'EUR' },
  el: { symbol: '€', code: 'EUR' },
  he: { symbol: '₪', code: 'ILS' },
  th: { symbol: '฿', code: 'THB' },
  vi: { symbol: '₫', code: 'VND' },
  id: { symbol: 'Rp', code: 'IDR' },
  ro: { symbol: 'lei', code: 'RON' },
  uk: { symbol: '₴', code: 'UAH' },
  cs: { symbol: 'Kč', code: 'CZK' },
  hu: { symbol: 'Ft', code: 'HUF' },
  ca: { symbol: '€', code: 'EUR' },
};

const MEASUREMENT_MAP = {
  en: 'uk', es: 'metric', fr: 'metric', de: 'metric', it: 'metric',
  pt: 'metric', nl: 'metric', pl: 'metric', ru: 'metric', zh: 'metric',
  ja: 'metric', ko: 'metric', ar: 'metric', hi: 'metric', tr: 'metric',
  sv: 'metric', da: 'metric', no: 'metric', fi: 'metric', el: 'metric',
  he: 'metric', th: 'metric', vi: 'metric', id: 'metric', ro: 'metric',
  uk: 'metric', cs: 'metric', hu: 'metric', ca: 'metric',
};

const DIETARY_MAP = {
  ar: { suggestHalal: true, hidePork: true },
  tr: { suggestHalal: true, hidePork: true },
  hi: { suggestVegetarian: true },
  he: { suggestKosher: true },
  id: { suggestHalal: true, hidePork: true },
};

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState({ code: 'en', name: 'English' });
  const [languages, setLanguages] = useState([]);
  const [loadingLanguages, setLoadingLanguages] = useState(false);
  const [seasonalProduce, setSeasonalProduce] = useState([]);
  const [localisationProfile, setLocalisationProfile] = useState(null);

  const getToken = () => localStorage.getItem('token') || sessionStorage.getItem('token');

  // Derived localisation values — instant, no API needed
  const currency        = CURRENCY_MAP[language.code] || { symbol: '€', code: 'EUR' };
  const measurementSystem = MEASUREMENT_MAP[language.code] || 'metric';
  const isMetric        = measurementSystem !== 'imperial';
  const dietaryDefaults = DIETARY_MAP[language.code] || {};

  // Load supported languages once
  useEffect(() => {
    const fetchLanguages = async () => {
      setLoadingLanguages(true);
      try {
        const res = await fetch(`${API_URL}/api/translate/languages`);
        if (res.ok) {
          const data = await res.json();
          setLanguages(data.languages || []);
        }
      } catch (e) {
        console.error('Failed to fetch languages', e);
      }
      setLoadingLanguages(false);
    };
    fetchLanguages();
  }, []);

  // Load language preference from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('cookme_language');
    if (stored) {
      try { setLanguage(JSON.parse(stored)); } catch {}
    }
  }, []);

  // Fetch full localisation profile + seasonal produce when language changes
  useEffect(() => {
    const fetchProfile = async () => {
      const token = getToken();
      if (!token) return;
      try {
        const res = await fetch(`${API_URL}/api/localisation/profile`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setLocalisationProfile(data);
          setSeasonalProduce(data.seasonal_produce || []);
        }
      } catch (e) {
        console.error('Failed to fetch localisation profile', e);
      }
    };
    fetchProfile();
  }, [language.code]);

  // Save language preference
  const saveLanguage = useCallback(async (code, name) => {
    const lang = { code, name };
    setLanguage(lang);
    localStorage.setItem('cookme_language', JSON.stringify(lang));
    const token = getToken();
    if (!token) return;
    try {
      await fetch(`${API_URL}/api/translate/language`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ language_code: code, language_name: name }),
      });
    } catch (e) {
      console.error('Failed to save language preference', e);
    }
  }, []);

  // Translate a recipe
  const translateRecipe = useCallback(async (recipe) => {
    if (language.code === 'en') return recipe;
    const token = getToken();
    if (!token) return recipe;
    try {
      const res = await fetch(`${API_URL}/api/translate/recipe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          recipe_id: recipe.recipe_id || null,
          title: recipe.title || '',
          description: recipe.description || '',
          ingredients: recipe.ingredients || [],
          steps: recipe.steps || [],
          tags: recipe.tags || [],
          target_language: language.code,
          target_language_name: language.name,
        }),
      });
      if (!res.ok) return recipe;
      const translated = await res.json();
      return {
        ...recipe,
        title: translated.title,
        description: translated.description,
        ingredients: translated.ingredients,
        steps: translated.steps,
        tags: translated.tags,
        _translated: true,
        _language: language.code,
      };
    } catch (e) {
      return recipe;
    }
  }, [language]);

  // Check if an ingredient is in season
  const checkSeasonal = useCallback((ingredientName) => {
    if (!seasonalProduce.length) return null;
    const lower = ingredientName.toLowerCase();
    const inSeason = seasonalProduce.some(s => lower.includes(s) || s.includes(lower));
    return inSeason;
  }, [seasonalProduce]);

  return (
    <LanguageContext.Provider value={{
      language,
      languages,
      loadingLanguages,
      saveLanguage,
      translateRecipe,
      isEnglish: language.code === 'en',
      // Localisation
      currency,
      measurementSystem,
      isMetric,
      dietaryDefaults,
      seasonalProduce,
      localisationProfile,
      checkSeasonal,
    }}>
      {children}
    </LanguageContext.Provider>
  );
};
