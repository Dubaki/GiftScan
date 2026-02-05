import WebApp from "@twa-dev/sdk";

export function useTelegram() {
  const user = WebApp.initDataUnsafe?.user;

  return {
    webApp: WebApp,
    user,
    userId: user?.id,
    username: user?.username,
    colorScheme: WebApp.colorScheme, // "light" | "dark"
  };
}
