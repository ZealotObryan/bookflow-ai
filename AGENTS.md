# BookFlow AI UI Engineering Rules

## Responsive layout
- Build mobile-first from 320px upward; verify 375px, 768px, 1024px and 1440px layouts.
- Prefer intrinsic layouts: CSS Grid with `auto-fit/minmax`, flex wrapping, min/max sizing and content-driven layout primitives.
- Avoid fixed-width page containers. Use `width: 100%`, sensible `max-width`, and fluid gutters.
- Use `clamp()` for typography, spacing and component sizing. Keep long content shrinkable with `min-width: 0` and allow safe wrapping.
- Use container queries for reusable cards, panels, widgets and forms that can appear in differently sized regions.
- Use `100dvh`/ `min-height: 100dvh` for viewport-bound app surfaces and account for `env(safe-area-inset-*)` on mobile.

## Touch and accessibility
- Interactive controls should have at least a 44px touch target wherever practical.
- Essential actions must never depend on hover. Preserve visible keyboard focus and semantic controls.
- Complex menus, dialogs and popovers must support keyboard navigation, focus management, escape dismissal and screen readers.
- Respect `prefers-reduced-motion`; do not animate essential information in a way that blocks access.

## Motion and performance
- Prefer CSS for simple transitions. Add Motion or AutoAnimate only where a real interaction benefits from it.
- Animate transform and opacity rather than layout-heavy properties.
- Avoid entrance effects that cause content flashes, cumulative layout shift or delayed access to controls.
- Use responsive images and lazy-load below-the-fold media where appropriate.

## Quality gate
- Check for horizontal overflow, clipped dialogs, unreachable controls, tiny tap targets and text collisions.
- Test keyboard-only navigation and reduced-motion mode.
- Verify dashboard, public booking, authentication and onboarding independently at narrow and wide widths.
- Do not claim visual QA or deployment until the relevant checks have actually completed.
