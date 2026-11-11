// ورودی سامانه — React SPA سرو شده از FastAPI (هم‌مبدأ)
import React from "react";
import { createRoot } from "react-dom/client";
import { HttpProvider, makeHttpClient } from "./app/http.js";
import DocumentApp from "./app/App.jsx";
import "./app/document.css";

const http = makeHttpClient();

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <HttpProvider value={http}>
      <DocumentApp />
    </HttpProvider>
  </React.StrictMode>
);
