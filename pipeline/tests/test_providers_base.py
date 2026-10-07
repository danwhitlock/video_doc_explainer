from pipeline.providers.base import LLMProvider


class DummyProvider:
    """A minimal class that satisfies LLMProvider purely by its shape -
    it doesn't inherit from LLMProvider at all.
    """

    name = "dummy"
    model = "dummy-model"

    def extract(self, text, schema):
        return {}

    def answer(self, question, passages):
        return {}


def test_dummy_provider_matches_protocol_structurally():
    assert isinstance(DummyProvider(), LLMProvider)


def test_object_missing_methods_does_not_match_protocol():
    class NotAProvider:
        name = "nope"
        model = "nope"

    assert not isinstance(NotAProvider(), LLMProvider)
