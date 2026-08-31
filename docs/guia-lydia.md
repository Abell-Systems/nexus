# Guía del proyecto para Lydia (en español)

*Última actualización: 24 de agosto de 2026*

## ¿Qué es esto?

Un agente de inteligencia artificial que busca **espacios en blanco** (*white space*) en el panorama de patentes: zonas tecnológicas donde todavía existe oportunidad de inventar porque las patentes existentes no lo cubren.

La analogía es simple: en lugar de que un analista revise miles de patentes una por una para detectar dónde está saturado el mercado tecnológico y qué huecos quedan libres, este sistema lo hace automáticamente y —esto es lo importante— **siempre cita las patentes concretas que respaldan cada conclusión**.

## ¿Cómo funciona? (los cuatro pasos)

El sistema es una cadena de cuatro agentes especializados, como un equipo de un despacho de patentes:

1. **Investigador** (*research agent*) — busca y recopila las patentes relevantes de un dominio tecnológico. El dominio de demostración es *electrolitos de estado sólido para baterías de vehículos eléctricos*.
2. **Clasificador** (paso automático, sin IA generativa) — agrupa esas patentes por familia técnica y calcula cuáles zonas están saturadas y cuáles son espacios en blanco prometedores.
3. **Inventor** (*invention agent*) — propone invenciones candidatas dentro de los espacios en blanco.
4. **Abogado del diablo** (*adversarial agent*) — ataca cada propuesta buscando arte previo (*prior art*) que la invalidara. Solo sobreviven las propuestas que resisten.
5. **Gobernador** (*governor agent*) — puntúa a los supervivientes en cuatro dimensiones: novedad, riesgo de arte previo, diferenciación y evidencia. Cada puntuación debe citar números de patente específicos.

## Lo que distingue a este sistema (el ángulo para tu artículo)

En un mundo donde la IA "alucina", este proyecto se construye sobre la **trazabilidad**: ninguna afirmación se acepta sin su evidencia citada.

- El veredicto del adversario debe listar las patentes exactas que usó para rechazar una idea (`cited_patents`).
- La puntuación del gobernador debe incluir la lista `supporting_evidence` con números de publicación verificables.

Esto refleja exactamente cómo trabaja un examinador de patentes profesional: una conclusión sin referencia al documento que la sustenta no vale nada. Es la diferencia entre "la IA dice que esta idea es nueva" y "esta idea es nueva según estas cinco patentes publicadas, que puedes consultar".

## Estado actual

**Funcionando y probado en vivo (24 de agosto):**
- Los cuatro agentes trabajan en cadena contra el modelo Gemini de Google.
- Una ejecución real produjo un candidato puntuado así: *"In-Situ Formed Halide-Borate Composite SEI via Vapor-Phase Halogenation"* — novedad 0.92, riesgo de arte previo 0.85, diferenciación 0.88, evidencia 0.95, citando las patentes `US-10448361-B2`, `US-10437821-B2` y `US-11226419-B2`.
- La interfaz web muestra el mapa de oportunidades: grupos de patentes con sus espacios en blanco, y al hacer clic en un grupo, las invenciones propuestas con sus puntuaciones y citas.

**Listo (31 de agosto):**
- Desplegado en Google Cloud Run con datos reales de BigQuery.
- Vídeo técnico grabado, silencioso y con subtítulos en pantalla: `docs/demo/patent-innovation-agent-demo.mp4` (2:07, foco 100% en el producto).
- Vídeo "pitch" con la narrativa Mens et Manus (MIT → el problema → la idea → demo real → por qué importa → visión): `docs/demo/abell-systems-pitch.mp4` (3:42, silencioso, con texto en pantalla).
- Guion de narración para el vídeo técnico: `docs/demo/narration_script.md`.
- **Deck de presentación para la demo en directo:** `docs/demo/abell-systems-pitch.pptx` (11 diapositivas, misma narrativa Mens et Manus). La diapositiva 6 ("LIVE DEMO") es la chuleta para el presentador: trae escrito literalmente el dominio y la query a teclear, y el orden de clics (Analyze opportunity → View evidence → How the agent reached this result). Ábrelo en PowerPoint o Google Slides y sigue esa diapositiva mientras uno de los dos maneja la app en directo.

**Pendiente:**
- Subir el vídeo elegido a YouTube/Vimeo como *unlisted* y enlazarlo en `docs/devpost-draft.md`.
- Decidir cuál de los dos vídeos (técnico o pitch) va al formulario de Devpost — pueden convivir, pero solo uno es "el" vídeo de la submission.

## ¿Qué puedes hacer tú ahora mismo?

Con Python instalado, todo corre en tu máquina sin claves ni costes (usa datos simulados):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8080

# en otra terminal:
cd frontend
npm install && npm run dev
```

Abre `http://localhost:5173`, busca "solid electrolyte interphase" en dominio "solid-state battery electrolytes", expande un grupo y explora las patentes representativas.

*(Las funciones de inventar/puntuar sí necesitan una clave gratuita de Gemini API en `backend/.env` — pídela al equipo, y ojo: el nivel gratuito limita a 20 peticiones al día por modelo.)*

## Ideas para tu artículo

1. **Trazabilidad como requisito, no como extra**: el sistema rechaza arquitectónicamente cualquier salida sin citas — un paralelo directo con la obligación de divulgar arte previo en una solicitud de patente.
2. **El adversario como búsqueda de oposición automatizada**: el agente que intenta "matar" cada invención imita el examen de novedad, no el marketing.
3. **Espacios en blanco medibles**: la fórmula de puntuación (densidad del grupo + antigüedad + velocidad de citación) traduce intuiciones de análisis de paisaje tecnológico a algo reproducible.
4. **Economía del hallazgo**: el presupuesto de cuota gratuita (20 llamadas/día) obligó a diseñar la ejecución más frugal válida — un caso de estudio de optimización bajo restricción.
