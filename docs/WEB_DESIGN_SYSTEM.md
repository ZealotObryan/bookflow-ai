# BookFlow AI web design system

## Visual direction
A calm, premium operations workspace for service businesses: warm off-white surfaces, deep botanical green, restrained sage accents, generous spacing, compact data density and subtle motion. Avoid generic admin-template styling and decorative motion that competes with operational tasks.

## Reference resources
- [21st.dev](https://21st.dev/): React/Tailwind component discovery and composition patterns.
- [React Bits](https://www.reactbits.dev/): restrained interaction and animation inspiration; respect reduced-motion preferences.
- [Magic UI](https://magicui.design/docs): polished marketing sections and presentation patterns.
- [Uiverse](https://uiverse.io/): small interaction and control inspiration. Review individual source terms before reuse; the site describes its elements as MIT licensed.
- [Mobbin](https://mobbin.com/): UX research for real product flows, navigation, information hierarchy, tables, onboarding and responsive behavior. Use as inspiration, not copied proprietary screens.

## Implementation principles
- Next.js App Router, React, TypeScript, CSS variables and lucide-react.
- Source-owned components; no remote component runtime.
- Responsive navigation and tables, keyboard focus visibility and reduced-motion support.
- Preview records are explicitly labelled and stored only in the current browser.
- No credentials, access tokens or personal data are stored in localStorage.
- Real backend integration must replace preview-only state before handling live customer data.

## Current scope
Marketing landing page and interactive dashboard preview. Dashboard actions mutate browser-local preview data only. Authentication, business onboarding, CRUD persistence, Google Calendar, WhatsApp and payment integrations remain follow-on work.
