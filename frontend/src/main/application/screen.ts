export type Screen = "whitespace" | "matcher";

/** The front page describes the study; the matcher keeps its own address and its shared links (`?demanda=`). */
export function chooseScreen(pathname: string, search: string): Screen {
  return pathname.startsWith("/matches") || new URLSearchParams(search).has("demanda") ? "matcher" : "whitespace";
}
