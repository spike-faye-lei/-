"""llm_utils：JSON 容错解析 + 分数钳制"""
import pytest

from llm_utils import parse_llm_json, to_score


class TestParseLlmJson:
    def test_裸_json(self):
        assert parse_llm_json('{"a": 1}') == {"a": 1}

    def test_代码块包裹(self):
        content = '```json\n{"a": 1}\n```'
        assert parse_llm_json(content) == {"a": 1}

    def test_夹带文字截取花括号(self):
        content = '好的，输出如下：\n{"a": 1}\n希望有帮助'
        assert parse_llm_json(content) == {"a": 1}

    def test_空字符串抛异常(self):
        with pytest.raises(ValueError):
            parse_llm_json("")


class TestToScore:
    def test_正常值(self):
        assert to_score(7.5) == 7.5

    def test_字符串数字(self):
        assert to_score("8") == 8.0

    def test_非法值按0(self):
        assert to_score("abc") == 0.0
        assert to_score(None) == 0.0

    def test_超界钳制(self):
        assert to_score(15) == 10.0
        assert to_score(-3) == 0.0
