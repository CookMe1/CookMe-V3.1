/**
 * Image Quality Validator
 * Evaluates images before sending to AI vision models to save costs.
 * Rejects blurry, dark, or unreadable images.
 */

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Maximum file size in bytes (1MB)
const MAX_FILE_SIZE = 1 * 1024 * 1024;

// Target quality to start compression (0.0 - 1.0)
const INITIAL_QUALITY = 0.85;

/**
 * Compress image to be under MAX_FILE_SIZE
 * @param {string} base64Data - Base64 encoded image data
 * @param {number} maxWidth - Maximum width to resize to
 * @returns {Promise<string>} - Compressed base64 image
 */
export const compressImage = (base64Data, maxWidth = 1200) => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      let width = img.width;
      let height = img.height;

      // Scale down if wider than maxWidth
      if (width > maxWidth) {
        height = Math.round((height * maxWidth) / width);
        width = maxWidth;
      }

      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, width, height);

      // Start with initial quality and reduce until under 1MB
      let quality = INITIAL_QUALITY;
      let result = canvas.toDataURL('image/jpeg', quality);

      // Iteratively reduce quality until under 1MB
      while (getBase64Size(result) > MAX_FILE_SIZE && quality > 0.1) {
        quality -= 0.1;
        result = canvas.toDataURL('image/jpeg', quality);
      }

      // If still too large, reduce dimensions further
      if (getBase64Size(result) > MAX_FILE_SIZE) {
        const smallerCanvas = document.createElement('canvas');
        const scale = 0.7;
        smallerCanvas.width = Math.round(width * scale);
        smallerCanvas.height = Math.round(height * scale);
        const smallCtx = smallerCanvas.getContext('2d');
        smallCtx.drawImage(canvas, 0, 0, smallerCanvas.width, smallerCanvas.height);
        result = smallerCanvas.toDataURL('image/jpeg', 0.7);
      }

      resolve(result);
    };
    img.onerror = () => reject(new Error('Failed to load image'));
    img.src = base64Data;
  });
};

/**
 * Calculate the byte size of a base64 string
 * @param {string} base64 - Base64 encoded string
 * @returns {number} - Size in bytes
 */
const getBase64Size = (base64) => {
  const base64Length = base64.split(',')[1]?.length || base64.length;
  return Math.round((base64Length * 3) / 4);
};

/**
 * Validate image quality using AI vision
 * @param {string} imageData - Base64 encoded image data
 * @param {string} token - Auth token
 * @returns {Promise<{valid: boolean, reason?: string}>}
 */
export const validateImageQuality = async (imageData, token) => {
  try {
    // First compress the image if needed
    const compressedImage = await compressImage(imageData);
    
    const response = await fetch(`${API_URL}/api/recipes/validate-image`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ image_data: compressedImage })
    });

    if (!response.ok) {
      // If validation endpoint fails, allow image through (fail-open)
      console.warn('Image validation endpoint failed, allowing image');
      return { valid: true, compressedImage };
    }

    const result = await response.json();
    
    return {
      valid: result.status === 'ACCEPT',
      reason: result.reason || null,
      compressedImage
    };
  } catch (error) {
    console.error('Image validation error:', error);
    // Fail-open: if validation fails, allow the image
    return { valid: true, compressedImage: imageData };
  }
};

/**
 * User-friendly rejection messages
 */
export const getRejectMessage = (reason) => {
  const messages = {
    'blurry': 'Image is too blurry. Please take a clearer photo.',
    'dark': 'Lighting is too dark. Please use better lighting.',
    'unreadable': 'Text is not readable. Please take a clearer photo.',
    'motion_blur': 'Image has motion blur. Please hold the camera steady.',
    'noise': 'Image quality is too low. Please try again.',
    'overexposed': 'Image is too bright. Please reduce lighting.',
    'partial': 'Image content is cut off. Please capture the full content.',
    'default': 'Image quality is not good enough. Please try again.'
  };

  // Match reason to message
  const lowerReason = (reason || '').toLowerCase();
  
  if (lowerReason.includes('blur')) return messages.blurry;
  if (lowerReason.includes('dark') || lowerReason.includes('light')) return messages.dark;
  if (lowerReason.includes('read') || lowerReason.includes('text')) return messages.unreadable;
  if (lowerReason.includes('motion')) return messages.motion_blur;
  if (lowerReason.includes('noise') || lowerReason.includes('quality')) return messages.noise;
  if (lowerReason.includes('bright') || lowerReason.includes('exposed')) return messages.overexposed;
  if (lowerReason.includes('partial') || lowerReason.includes('cut')) return messages.partial;
  
  return reason || messages.default;
};

export default {
  validateImageQuality,
  compressImage,
  getRejectMessage,
  MAX_FILE_SIZE
};
