# Bloub for Flowly

Upstream: https://github.com/jeremy-prt/bloub

Revision: `b4bb3c1b5f93c7b87a2e8d620f667c4093d97749` (2026-10-19).

The complete upstream Vue application, animation engine, customizer, timeline editor,
locales and export implementations are retained in `src/`, together with their tests.
The MIT license and upstream credits are preserved. The code license does not grant
rights to x.ai trademarks or the visual design it recreates.

Flowly adaptations:

- Built locally into `public/avatar-studio` and embedded in the authenticated personal center.
- Default language is Chinese; French and English remain available.
- Browser persistence is namespaced by Flowly account ID.
- `flowlyBridge.ts` and `App.vue`'s exposed capture method supply shape, color, expression
  and animation sequence preferences to the parent. The header renders a live avatar
  without a circular frame. Uploaded images remain an explicit profile choice.
- Monochrome bodies and eyes invert with the parent theme; colored bodies retain their
  selected color with white eyes. The original selection is preserved.
- Preferences use the authenticated profile API and per-account browser persistence.
  When an older backend omits this field, the UI explicitly reports local-only storage;
  account synchronization requires loading the updated backend and reapplying the design.
- The studio is isolated from the main app's Vue styles, themes and routing.
- Build tooling uses the parent app's dependencies; `npm run build:avatar` includes TypeScript checks.
- Upstream TypeScript is checked with `vue-tsc`; upstream tests run with `npm run test:avatar`.
  It is excluded from the main app's JavaScript-only ESLint parser, not from validation.

The existing lightweight avatar used elsewhere in Flowly remains separately vendored at
`src/vendor/bloub` to preserve its application feedback behavior. This workspace does not
replace those runtime state bindings.
