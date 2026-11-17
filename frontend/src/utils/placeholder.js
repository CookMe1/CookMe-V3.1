// Neutral "no photo yet" tile. Used instead of a repeated stock photo, which would look like a fake/duplicate image.
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#27272a"/><stop offset="1" stop-color="#18181b"/></linearGradient></defs><rect width="800" height="600" fill="url(#g)"/><g fill="none" stroke="#f97316" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity="0.85"><circle cx="400" cy="290" r="95"/><circle cx="400" cy="290" r="55" opacity="0.5"/><path d="M270 205v110M250 205v55a20 20 0 0 0 40 0v-55M530 205c-20 0-30 40-30 75h30v35"/></g><text x="400" y="460" text-anchor="middle" font-family="sans-serif" font-size="30" fill="#71717a">Photo coming soon</text></svg>`;
export const PLACEHOLDER_IMAGE = `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;

// onError handler: swap to the placeholder once (no loop if the placeholder itself fails)
export const onImageError = (e) => {
  e.target.onerror = null;
  e.target.src = PLACEHOLDER_IMAGE;
};
