// Ports for the end-to-end run. Not 8000 and 5173, so `npm run dev` can stay open.
function port(name: string, fallback: number): number {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > 65535) throw new Error(`${name} must be a port number, got "${raw}"`);
  return value;
}

export const BACKEND_PORT = port("SUITS_E2E_BACKEND_PORT", 8011);
export const CLIENT_PORT = port("SUITS_E2E_CLIENT_PORT", 5183);
