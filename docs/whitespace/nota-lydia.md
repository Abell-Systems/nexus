# Abell Nexus: de las ausencias de co-clasificación a la evaluación de señales predictivas

**Nota de decisión · 21 de octubre de 2026.** Acompaña a la [pieza descriptiva](briefing-lydia.html), que muestra la cobertura de los datos y un mapa de lo ya observado. Todas las cifras proceden de resultados versionados en este repositorio.

## 1. Qué problema abordamos
Buscamos pares de subclases IPC que nunca han aparecido juntos en los documentos publicados por la OEPM. Hay muchos: unos 135.000 en el origen 2006. Una ausencia **no** es una oportunidad: indica solo que no se ha observado co-clasificación en este corpus y periodo, y no demuestra que las áreas no se combinen.

El protocolo (ADR 0036) comprueba si un ranking acierta mejor que unas reglas sencillas las primeras apariciones posteriores de esos pares. **No hemos demostrado que funcione**: todavía no existen las líneas base ni el detector.

## 2. Tres niveles
- **Nivel 1, descriptivo (existe):** listar ausencias. Describe el corpus.
- **Nivel 2, predictivo (objetivo del estudio):** ¿un ranking prioriza las apariciones posteriores mejor que una regla sencilla, con evaluación temporal preregistrada? Un resultado positivo probaría capacidad predictiva sobre publicaciones de la OEPM, no una oportunidad de innovación.
- **Nivel 3, estratégico (fuera de alcance):** si una combinación es relevante, viable o de interés comercial. Necesitaría otra pregunta, otras fuentes y validación experta.

## 3. Lo que hemos aprendido sobre los datos
Hemos comparado el corpus con el inventario oficial de la OEPM (todas las publicaciones, sin clasificación), publicación por publicación.

- El corpus **coincide casi por completo con el inventario en las publicaciones que contiene** (solo 384 de 708.176 no figuran en él). Eso no significa que **tenga cobertura completa**.
- **Faltan todas las publicaciones de tipo Y de 2000 a 2009** (qué denota ese tipo no lo hemos leído) y **todo el año 2010** (25.849 publicaciones). Hay huecos menores en 2011–2020.
- Hasta el origen 2003 falta el 13,75 % del inventario; hasta 2006, el 11,24 %.
- **La historia observada es corta**: el corpus empieza en 2000, así que los orígenes de desarrollo 2003 y 2006 tienen 4 y 7 años.
- Los recuentos del estudio dependen mucho más de la longitud y composición de esa historia (entre un 4 % y un 32 %) que de una pérdida aleatoria a las tasas conocidas (menos del 0,6 %).
- **No podemos estimar el efecto de la ausencia del tipo Y**: el inventario no incluye clasificaciones y no hay publicaciones Y observadas en esos años con las que simular.

## 4. Tres cuestiones distintas
| Cuestión | Qué es | Quién la decide |
|---|---|---|
| **Relevancia práctica** | Qué mejora del ranking merecería la pena | Abell |
| **Potencia estadística** | Qué diferencia puede detectar el diseño con estos datos | Depende de la anterior y de la variabilidad medida en desarrollo |
| **Limitaciones de cobertura** | Qué podemos afirmar con el corpus que tenemos | Lo que muestra la sección 3; condiciona la interpretación, no la utilidad |

## 5. Las preguntas para Lydia
**1. ¿Qué mejora justificaría usar el ranking?** Formalmente se mide con AUC-PR frente a la mejor regla sencilla, pero es más fácil pensarlo así: si el ranking propone 100 pares para revisión experta, ¿cuántos aciertos más que la regla sencilla harían que mereciera la pena? Se fija antes de ver resultados. Si ninguna mejora razonable es detectable con estos datos, el estudio debe poder concluirlo.

**2. Sobre los datos.** El corpus tiene IPC, fechas y solicitantes; no tiene texto, CPC ni familias. La OEPM publica además resúmenes, texto completo, CPC (desde 2013), estado legal (desde 2010) y citas; ningún conjunto trae familias. ¿Qué limitación concreta os impide responder a vuestra pregunta: contenido tecnológico, una clasificación más fina, familias, o es que la pregunta del estudio no es la que queréis responder?

**3. ¿Es el nivel estratégico un objetivo futuro?** No hace falta incorporarlo ahora.

**Propuesta:** cerrar primero el criterio de utilidad práctica y la potencia, y evaluar después sin confundir ausencia, predicción y oportunidad.
