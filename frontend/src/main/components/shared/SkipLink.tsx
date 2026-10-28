import { SKIP_TEXT } from "../../domain/whitespace";

// First focusable element of a page; its target is the main landmark (id="contenido", focusable by script so that the focus really moves there).
export function SkipLink() {
  return <a className="skip" href="#contenido">{SKIP_TEXT}</a>;
}
