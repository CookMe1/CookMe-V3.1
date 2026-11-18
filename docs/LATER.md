# Parked for later (agreed with Kabir, Nov 2026)

Pick these back up once the rest of the app is finished. Free methods only for now.

## 1. Home fetcher for blocked recipe sites
Some sites (Serious Eats, NYT) block data-centre servers, so server-side import fails.
- Run a tiny fetcher program on a home machine (Raspberry Pi, old PC or the Mac). A home connection looks like a normal reader.
- Expose it with a free Cloudflare Tunnel (a domain, about 10 EUR a year, gives a permanent address).
- Add it to `backend/page_fetch.py` as the last step after the free methods, behind two settings: the tunnel address and a shared secret. Off until both are set.
- Must: require the secret, fetch only public web pages (never home-network addresses), rate-limit, rely on the 30-day import cache.
- Fallback when it is down: the paste-text box (already built).

## 2. Other import options
- Desktop bookmarklet ("Save to CookMe") that reads the page in the user's own browser.
- Capacitor Android wrapper: fetches pages from the phone itself (how Stashcook-style apps work), plus Play Store listing and one-tap share.
- Clearer message on blocked sites: "select the recipe text and share it again".

## 3. Other open items
- Hosting move (Cloudflare Pages frontend, Koyeb/Cloud Run backend, MongoDB Atlas free) as its own project.
- Monetisation (Stripe Pro / affiliate links) when asked.
- Timer alarm sound/vibration; photo import.
