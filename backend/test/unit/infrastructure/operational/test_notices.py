from infrastructure.operational.notices import NOTICES


class NoticesTest:
    def test_should_have_exactly_four_notices_when_the_screen_is_served(self):
        assert len(NOTICES) == 4

    def test_should_state_quality_as_internal_llm_estimate_when_serving_notices(self):
        assert NOTICES[3] == (
            "Calidad del ranking: estimación interna con juicio de un modelo de lenguaje, sin validación humana."
        )
        assert not any("preregistrado" in n or "en evaluación" in n for n in NOTICES)
