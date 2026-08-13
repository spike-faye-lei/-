"""job_profile：维度关键词归类 + 岗位配置获取"""
from job_profile import PROFILES, classify_dimension, get_profile


class TestClassifyDimension:
    def test_技术问题归类技术能力(self):
        p = get_profile("ai-dev")
        assert classify_dimension("项目里 Redis 缓存是怎么设计的，命中率多少？", p) == "技术能力"

    def test_薪资问题归类求职意向(self):
        p = get_profile("ai-dev")
        assert classify_dimension("期望薪资多少？什么时候能到岗？", p) == "求职意向"

    def test_项目问题归类项目经验(self):
        p = get_profile("ai-dev")
        assert classify_dimension("你负责的客服系统上线后效果怎么样？", p) == "项目经验"

    def test_后端岗位系统设计维度(self):
        p = get_profile("backend")
        assert classify_dimension("这个支付系统如果要做分库分表，你会怎么设计？", p) == "系统设计"

    def test_未命中返回None(self):
        p = get_profile("ai-dev")
        assert classify_dimension("好的。", p) is None

    def test_大小写不敏感(self):
        p = get_profile("ai-dev")
        assert classify_dimension("REDIS 用了什么数据结构？", p) == "技术能力"


class TestGetProfile:
    def test_按id取(self):
        assert get_profile("backend")["job"] == "后端开发工程师"

    def test_未知id回退第一个(self):
        assert get_profile("不存在")["id"] == PROFILES[0]["id"]

    def test_每个岗位维度都有关键词(self):
        for p in PROFILES:
            for d in p["dimensions"]:
                assert d.get("keywords"), f"{p['id']} 的 {d['name']} 缺 keywords"
