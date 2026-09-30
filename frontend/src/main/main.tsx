import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import { MatchesPage } from "./components/Matches/MatchesPage.tsx";
import "./index.css";

const Root = window.location.pathname.startsWith("/matches") ? MatchesPage : App;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
