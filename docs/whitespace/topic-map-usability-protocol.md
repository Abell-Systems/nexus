# Mapa de temas tecnológicos: protocolo de prueba de usabilidad

**Estado:** Protocolo fijado antes de la sesión. No hay sesiones realizadas ni resultados; este documento no afirma nada sobre participantes.
**Fecha:** 2026-10-29
**Fuente:** [diseño del producto](../superpowers/specs/2026-10-29-technology-topic-map-product-design.md) §5, §11 · `frontend/src/main/domain/topicMap.ts` · `frontend/src/main/application/topicSummary.ts` · `frontend/src/main/components/TopicMap/`

## 1. Propósito

Comprobar si personas que hacen vigilancia tecnológica, sin explicación previa, entienden las cuatro vistas del mapa (¿Cómo evoluciona?, ¿De qué trata?, ¿Quién está?, Pistas sin explorar) y la marca «Nombres sin revisar». Se observa qué entienden, qué preguntan y qué echan en falta; no si les gusta.

**Prueba formativa.** Participan 2 o 3 personas (diseño §11: «dos o tres»). Con tan pocos participantes no hay afirmaciones estadísticas ni de usabilidad general: solo sirve para encontrar fallos de comprensión y corregirlos. Criterio de la fase: se da por entendido si al menos 2 de 3 (o 2 de 2, si solo hay dos) contestan bien, sin ayuda y en menos de 2 minutos, las preguntas **1 a 3** para un tema que no habían visto antes (diseño §11). Las preguntas 4 y 5 son informativas y no cuentan para el criterio.

Participantes: 2 o 3 personas ajenas al desarrollo y no expertas en clasificación de patentes (diseño §13, «First users»). Nadie se nombra aquí hasta confirmar disponibilidad e independencia.

## 2. Datos que se pueden usar

- **D4 está sin resolver** (el propietario debe leer el aviso legal de la OEPM y registrar fecha y lectura). Hasta entonces **no se puede usar ningún resultado derivado del corpus real**. Hoy **no existe ningún resultado sintético compartible**: el fixture está en línea en `frontend/test/unit/TopicMapPage.test.tsx` (líneas 9-34). Las sesiones necesitan, por tanto, o bien un JSON sintético solo de desarrollo (por crear, nunca servido ni con datos reales), o bien esperar a la Tarea 13, bloqueada hasta que D4 conste. Un tema sintético llamado «Baterías» no puede ser un tema «no visto antes»: la persona lo asociaría con el real.
- **No existe un tema sin usar.** Los umbrales de «menos de lo esperado» (O ≥ 30, E ≥ 30, O/E < 0,8) se eligieron mirando baterías y solar, los dos únicos temas del catálogo. Cualquier tema real que se use ya influyó en esas decisiones; hay que decirlo al interpretar resultados. Lo que sí es nuevo para la persona es el tema: se le pide uno que no haya visto antes dentro de la sesión.
- Si el resultado tiene `names_reviewed: false` la interfaz muestra «Nombres sin revisar» en todas las vistas; es lo esperado en el fixture sintético y es lo que mide la pregunta 5.

## 3. Instrucción uniforme (se lee igual a cada participante)

Se leen dos variantes, según el régimen de datos; cada participante oye solo la que corresponde y todos los de un régimen oyen la misma.

**Datos reales (solo tras D4):**

> «Esto es un prototipo que enseña datos de patentes publicadas en España sobre un tema. No estamos evaluándote a ti, sino la pantalla. Te haré cinco preguntas, una por una. Contesta en voz alta lo que veas en la pantalla y di lo que pienses mientras la usas. No puedo ayudarte ni explicarte nada mientras tanto. Si no sabes la respuesta, dilo y pasamos a la siguiente. Tienes unos dos minutos por pregunta.»

**Datos sintéticos:**

> «Esto es un prototipo. Los datos que verás en la pantalla están inventados, solo sirven para probar la pantalla; no son patentes reales ni dicen nada de ninguna empresa. No estamos evaluándote a ti, sino la pantalla. Te haré cinco preguntas, una por una. Contesta en voz alta lo que veas en la pantalla y di lo que pienses mientras la usas. No puedo ayudarte ni explicarte nada mientras tanto. Si no sabes la respuesta, dilo y pasamos a la siguiente. Tienes unos dos minutos por pregunta.»

La persona moderadora no explica, no señala y no confirma ni corrige respuestas. Si pregunta algo, responde «Haz lo que te parezca» y se anota la pregunta. La pantalla de partida es la de resumen del tema (frase y cuatro botones), con el tema ya abierto.

## 4. Preguntas y respuestas aceptadas

Las respuestas se calculan **antes de la sesión** del JSON de resultado del tema (`TopicMapResult`) y se escriben en la hoja de observación. Las cifras se comparan tal como las muestra la pantalla (redondeadas a número entero).

