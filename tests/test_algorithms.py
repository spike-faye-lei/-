"""algorithms：规则引擎 / TF-IDF 余弦 / 字段提取 / 加权评分（全部确定性，不调 LLM）"""
from algorithms import (
    EDU_LEVELS,
    bonus_layer_score,
    check_rules,
    composite_score,
    extract_fields,
    match_layer_score,
    rule_layer_score,
    tfidf_similarity,
    weighted_total,
)


class TestExtractFields:
    def test_完整简历提取(self):
        f = extract_fields("张伟，男，29岁，硕士，华中科技大学。3年AI应用开发经验。技能：Python、LangChain、Redis。期望薪资25-35K。邮箱 a@b.com")
        assert f["name"] == "张伟"
        assert f["education"] == "硕士"
        assert f["years"] == 3
        assert f["expected_salary"] == (25.0, 35.0)
        assert "python" in f["skills"] and "langchain" in f["skills"]
        assert f["email"] == "a@b.com"

    def test_空文本不崩(self):
        f = extract_fields("")
        assert f == {"name": "", "education": "", "years": 0, "skills": [], "expected_salary": None, "email": ""}

    def test_年限不误匹配年份(self):
        f = extract_fields("2026年毕业，应届")
        assert f["years"] == 0


class TestCheckRules:
    FIELDS = {"education": "本科", "years": 3, "skills": ["python", "langchain", "redis"], "expected_salary": (25.0, 35.0)}

    def test_全部通过(self):
        rules = {"min_education": "本科", "min_years": 1, "must_skills": ["python"], "max_salary": 40}
        passed, reasons = check_rules(self.FIELDS, rules)
        assert passed and reasons == []

    def test_学历不达标(self):
        rules = {"min_education": "硕士"}
        passed, reasons = check_rules(self.FIELDS, rules)
        assert not passed and any("学历" in r for r in reasons)

    def test_年限不足(self):
        rules = {"min_years": 5}
        passed, reasons = check_rules(self.FIELDS, rules)
        assert not passed and any("年限" in r for r in reasons)

    def test_年限超上限资历过高(self):
        rules = {"max_years": 2}
        passed, reasons = check_rules(self.FIELDS, rules)
        assert not passed and any("资历过高" in r for r in reasons)

    def test_缺必备技能(self):
        rules = {"must_skills": ["java"]}
        passed, reasons = check_rules(self.FIELDS, rules)
        assert not passed and any("java" in r for r in reasons)

    def test_薪资超预算(self):
        rules = {"max_salary": 20}
        passed, reasons = check_rules(self.FIELDS, rules)
        assert not passed and any("薪资" in r for r in reasons)

    def test_排除关键词(self):
        rules = {"exclude_keywords": ["外包"]}
        passed, reasons = check_rules({**self.FIELDS, "skills": ["python", "外包经历"]}, rules)
        assert not passed and any("外包" in r for r in reasons)

    def test_空规则全过(self):
        passed, reasons = check_rules(self.FIELDS, {})
        assert passed and reasons == []


class TestTfidf:
    JD = "招聘AI应用开发工程师：要求Python、LangChain、RAG、向量数据库、大模型应用开发经验"

    def test_相关简历分高于无关简历(self):
        sims = tfidf_similarity(self.JD, [
            "张伟 3年AI开发 Python LangChain RAG Milvus 大模型",
            "李婷 3年前端 Vue React 小程序 无AI经验",
        ])
        assert sims[0] > sims[1]

    def test_无关简历接近0(self):
        sims = tfidf_similarity(self.JD, ["纯行政工作，无技术经验"])
        assert sims[0] < 0.1

    def test_相同文本为1(self):
        sims = tfidf_similarity(self.JD, [self.JD])
        assert abs(sims[0] - 1.0) < 0.01

    def test_空输入不崩(self):
        assert tfidf_similarity("", ["", ""]) == [0.0, 0.0]

    def test_返回长度与输入一致(self):
        sims = tfidf_similarity(self.JD, ["a", "b", "c"])
        assert len(sims) == 3


