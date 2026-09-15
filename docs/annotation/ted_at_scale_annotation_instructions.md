# Guía de anotación — #104 dual annotation a escala (108 pares)

Misma escala e instrucciones que el piloto PR-E.1
(`docs/annotation/pilot_pr_e1_annotation_instructions.md`), aplicadas ahora al
lote real congelado: 19 demandas del Dev split (de 30 totales; 11 no producen
ningún candidato elegible con el corpus de 63 patentes y quedan fuera de este
lote — ver `data/annotations/ted_at_scale_annotation_batch.json` campo
`zero_pool_demand_ids`), 108 pares demanda–patente en total.

## Qué vas a recibir

Tu copia individual del fichero (`ted_at_scale_annotation_valentin.csv` o
`ted_at_scale_annotation_lydia.csv`), con 108 filas demanda–patente y una
columna `judgment` en blanco. Ambas copias tienen las mismas filas en el mismo
orden — no las compares ni sincronices hasta que ambas estén completas.

## Qué tienes que hacer

Para cada uno de los 108 pares, decide: **¿qué tan relevante es esta patente
para resolver la demanda tecnológica indicada, desde un punto de vista
puramente técnico?**

Evalúa cada par de forma independiente: no compares un par con otro mientras
valoras, y no vuelvas atrás a cambiar una valoración anterior después de ver
pares posteriores.

**No estás juzgando:**
- Si la patente cualifica legalmente como antecedente (prior art).
- Si la fecha de publicación importa (no vas a ver ninguna fecha — ya fue
  evaluada por separado, ADR 0019, antes de que este lote se generara).
- Qué tan "importante" o "urgente" es la demanda.
- Qué sistema o método encontró esta patente como candidata, ni su
  posición/orden en el fichero.

## La escala de valoración (0 a 3)

| Valor | Etiqueta | Significado |
|---|---|---|
| **0** | No relevante | La patente no tiene ninguna conexión técnica significativa con la demanda. |
| **1** | Marginalmente relevante | Misma área técnica general, pero no aborda el problema real de la demanda. |
| **2** | Relevante | Aborda un componente real del problema de la demanda, o un enfoque técnico claramente análogo. |
| **3** | Altamente relevante | Aborda directamente el problema planteado por la demanda — una posible solución candidata o un antecedente técnico sustancial en sentido llano (no un juicio legal). |

**Entre 1 y 2:** un 2 requiere que la patente aborde un componente real del
problema — no solo el mismo campo general. Un 1 es "el mismo barrio"; un 2 es
"el mismo edificio."

**Entre 2 y 3:** un 3 requiere que la patente aborde el problema de la demanda
en su conjunto, no solo una parte.

**Caso especial — mecanismo alternativo:** si una patente resuelve
completamente el problema de la demanda pero mediante un mecanismo técnico
sustancialmente distinto, valórala como **2, no 3**.

## Reglas importantes

- **No modifiques** los identificadores de demanda ni de patente de ninguna fila.
- **No elimines ni dupliques** ninguna fila.
- **Completa las 108 filas.**
- Trabaja de forma independiente hasta que ambas personas hayáis terminado el
  conjunto completo — solo entonces se calcula el acuerdo entre anotadores
  (Cohen's κ) y se hace la adjudicación de discrepancias.
- El conjunto de 108 pares está cerrado de antemano (`ted_at_scale_annotation_batch.sha256`):
  tu valoración no puede añadir, quitar ni reordenar ningún par. Si una
  patente te parece irrelevante, ambigua o difícil de clasificar, eso es un
  resultado de la evaluación — no un motivo para modificar el corpus o el
  lote retrospectivamente.

## Cuándo y cómo devolver el fichero

Cuando hayas completado las 108 valoraciones, devuelve el fichero
**[canal de entrega a definir — correo / carpeta compartida / otro]**.
