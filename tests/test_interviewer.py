"""interviewer：维度覆盖跟踪（关键词归类）+ 动态难度状态机 + prompt 注入"""
import interviewer
from interviewer import InterviewSession
from job_profile import get_profile

PROFILE = get_profile("ai-dev")
RESUME = {
    "name": "测试",
    "education": "本科",
    "years": 3,
    "skills": ["Python"],
    "projects": ["做过客服系统"],
    "target_role": "AI 应用开发",
}


def _make_session(style="tech", difficulty=0):
    s = InterviewSession(RESUME, PROFILE, style=style)
    s.difficulty = difficulty
    return s


class TestCoverageTracking:
    def test_stream_first_message_归类覆盖维度(self, monkeypatch):
        def fake_stream(messages, **kwargs):
            # 注意：chat_stream 的契约是 yield 纯字符串增量（不是 (text, done) 元组）
            yield "你好，我是招聘官。"
            yield "期望薪资多少？"
            yield "什么时候到岗？"

        monkeypatch.setattr(interviewer, "chat_stream", fake_stream)
        s = _make_session()
        for _, done in interviewer.stream_first_message(s):
            if done:
                break
        assert "求职意向" in s.covered_dims

    def test_stream_next_message_技术问题归类技术能力(self, monkeypatch):
        def fake_stream(messages, **kwargs):
            yield "项目里 Redis 缓存怎么设计的？"

        monkeypatch.setattr(interviewer, "chat_stream", fake_stream)
        s = _make_session()
        for _, done in interviewer.stream_next_message(s, "我做过电商项目"):
            if done:
                break
        assert "技术能力" in s.covered_dims

    def test_未命中关键词不归类(self, monkeypatch):
        def fake_stream(messages, **kwargs):
            yield "好的。"

        monkeypatch.setattr(interviewer, "chat_stream", fake_stream)
        s = _make_session()
        for _, done in interviewer.stream_first_message(s):
            if done:
                break
        assert s.covered_dims == set()

    def test_build_messages_注入覆盖情况(self):
        s = _make_session()
        s.covered_dims.add("技术能力")
        messages = s._build_messages()
        content = messages[0]["content"]
        assert "已考察" in content
        assert "技术能力" in content
        assert "尚未考察" in content
        assert "项目经验" in content  # 未覆盖维度要出现在提示里


class TestDynamicDifficulty:
    def test_连续两次含糊降难度(self):
        s = _make_session(difficulty=2)
        s.update_difficulty("不知道")
        assert s.difficulty == 2  # 第一次不降
        s.update_difficulty("忘了")
        assert s.difficulty == 1  # 连续第二次降

    def test_连续两次技术信号升难度(self):
        s = _make_session(difficulty=0)
        s.update_difficulty("我们项目用了 Redis 缓存做热点数据，命中率做到了 85%，QPS 峰值 2000")
        assert s.difficulty == 0  # 第一次不升
        s.update_difficulty("我们给订单表建了 3 个联合索引，查询耗时从 200ms 降到了 20ms")
        assert s.difficulty == 1  # 连续第二次升

    def test_难度有上下界(self):
        s = _make_session(difficulty=2)
        for _ in range(4):
            s.update_difficulty("我们项目用了 Redis 缓存做热点数据，命中率做到了 85%，QPS 峰值 2000")
        assert s.difficulty == 2  # 封顶

    def test_中性回答重置连击(self):
        s = _make_session(difficulty=1)
        s.update_difficulty("不知道")
        # 中性回答：≥20 字符、无含糊词、无技术信号 → 重置 bad streak
        s.update_difficulty("我们团队有五个人，平时配合得还不错，没有特别大的矛盾")
        s.update_difficulty("不知道")
        assert s.difficulty == 1  # bad streak 被打断，不降
