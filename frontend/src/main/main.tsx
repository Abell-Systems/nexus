import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { chooseScreen } from "./application/screen";
import { MatchesPage } from "./components/Matches/MatchesPage.tsx";
import { WhiteSpacePage } from "./components/WhiteSpace/WhiteSpacePage.tsx";
import "./index.css";

const screen = chooseScreen(window.location.pathname, window.location.search);

createRoot(document.getElementById("root")!).render(
  <StrictMode>{screen === "matcher" ? <MatchesPage /> : <WhiteSpacePage />}</StrictMode>,
);
