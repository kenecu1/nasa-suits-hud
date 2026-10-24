const bridgeUrl = import.meta.env.VITE_BRIDGE_URL;
if (!bridgeUrl) throw new Error('VITE_BRIDGE_URL is not set in hud/.env');

export const config = {
  bridgeUrl,
};