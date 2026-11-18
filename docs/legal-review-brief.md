# CookMe: brief for a lawyer reviewing the Terms and Privacy Policy

**What the app is:** a recipe app (web, used on phones) for UK/EU users. Operator is based in Madrid, Spain. Contact: mail.cookme@gmail.com. Currently a friends-and-family test, planned growth to roughly 25,000 users.

**Pages to review:** `frontend/src/pages/Legal.js` (Terms of Service at /terms, Privacy Policy at /privacy).

## What the app does with personal data
- Sign-in through Google, Auth0 and others: name, email, avatar.
- Users' own recipes, meal plans, pantry, shopping lists, cookbooks.
- Optional public sharing of recipes with a consent record (`recipe_consents`: user, recipe, date).
- Comments and replies, reports against users/recipes/comments, an admin who can lock, remove or ban accounts.
- A "data export" and "delete my account" function in Profile.
- Crash reports from browsers (error message, page path, browser type; no account id) kept 30 days.
- Optional email alerts to the operator when something is reported.
- Third-party services: hosting (Emergent for now), MongoDB, Auth0, Pexels/other image sources, AI services for recipe import.

## Questions for the lawyer
1. Is the operator named correctly (`REACT_APP_OPERATOR_NAME`), and does a sole trader (autonomo) or a company need to be the data controller?
2. GDPR/UK GDPR: lawful bases, retention periods, international transfers (US hosts and AI providers), rights wording, DPO needed?
3. Do we need a cookie banner, given only login/preference storage is used?
4. User-generated content: liability under the EU Digital Services Act and UK Online Safety Act for a small platform; is our report-and-review process enough? Notice-and-action wording?
5. Licence users grant over shared recipes and comments; are the licence and moderation terms enforceable?
6. Master recipes come from Wikibooks (CC BY-SA) and other sources: is our attribution adequate, and what are the obligations if we sell a Pro plan?
7. Governing law and jurisdiction (`REACT_APP_GOVERNING_LAW`) for UK and EU consumers.
8. Age: minimum age to use the app and any parental-consent wording.
9. Subscription terms (planned later): withdrawal rights, VAT, auto-renewal rules.
10. Affiliate links (planned later): disclosure wording.
