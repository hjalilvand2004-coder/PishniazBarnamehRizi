// لایه ارتباط با بک‌اند FastAPI — مستقل از هاست (Next یا Vite)
// هر هاست یک آبجکت http با متدهای get و url ارائه می‌کند:
//   get(path) -> Promise<json>
//   url(path) -> string (برای لینک‌های دانلود)
import { createContext, useContext } from "react";

export const HttpCtx = createContext({
  get: async () => {
    throw new Error("هسته ارتباط با سرور فراهم نشده است");
  },
  url: (p) => p,
});

export const HttpProvider = HttpCtx.Provider;

export function useHttp() {
  return useContext(HttpCtx);
}

export function makeHttpClient({ baseUrl = "", transformPath = (p) => p } = {}) {
  const build = (path) => baseUrl + transformPath(path);
  return {
    get: async (path) => {
      const res = await fetch(build(path), { headers: { Accept: "application/json" } });
      if (!res.ok) {
        throw new Error(`پاسخ ناموفق از سرور (کد ${res.status})`);
      }
      return res.json();
    },
    url: build,
  };
}
