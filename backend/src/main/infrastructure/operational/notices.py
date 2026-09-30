"""Fixed on-screen notices (spec section 7). Served by the backend so the UI never hard-codes them.

NOTICE_QUALITY is deliberately a single constant. It changes only when docs/operational-dense-probe-result.md
exists, and then it states the outcome as written there.
"""

NOTICE_RANKING = "Ordenado por similitud de recuperación. No garantiza que el activo resuelva la demanda."
NOTICE_DATA = "Datos: Google Patents Public Data. Licencia en verificación; uso interno."
NOTICE_COVERAGE = (
    "Cobertura: patentes y modelos de utilidad ES de solicitantes españoles. "
    "Las solicitudes EP con solicitante español aún no se incluyen."
)
NOTICE_QUALITY = "Calidad del ranking en evaluación (probe preregistrado)."

NOTICES = (NOTICE_RANKING, NOTICE_DATA, NOTICE_COVERAGE, NOTICE_QUALITY)
