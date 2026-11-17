import React, { useEffect, useState } from 'react';

/**
 * Google AdMob-style Adaptive Banner Component
 * 
 * CONFIGURATION:
 * To enable real ads, set these in your .env file:
 * - REACT_APP_ADMOB_PUBLISHER_ID=ca-pub-XXXXXXXXXXXXXXXX
 * - REACT_APP_ADMOB_AD_UNIT_ID=ca-app-pub-XXXXXXXXXXXXXXXX/XXXXXXXXXX
 * 
 * For testing, you can use Google's test ad unit IDs:
 * - Test Banner: ca-app-pub-3940256099942544/6300978111
 */

const AdBanner = () => {
  const [adLoaded, setAdLoaded] = useState(false);
  const [adError, setAdError] = useState(false);
  
  // Configuration - replace with your actual AdMob IDs
  const publisherId = process.env.REACT_APP_ADMOB_PUBLISHER_ID || '';
  const adUnitId = process.env.REACT_APP_ADMOB_AD_UNIT_ID || '';
  // Consider configured if publisher ID is set (ad unit can use auto placement)
  const isConfigured = publisherId && publisherId.startsWith('ca-pub-');

  useEffect(() => {
    // Only load Google AdSense script if configured with real IDs
    if (isConfigured && !window.adsbygoogle) {
      const script = document.createElement('script');
      script.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${publisherId}`;
      script.async = true;
      script.crossOrigin = 'anonymous';
      script.onload = () => setAdLoaded(true);
      script.onerror = () => setAdError(true);
      document.head.appendChild(script);
    } else if (isConfigured) {
      setAdLoaded(true);
    }
  }, [publisherId, isConfigured]);

  useEffect(() => {
    // Initialize ad when script is loaded
    if (adLoaded && isConfigured && window.adsbygoogle) {
      try {
        (window.adsbygoogle = window.adsbygoogle || []).push({});
      } catch (e) {
        console.log('AdSense error:', e);
      }
    }
  }, [adLoaded, isConfigured]);

  return (
    <div 
      className="fixed bottom-0 left-0 right-0 z-[9999] bg-zinc-950 border-t border-zinc-800"
      data-testid="ad-banner-container"
      style={{ 
        minHeight: '50px',
        maxHeight: '100px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
    >
      {isConfigured ? (
        // Real Google Ad
        <ins
          className="adsbygoogle"
          style={{ 
            display: 'block',
            width: '100%',
            height: 'auto',
            minHeight: '50px',
            maxHeight: '100px'
          }}
          data-ad-client={publisherId}
          data-ad-slot={adUnitId ? (adUnitId.split('/')[1] || adUnitId) : 'auto'}
          data-ad-format="auto"
          data-full-width-responsive="true"
          data-testid="google-ad-unit"
        />
      ) : (
        // Placeholder Banner - shows when AdMob is not configured
        <div 
          className="w-full h-full flex items-center justify-center px-4 py-2"
          data-testid="ad-placeholder"
        >
          <div className="flex items-center gap-3 text-zinc-500">
            <div className="flex items-center gap-2">
              <svg 
                className="w-5 h-5 text-zinc-600" 
                viewBox="0 0 24 24" 
                fill="none" 
                stroke="currentColor" 
                strokeWidth="1.5"
              >
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="M7 15h0M12 15h0M17 15h0" strokeLinecap="round" />
                <path d="M7 9h10" />
              </svg>
              <span className="text-xs font-medium tracking-wide uppercase">
                Ad Space
              </span>
            </div>
            <span className="text-zinc-600 text-xs hidden sm:inline">
              Configure REACT_APP_ADMOB_PUBLISHER_ID to display ads
            </span>
          </div>
        </div>
      )}
      
      {/* Error state */}
      {adError && isConfigured && (
        <div className="absolute inset-0 flex items-center justify-center bg-zinc-950">
          <span className="text-zinc-600 text-xs">Ad failed to load</span>
        </div>
      )}
    </div>
  );
};

export default AdBanner;
