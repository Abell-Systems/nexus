export type Screen = "whitespace" | "matcher" | "topics";

/** The front page describes the study; the matcher keeps its own address and its shared links (`?demanda=`). */
export function chooseScreen(pathname: string, search: string): Screen {
  if (pathname.startsWith("/temas")) return "topics";
  return pathname.startsWith("/matches") || new URLSearchParams(search).has("demanda") ? "matcher" : "whitespace";
}
