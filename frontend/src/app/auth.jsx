// لایه احراز هویت فرانت‌اند — مدیریت نشست، نقش کاربر و جریان خروج
// توکن‌ها هرگز به مرورگر داده نمی‌شوند؛ فقط کوکی httpOnly نشست با بک‌اند صحبت می‌کند.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useHttp } from "./http.js";

const AuthCtx = createContext(null);

export function useAuth() {
  return useContext(AuthCtx);
}

function readUrlFlash() {
  const params = new URLSearchParams(window.location.search);
  const flash = {};
  if (params.get("logout")) {
    flash.kind = "ok";
    flash.text = "با موفقیت خارج شدید. برای ورود مجدد از دکمه ورود سازمانی استفاده کنید.";
  }
  const err = params.get("error");
  if (err) {
    flash.kind = err === "no_access" ? "no_access" : "error";
    flash.text = ERROR_TEXTS[err] || ERROR_TEXTS.denied;
  }
  if (params.get("demoLogin") === "1") {
    flash.kind = "info";
    flash.text = "پیش‌نمایش صفحه ورود — در استقرار رسمی، دکمه ورود سازمانی فعال است.";
  }
  if (flash.kind || params.get("error") || params.get("logout")) {
    // پاکسازی پارامترها از نشانی پس از یک‌بار خواندن
    window.history.replaceState({}, "", window.location.pathname);
  }
  return flash;
}

const ERROR_TEXTS = {
  no_access: "دسترسی به این سامانه برای شما ثبت نشده است. لطفاً با مدیر سامانه تماس بگیرید.",
  sso: "ارتباط با مرکز احراز هویت سازمانی برقرار نشد. لطفاً کمی بعد دوباره تلاش کنید.",
  state: "جریان ورود منقضی یا نامعتبر بود. لطفاً دوباره وارد شوید.",
  token: "اعتبارسنجی ورود ناموفق بود. لطفاً دوباره وارد شوید.",
  rate: "تعداد تلاش‌ها بیش از حد مجاز است؛ لطفاً کمی بعد دوباره تلاش کنید.",
  denied: "ورود از سمت مرکز احراز هویت پذیرفته نشد؛ لطفاً دوباره تلاش کنید.",
};

export function AuthProvider({ children }) {
  const http = useHttp();
  const [state, setState] = useState({
    status: "loading", // loading | anon | authed
    user: null,
    config: null,
    flash: null,
  });

  const applyFlash = useCallback((flash) => setState((s) => ({ ...s, flash })), []);

  const reload = useCallback(async () => {
    try {
      const me = await http.get("/api/auth/me");
      setState((s) => ({ ...s, status: "authed", user: me.user, flash: null }));
    } catch {
      setState((s) => ({ ...s, status: "anon", user: null }));
    }
  }, [http]);

  useEffect(() => {
    const flash = readUrlFlash();
    if (flash && flash.text) applyFlash(flash);
    else if (flash && flash.kind) applyFlash(flash);
    http
      .get("/api/auth/config")
      .then((cfg) => setState((s) => ({ ...s, config: cfg })))
      .catch(() => setState((s) => ({ ...s, config: null })))
      .finally(reload);
  }, [http, reload, applyFlash]);

  const loginDemo = useCallback(
    async (role) => {
      setState((s) => ({ ...s, flash: { kind: "info", text: "در حال ورود نمایشی…" } }));
      try {
        await http.post("/api/auth/demo-login", { role });
        await reload();
      } catch (e) {
        setState((s) => ({ ...s, flash: { kind: "error", text: e.message } }));
      }
    },
    [http, reload]
  );

  const logout = useCallback(() => {
    // خروج یکپارچه: نشست محلی و نشست مرکز احراز هر دو بسته می‌شوند
    window.location.assign("/auth/logout");
  }, []);

  const value = useMemo(
    () => ({ ...state, reload, loginDemo, logout, applyFlash }),
    [state, reload, loginDemo, logout, applyFlash]
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export { ERROR_TEXTS };
