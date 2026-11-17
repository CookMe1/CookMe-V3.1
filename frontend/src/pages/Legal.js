import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

// Set these in the hosting environment (REACT_APP_...). Until then the pages say to use the in-app report buttons.
const OPERATOR = process.env.REACT_APP_OPERATOR_NAME || 'the CookMe team';
const CONTACT = process.env.REACT_APP_CONTACT_EMAIL || '';
const GOVERNING_LAW = process.env.REACT_APP_GOVERNING_LAW || '';
export const LEGAL_UPDATED = '17 November 2026';

const A = ({ href, children }) => <a className="text-orange-500 underline" href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
const H = ({ children }) => <h2 className="text-lg font-semibold text-zinc-100 mt-8 mb-2">{children}</h2>;
const P = ({ children }) => <p className="text-zinc-400 leading-relaxed mb-3">{children}</p>;
const L = ({ items }) => <ul className="list-disc pl-5 space-y-1 text-zinc-400 mb-3">{items.map((i, n) => <li key={n}>{i}</li>)}</ul>;
const Contact = () => CONTACT
  ? <>email <a className="text-orange-500 underline" href={`mailto:${CONTACT}`}>{CONTACT}</a></>
  : <>use the “Report” buttons in the app</>;

const Shell = ({ title, children }) => (
  <div className="min-h-screen bg-[#09090b] text-zinc-100">
    <div className="max-w-2xl mx-auto px-4 py-10">
      <Link to="/dashboard" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200 mb-6"><ArrowLeft className="w-4 h-4" /> Back to CookMe</Link>
      <h1 className="font-display text-3xl font-bold mb-1">{title}</h1>
      <p className="text-zinc-500 text-sm mb-6">Last updated {LEGAL_UPDATED}</p>
      {children}
      <div className="mt-10 pt-6 border-t border-zinc-800 text-sm text-zinc-500 flex gap-4">
        <Link to="/terms" className="hover:text-zinc-300">Terms of Service</Link>
        <Link to="/privacy" className="hover:text-zinc-300">Privacy Policy</Link>
      </div>
    </div>
  </div>
);

export const Terms = () => (
  <Shell title="Terms of Service">
    <P>These terms are an agreement between you and {OPERATOR} (“CookMe”, “we”) about your use of the CookMe app. By creating an account or using CookMe you agree to them. If you don’t agree, please don’t use the app.</P>

    <H>1. Your account</H>
    <L items={[
      'You must be at least 16 years old to use CookMe.',
      'You sign in through a sign-in provider (such as email via Auth0, Google, Facebook, Apple or X). Keep your sign-in details safe; you are responsible for what happens on your account.',
      'Give us accurate information and don’t share your account or pretend to be someone else.',
    ]} />

    <H>2. Your recipes stay yours</H>
    <P>Recipes, photos and notes you add are yours. By default they are private and only you can see them. We don’t claim ownership of them. You give us only the permission needed to store them and show them back to you.</P>

    <H>3. Sharing recipes publicly</H>
    <P>You can choose to make a recipe public. Before it goes public it must pass our automated checks and you must confirm the consent shown on screen. When you make a recipe public:</P>
    <L items={[
      'you confirm the recipe is your own, or that you have the right to share it, and that the photo is your own;',
      'you give CookMe a free, non-exclusive, worldwide licence to show it to other CookMe users, to translate, resize and tag it, and to feature it inside the app;',
      'other users may save a copy for their own personal use;',
      'you can make it private again at any time. We then stop showing it, but copies other people already saved can stay in their own collections;',
      'we may remove a public recipe that breaks these terms.',
    ]} />
    <P>Don’t share recipes you copied from a website, book, video or another person unless you have the right to. Recipes imported from the web can’t be made public.</P>

    <H>4. Comments and community rules</H>
    <P>You can comment on and reply to shared recipes. You are responsible for what you post. You must not post:</P>
    <L items={[
      'phone numbers, email addresses, home addresses, social media handles, web links or other ways to contact you or anyone else (our filter blocks these automatically);',
      'profanity, hate speech, harassment, threats, sexual content, or content that is illegal or unsafe;',
      'spam, adverts or promotion of products, services or websites;',
      'anyone else’s private information, or content that infringes someone’s copyright or other rights.',
    ]} />
    <P>Be kind. Comments show your first name and the initial of your surname.</P>

    <H>5. Reporting and moderation</H>
    <P>Every shared recipe and comment has a Report button. We may hide or remove content, make a recipe private, or suspend or close accounts that break these terms. If several people report the same comment it is hidden until we have reviewed it; if several people report a public recipe it is made private while we review it. If you think we got it wrong, {CONTACT ? <>contact us: <Contact />.</> : <>please <Contact />.</>}</P>

    <H>6. Recipes and food safety</H>
    <P>Recipes and nutrition information in CookMe come from a mix of sources and from other users. They are for general information, can contain mistakes, and are not medical or dietary advice. You are responsible for checking ingredients for allergies and intolerances, cooking food safely (temperatures, times, storage) and using your own judgement. Cooking involves risks such as heat, knives and food poisoning.</P>

    <H>7. Third-party content</H>
    <P>Some recipes and photos come from third parties under open licences (for example Wikibooks Cookbook under CC BY-SA 4.0, Foodista under CC BY 3.0, TheMealDB, and photos from Pexels). Credits and licences are shown on the recipe and in your profile settings. Those licences apply to that content in addition to these terms.</P>

    <H>8. Using the app fairly</H>
    <L items={[
      'Don’t try to break, overload or scrape the app, or get around its limits or content checks.',
      'Don’t use CookMe for anything illegal.',
      'Don’t copy the app’s own design, code or curated data to build a competing service.',
    ]} />

    <H>9. Availability and changes</H>
    <P>CookMe is provided “as is”. We try to keep it running and accurate but don’t promise it will always be available or error-free. We may change or stop features. We may update these terms; if the changes matter we will tell you in the app, and continuing to use CookMe means you accept them.</P>

    <H>10. Liability</H>
    <P>Nothing in these terms limits liability that can’t legally be limited (for example for death or personal injury caused by negligence, or fraud), or your legal rights as a consumer. Subject to that, we are not liable for loss that was not reasonably foreseeable, for content posted by users, or for illness or injury resulting from following a recipe.</P>

    <H>11. Closing your account</H>
    <P>You can delete your account at any time from Profile → Settings. This erases your account and the things you created. See the <Link className="text-orange-500 underline" to="/privacy">Privacy Policy</Link> for details.</P>

    {GOVERNING_LAW && (<><H>12. Governing law</H><P>These terms are governed by the laws of {GOVERNING_LAW}. This doesn’t affect any mandatory consumer rights you have where you live.</P></>)}

    <H>Contact</H>
    <P>Questions about these terms: <Contact />.</P>
  </Shell>
);

