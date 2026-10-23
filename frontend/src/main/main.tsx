import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { chooseScreen } from "./application/screen";
import { WhiteSpacePage } from "./components/WhiteSpace/WhiteSpacePage.tsx";
import "./index.css";

// The static staging build (VITE_STATIC_ONLY=1) leaves the matcher out of the bundle: the constant makes the dynamic import dead code.
const MatchesPage = import.meta.env.VITE_STATIC_ONLY
  ? null
  : lazy(() => import("./components/Matches/MatchesPage.tsx").then((m) => ({ default: m.MatchesPage })));
const screen = chooseScreen(window.location.pathname, window.location.search);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {MatchesPage && screen === "matcher" ? (
      <Suspense fallback={null}>
        <MatchesPage />
      </Suspense>
    ) : (
      <WhiteSpacePage />
    )}
  </StrictMode>,
);