class TestWeightedTotal:
    def test_加权正确(self):
        wm = {"技术能力": 40, "项目经验": 30, "沟通表达": 20, "求职意向": 10}
        assert weighted_total({"技术能力": 8, "项目经验": 6, "沟通表达": 7, "求职意向": 9}, wm) == 7.3

    def test_缺失维度按0拉低(self):
        wm = {"技术能力": 40, "项目经验": 30, "沟通表达": 20, "求职意向": 10}
        assert weighted_total({"技术能力": 8, "项目经验": 6, "沟通表达": 7}, wm) == 6.4

    def test_空权重不除零(self):
        assert weighted_total({}, {}) == 0.0


class TestEduLevels:
    def test_等级顺序(self):
        assert EDU_LEVELS["博士"] > EDU_LEVELS["硕士"] > EDU_LEVELS["本科"] > EDU_LEVELS["大专"]


class TestBiasGuard:
    """偏见守护：打分与性别/年龄/姓名无关（就业歧视合规的确定性证明）

    三层打分（规则/匹配/加分）均不读取性别、年龄字段；
    匹配层词表只含技能词，性别词"男/女"与数字年龄不参与向量计算。
    """

    RULES = {"min_education": "本科", "min_years": 1, "must_skills": ["python", "大模型"], "max_salary": 40}
    JD = "招聘AI应用开发工程师：要求Python、LangChain、RAG、向量数据库、大模型API"

    def _score(self, resume_text):
        f = extract_fields(resume_text)
        r = rule_layer_score(f, self.RULES)
        m = match_layer_score(self.JD, [resume_text])[0]
        b = bonus_layer_score(f, resume_text)
        return composite_score(r, m, b)["total"]

    def test_性别不影响打分(self):
        male = self._score("张伟，男，28岁，硕士，3年Python大模型RAG开发经验，期望20-30K")
        female = self._score("张薇，女，28岁，硕士，3年Python大模型RAG开发经验，期望20-30K")
        assert male == female

    def test_年龄不影响打分(self):
        young = self._score("张伟，男，24岁，硕士，3年Python大模型RAG开发经验，期望20-30K")
        old = self._score("张伟，男，38岁，硕士，3年Python大模型RAG开发经验，期望20-30K")
        assert young == old

    def test_姓名不影响打分(self):
        a = self._score("张伟，男，28岁，硕士，3年Python大模型RAG开发经验，期望20-30K")
        b = self._score("李国强，男，28岁，硕士，3年Python大模型RAG开发经验，期望20-30K")
        assert a == b


class TestHybridRetrieval:
    """模块二：BM25 + TF-IDF 混合检索 + RRF 融合（dense 适配位）"""

    JD = "招聘AI工程师：要求Python、LangChain、RAG、向量数据库"

    def test_bm25区分相关与无关(self):
        from algorithms import bm25_scores
        scores = bm25_scores(self.JD, ["张伟 Python LangChain RAG", "李婷 Vue 前端", "王五 Python 后端"])
        assert scores[0] > scores[2] > scores[1]

    def test_混合检索排序合理(self):
        from algorithms import match_layer_score
        scores = match_layer_score(self.JD, ["张伟 Python LangChain RAG Milvus", "李婷 Vue React 前端"])
        assert scores[0] > scores[1] and 0 <= scores[0] <= 100

    def test_dense三路融合(self):
        from algorithms import match_layer_score
        rs = ["张伟 Python LangChain RAG", "李婷 Vue 前端", "王五 Python 后端"]
        dense = [0.9, 0.1, 0.7]
        scores = match_layer_score(self.JD, rs, dense_scores=dense)
        assert scores[0] >= scores[2] > scores[1]
        assert all(0 <= s <= 100 for s in scores)

    def test_rrf确定性(self):
        from algorithms import reciprocal_rank_fusion
        a = reciprocal_rank_fusion([[3, 1, 2], [2, 3, 1]])
        b = reciprocal_rank_fusion([[3, 1, 2], [2, 3, 1]])
        assert a == b  # 同输入必同输出