export const Privacy = () => (
  <Shell title="Privacy Policy">
    <P>This explains what personal data CookMe collects, why, who we share it with and what your rights are. {OPERATOR} is the controller of your personal data.</P>

    <H>What we collect</H>
    <L items={[
      'Account details from your sign-in provider: your name, email address and profile picture (if provided), and a unique account id. We never see or store your password.',
      'What you put in the app: recipes, photos, cookbooks, meal plans, shopping lists, pantry items, favourites, saves and likes.',
      'What you choose to share: public recipes, comments and replies, and the consent you gave when sharing (the wording you agreed to, the date, and whether you chose to show your name).',
      'Reports you make about other people’s recipes or comments.',
      'Technical data needed to run the service: login session tokens and basic server logs (such as IP address and errors).',
    ]} />
    <P>We don’t sell your data, we don’t show adverts, and we don’t use advertising or tracking cookies.</P>

    <H>Why we use it, and our legal basis</H>
    <L items={[
      'To provide the app you signed up for: store your recipes, plan meals, build shopping lists (contract).',
      'To publish a recipe or comment when you choose to share it (your consent, which you can withdraw by making it private or deleting it).',
      'To keep the community safe: automatic checks for contact details and profanity, reports, removing content and accounts that break our terms (our legitimate interest, and legal obligations).',
      'To keep the service secure and fix problems (legitimate interest).',
    ]} />

    <H>What other people can see</H>
    <L items={[
      'Private recipes and everything else in your account are visible only to you.',
      'Public recipes and comments are visible to other signed-in CookMe users. Public recipes show your name only if you chose that, otherwise “CookMe community”. Comments show your first name and surname initial.',
      'We never show your email address or account id to other users.',
    ]} />

    <H>Who we share data with</H>
    <P>We use service providers to run CookMe. They process data only on our behalf:</P>
    <L items={[
      'hosting and database provider (currently Emergent) to run the app and store data;',
      'Auth0 (Okta) for email sign-in, and Google, Facebook, Apple or X if you sign in with them;',
      'an AI provider, only when you use AI features (such as importing a recipe or generating a plan); the text you submit for that feature is sent to it.',
    ]} />
    <P>Some providers are outside the UK and EU (for example in the United States). Where that happens we rely on safeguards such as standard contractual clauses or the provider’s data-transfer framework. We may also disclose data if the law requires it.</P>

    <H>How long we keep it</H>
    <L items={[
      'Your account data and content: until you delete it or your account.',
      'Login sessions: expire automatically.',
      'Reports and moderation records: kept while needed to keep the community safe.',
      'The record that you gave consent to publish a recipe: kept (without your account details being linked to a live account) as proof of the licence you gave, for as long as the recipe could still be in other people’s saved collections.',
    ]} />

    <H>Your rights</H>
    <P>Under UK and EU data protection law you can ask to access, correct, delete, restrict or object to our use of your data, to receive it in a portable format, and to withdraw consent at any time. In the app you can:</P>
    <L items={[
      'edit or delete any recipe or comment;',
      'make a public recipe private again;',
      'download all your data and delete your account from Profile → Settings → Your data.',
    ]} />
    <P>For anything else, <Contact />. You also have the right to complain to your data protection authority (in the UK, the ICO; in Spain, the AEPD).</P>

    <H>Children</H>
    <P>CookMe is not for children under 16 and we don’t knowingly collect their data. If you think a child has an account, tell us and we will delete it.</P>

    <H>Security</H>
    <P>We use encrypted connections and verified sign-in tokens, and limit access to data. No online service is perfectly secure; if there is a breach that affects you we will tell you as the law requires.</P>

    <H>Changes</H>
    <P>If we change this policy in a way that matters we will tell you in the app and update the date above.</P>
  </Shell>
);
