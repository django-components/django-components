from django_components.util.misc import is_str_wrapped_in_quotes

class TestUtils:
    def test_is_str_wrapped_in_quotes(self):
        assert is_str_wrapped_in_quotes("word") is False
        assert is_str_wrapped_in_quotes('word"') is False
        assert is_str_wrapped_in_quotes('"word') is False
        assert is_str_wrapped_in_quotes('"word"') is True
        assert is_str_wrapped_in_quotes("\"word'") is False
        assert is_str_wrapped_in_quotes('"word" ') is False
        assert is_str_wrapped_in_quotes('"') is False
        assert is_str_wrapped_in_quotes("") is False
        assert is_str_wrapped_in_quotes('""') is True
        assert is_str_wrapped_in_quotes("\"'") is False
