/** "A, B y C"; the conjunction is "e" before a name that starts with the sound /i/ ("Siemens e IBM"; "Hierros" keeps "y"). */
export function listAnd(names: string[]): string {
  if (names.length < 2) return names.join("");
  const last = names[names.length - 1];
  const conjunction = /^h?i(?![aeiouáéíóúü])/i.test(last) ? " e " : " y ";
  return `${names.slice(0, -1).join(", ")}${conjunction}${last}`;
}
