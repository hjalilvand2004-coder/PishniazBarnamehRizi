// ورودی سامانه — React SPA سرو شده از FastAPI (هم‌مبدأ) با پوسته احراز هویت
import React from "react";
import { createRoot } from "react-dom/client";
import { HttpProvider, makeHttpClient } from "./app/http.js";
import App from "./app/App.jsx";
import "./app/document.css";

const http = makeHttpClient();

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HttpProvider value={http}>
      <App />
    </HttpProvider>
  </React.StrictMode>
);