| # | Vista | Pregunta (literal) | Respuesta aceptada y regla |
|---|---|---|---|
| 1 | ¿Cómo evoluciona? | «¿Se publican más o menos documentos al año ahora que a principios de los 2000? ¿En qué año se publicaron más?» | Media 2024–2025 frente a media 2000–2009, calculadas como `periodAverages`: media de `trend[].documents` de los años del periodo presentes en `trend` (2010 no existe y no cuenta como cero). Se comparan **las cifras tal como las imprime la pantalla** (`docsPerYear`): `Math.round`, y «menos de 1 documento al año» cuando 0 < media < 1. «Más» o «menos» si las cifras mostradas difieren (distinta cadena; «menos de 1» es menor que «1»); «parecido» si la cadena mostrada es idéntica. Año: `peakYears`, el año (o años, todos si hay empate) con `trend[].documents` máximo. Si el periodo inicial o el reciente no tiene datos, la pregunta se sustituye por una sobre 2011–2023 y se anota. No se usan temas con todos los años a cero (la pantalla solo dice «No hay documentos de este tema desde 2000.»). Correcta solo si acierta la comparación **y** el año (cualquiera de los empatados). |
| 2 | ¿De qué trata? | «¿Cuál es la parte más grande de este tema?» | `subareas[].name` con mayor `documents`. Si hay empate, valen todos los empatados. Un tema sin `subareas` con `documents > 0` no sirve para esta pregunta. |
| 3 | ¿Quién está? | «¿Qué empresa o entidad aparece más como solicitante en total, sumando todos los años?» | El máximo de `applicants[].documents`; se aceptan los nombres de todas las entidades empatadas en ese máximo (normalmente `applicants[0].name`). Vale su nombre sin la forma jurídica; las variantes de `originals` no cuentan como otra entidad. Si la persona nombra al líder reciente que muestra ¿Cómo evoluciona? (`top_applicant_recent`, 2024–2025) y no coincide, se anota como comentario y no como error cuando la propia pantalla lo dice así; si la pregunta se contesta con otro dato que la pantalla no dice, es error. |
| 4 | Pistas sin explorar | «¿Con qué otras tecnologías se combina este tema menos de lo que cabría esperar?» | Cualquiera de los `rare[].name` (la lista completa, alfabética, cinco visibles y el resto tras «Ver N más»). Se acepta nombrar una o varias, todas de la lista. Si `rare` está vacío, la respuesta correcta es «ninguna» (la pantalla dice «Ningún tema vecino cumple el criterio provisional todavía.»). |
| 5 | Marca y aviso | (a) Si `names_reviewed` es `false`: «¿Qué te dice la etiqueta “Nombres sin revisar”?» (b) En todos los casos: «¿Esta pantalla te dice qué es nuevo o qué se puede patentar?» | (a) Que los nombres de las tecnologías aún no los ha revisado una persona del sector (la interfaz nunca lista qué nombres concretos están sin revisar, así que la respuesta aceptada solo concierne al significado de la etiqueta; texto de la interfaz: «Los nombres de este tema aún no los ha revisado una persona del sector.»). Decir que los datos «no están validados» o «están mal» no es lo que significa la etiqueta: se anota como comprensión distinta de la etiqueta, no como dato incorrecto. (b) «No»: el diálogo «Cómo leer esto» lo dice («Nada de lo que ves aquí dice qué es nuevo ni qué se puede patentar.») y el texto «Son pistas para investigar, no oportunidades» solo se ve en la vista Pistas sin explorar cuando hay pistas; hay que abrir esa vista o el diálogo para encontrarlo. Si `names_reviewed` es `true`, solo se hace (b). |

Solo las respuestas 1 a 3 cuentan para el criterio de la fase; la 4 y la 5 son informativas.

## 5. Qué es un error

Decidido de antemano, por pregunta:

- **Error:** respuesta distinta de la aceptada; respuesta correcta a medias en la pregunta 1 (solo comparación o solo año); respuesta que contradice lo que la pantalla dice (por ejemplo afirmar que el tema «crece», palabra que la interfaz no usa, o que una pista es una oportunidad patentable).
- **Falta:** no contesta en 2 minutos, dice que no lo sabe, o solo contesta tras una ayuda de la persona moderadora (la ayuda se anota y la pregunta cuenta como falta).
- **No es error:** contestar con otras palabras, con el nombre acortado, o corregirse a sí misma antes de dar la respuesta final (se anota la duda).
- Una confusión sobre un dato que la pantalla muestra bien es un hallazgo sobre la pantalla, no sobre la persona; se anota igual.

## 6. Hoja de observación

Una por participante y tema. Rellenar en blanco antes de la sesión la columna «Respuesta aceptada».

Participante (código): ____ · Fecha: ____ · Tema: ____ · Datos: sintético / real (solo tras D4) · `names_reviewed`: ____

| # | Respuesta aceptada | Tiempo hasta responder (s) | Respuesta dada | Correcta / error / falta | Dudas (dónde dudó, qué botón probó antes) | Comentarios en voz alta |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5a | | | | | | |
| 5b | | | | | | |

Al final: ¿abrió «Cómo leer esto»? ____ · Preguntas hechas a la persona moderadora: ____ · Qué echó en falta: ____

## 7. Análisis

Por pregunta, cuántos de los participantes contestaron bien sin ayuda y en menos de 2 minutos, más las dudas y comentarios literales. No se calculan porcentajes ni se generaliza. Cada error o falta se registra como hallazgo sobre la pantalla con la vista afectada.
