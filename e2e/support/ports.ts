// Ports for the end-to-end run. Not 8000 and 5173, so `npm run dev` can stay open.
export const BACKEND_PORT = Number(process.env.SUITS_E2E_BACKEND_PORT ?? "8011");
export const CLIENT_PORT = Number(process.env.SUITS_E2E_CLIENT_PORT ?? "5183");
