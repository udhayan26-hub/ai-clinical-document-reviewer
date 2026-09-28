# 001. Frontend stack: React + TypeScript + Vite + Tailwind CSS

## Problem

The frontend must let a user submit a clinical document (text, image, or PDF), show processing status, and render a structured clinical report and history — as a genuinely separate application from the backend, communicating only over the REST contract in `docs/architecture/system-architecture.md`.

## Decision

React with TypeScript, built with Vite, styled with Tailwind CSS. This was specified as the required technology direction for the assignment; this record captures the rationale for why it's a reasonable fit rather than re-litigating the choice.

## Rationale

- **TypeScript** lets the frontend mirror the backend's Pydantic contracts as compile-checked types (`frontend/src/types/api.ts`, `clinicalReport.ts`), so a drift between what the API returns and what the UI expects is a compile error, not a runtime surprise — important for a report shape with as many optional/nested fields as `ClinicalReport`.
- **Vite** gives a fast local dev loop and a standard `build`/`preview` split that maps directly onto the Docker/CI setup (`npm run build` is exactly what CI and the production image run).
- **Tailwind CSS** avoids hand-rolling a component styling system before there's any UI to style, while still being straightforward to remove/replace per-component if a design system is introduced later.

## Alternatives Considered

- **Next.js** — would blur the "frontend and backend must be separate" requirement (its API routes and SSR data-fetching encourage backend logic living in the frontend project); a plain Vite SPA keeps the boundary explicit.
- **Vue / Svelte** — equally viable technically; not chosen because React has the largest available ecosystem for the kind of document/report UI this app needs (file upload widgets, structured-data display), and it was the specified direction.
- **CSS Modules / styled-components** instead of Tailwind — more ceremony per component with no clear benefit at this project's current size; revisit if the design system grows complex enough to want co-located component styles.

## Trade-offs

- Tailwind's utility classes can make markup noisier than semantic class names; acceptable for an internal/assignment-scale UI.
- No SSR/SEO — irrelevant here since this is an authenticated-style internal tool, not a public content site.
- Hand-mirrored TypeScript types (rather than generated from the OpenAPI schema) can drift from the backend if not kept in sync manually — tracked as a follow-up in `002-backend.md`.
