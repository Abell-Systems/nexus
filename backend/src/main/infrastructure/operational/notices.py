"""Fixed on-screen notices (spec section 7). Served by the backend so the UI never hard-codes them.

NOTICE_QUALITY is deliberately a single constant. It states what is true: the quality estimate is internal and
LLM-judged (spec Amendment A3 parked the human probe). It changes only if a human-validated result ever exists,
and then it states that outcome as written in the result document.
"""

NOTICE_RANKING = "Ordenado por similitud de recuperación. No garantiza que el activo resuelva la demanda."
NOTICE_DATA = (
    "Datos: «Google Patents Public Data», de IFI CLAIMS Patent Services y Google, "
    "con licencia Creative Commons Attribution 4.0 International."
)
NOTICE_COVERAGE = (
    "Cobertura: patentes y modelos de utilidad ES de solicitantes españoles. "
    "Las solicitudes EP con solicitante español aún no se incluyen."
)
NOTICE_QUALITY = "Calidad del ranking: estimación interna con juicio de un modelo de lenguaje, sin validación humana."

NOTICES = (NOTICE_RANKING, NOTICE_DATA, NOTICE_COVERAGE, NOTICE_QUALITY)
