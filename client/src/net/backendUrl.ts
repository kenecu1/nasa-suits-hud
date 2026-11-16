// The backend is reached through the page's own origin: the dev server forwards /ws to it
// (client/vite.config.ts). So the headset needs only one address, the page's.
export function wsUrl(pageUrl: string): string {
  const url = new URL("/ws", pageUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url.toString();
}
