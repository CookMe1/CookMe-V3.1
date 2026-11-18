import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// Report crashes to our own server (shown in Admin) so problems are noticed. Max 5 per visit.
let reported = 0;
const report = (message, stack) => {
  try {
    if (reported++ >= 5 || !process.env.REACT_APP_BACKEND_URL) return;
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/monitoring/client-error`, {
      method: "POST", keepalive: true, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: String(message || ""), stack: String(stack || ""), url: window.location.pathname }),
    }).catch(() => {});
  } catch (e) { /* never let reporting break the app */ }
};
window.addEventListener("error", (e) => report(e.message, e.error && e.error.stack));
window.addEventListener("unhandledrejection", (e) => report(e.reason && e.reason.message ? e.reason.message : e.reason, e.reason && e.reason.stack));

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
