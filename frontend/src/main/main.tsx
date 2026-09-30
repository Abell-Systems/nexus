import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { MatchesPage } from "./components/Matches/MatchesPage.tsx";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MatchesPage />
  </StrictMode>,
);
