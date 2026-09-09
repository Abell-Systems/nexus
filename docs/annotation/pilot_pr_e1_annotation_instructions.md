# Guía de anotación — Piloto de re-anotación ciega (38 pares)

## Qué vas a recibir

Un fichero con **38 pares demanda–patente**. Cada fila contiene una demanda tecnológica y una patente candidata, junto con una columna en blanco donde debes escribir tu valoración.

## Qué tienes que hacer

Para cada uno de los 38 pares, debes decidir: **¿qué tan relevante es esta patente para resolver la demanda tecnológica indicada, desde un punto de vista puramente técnico?**

Evalúa cada par **de forma independiente**: no compares un par con otro mientras valoras, y no vuelvas atrás a cambiar una valoración anterior después de ver pares posteriores.

**No estás juzgando:**
- Si la patente cualifica legalmente como antecedente (prior art).
- Si la fecha de publicación importa (no vas a ver ninguna fecha).
- Qué tan "importante" o "urgente" es la demanda.
- Qué sistema o método encontró esta patente como candidata (tampoco lo vas a ver).

Si en algún momento te sorprendes razonando sobre fechas, prioridad o legalidad, esa idea no pertenece a esta tarea — ignórala y sigue con la evaluación puramente técnica.

## Qué información puedes usar para decidir

Por cada par verás únicamente:
- El título y la descripción de la demanda.
- El identificador, título, resumen (abstract) y clasificación técnica (CPC) de la patente candidata — como evidencia auxiliar, no como pista ni recomendación.

**No verás** ninguna puntuación de relevancia, qué método la encontró, su posición en ninguna lista, ni su fecha de publicación. Si la evidencia de un par te parece demasiado escasa para decidir con seguridad, valora con lo que tienes delante — no busques la patente por tu cuenta fuera del fichero, porque eso reintroduciría información (como la fecha) que deliberadamente no debes usar.

## La escala de valoración (0 a 3)

| Valor | Etiqueta | Significado |
|---|---|---|
| **0** | No relevante | La patente no tiene ninguna conexión técnica significativa con la demanda. |
| **1** | Marginalmente relevante | Misma área técnica general, pero no aborda el problema real de la demanda. |
| **2** | Relevante | Aborda un componente real del problema de la demanda, o un enfoque técnico claramente análogo. |
| **3** | Altamente relevante | Aborda directamente el problema planteado por la demanda — una posible solución candidata o un antecedente técnico sustancial en sentido llano (no un juicio legal). |

### Cómo distinguir los casos más difíciles

**Entre 1 y 2:** un 2 requiere que la patente aborde un componente real del problema (el mismo sub-problema, el mismo requisito funcional, o un mecanismo técnico claramente análogo) — no solo el mismo campo general. Un 1 es "el mismo barrio"; un 2 es "el mismo edificio."

**Entre 2 y 3:** un 3 requiere que la patente aborde el problema de la demanda **en su conjunto**, no solo una parte — aunque no sea una solución perfecta, un 3 debería sentirse como "si yo tuviera que resolver esta demanda, miraría esta patente de cerca," no como "esto es una pieza de una posible solución."

**Caso especial — mecanismo alternativo:** si una patente resuelve completamente el problema de la demanda pero mediante un mecanismo técnico sustancialmente distinto al que describe la demanda (por ejemplo, una solución química para una demanda planteada en términos mecánicos), valórala como **2, no 3**. Para un 3, el mecanismo debe coincidir, no solo el resultado final.

## Cómo registrar tu valoración

Junto a cada par, en la columna correspondiente, escribe únicamente el número de tu valoración: **0, 1, 2 o 3**. No dejes ninguna fila sin valorar.

## Reglas importantes

- **No modifiques** los identificadores de demanda ni de patente de ninguna fila.
- **No elimines ni dupliques** ninguna fila.
- **Completa las 38 filas** — el fichero no está completo si falta alguna.
- Trabaja de forma independiente: no comentes valoraciones concretas con nadie más hasta que ambas personas hayan terminado el conjunto completo.
- El conjunto de 38 pares está cerrado de antemano: tu valoración no puede añadir, quitar ni reordenar ningún par.

## Cuándo y cómo devolver el fichero

Cuando hayas completado las 38 valoraciones, devuelve el fichero **[canal de entrega a definir — correo / carpeta compartida / otro]**.
