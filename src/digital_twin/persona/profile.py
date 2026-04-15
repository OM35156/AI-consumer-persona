"""Consumer persona profile — based on 'Persona Strategy' book methodology.

A persona is not an abstract "user type" but a specific, named individual
with goals, factoids, personality quirks, and a face. The persona speaks
in first person and represents a real pattern found in the data.

Key concepts from the book:
- Identification: Name, age, catchphrase
- Goals: Short-term and long-term objectives
- Factoids: Data-backed behavioral facts
- Situation & Environment: Devices, schedule, physical setting
- Psychological Details: Values, fears, frustrations, quirks
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from digital_twin.data.schema import (
    BrandExposure,
    CategoryProfile,
    ChannelPreference,
    ConsumerDemographics,
    Factoid,
    PersonaGoal,
    PersonalityTrait,
    ResponseStyle,
)


class HistoricalResponse(BaseModel):
    """過去の調査回答（few-shot例）."""

    question_text: str
    question_category: str
    response_value: str | int | float | list[str] | None = None
    free_text: str | None = None


class ConsumerPersona(BaseModel):
    """Complete consumer persona — 'a specific someone'.

    This is the core data structure that feeds into the LLM prompt.
    The persona should feel like a real person that development teams
    can empathize with and use as a decision-making tool.
    """

    # --- Identification (識別情報) ---
    persona_id: str
    name: str  # 実在感のある日本語フルネーム
    age: int
    gender: str
    catchphrase: str = ""  # このペルソナを象徴する一言

    # --- Consumer Profile ---
    demographics: ConsumerDemographics
    category_profile: CategoryProfile
    channel_preferences: list[ChannelPreference] = []

    # --- Persona Strategy Components ---
    goals: list[PersonaGoal] = []
    factoids: list[Factoid] = []
    personality_traits: list[PersonalityTrait] = []

    # --- Response Style ---
    response_style: ResponseStyle = Field(default_factory=ResponseStyle)

    # --- Historical Data ---
    brand_history: list[BrandExposure] = []
    historical_responses: list[HistoricalResponse] = []

    # --- Generated Narrative ---
    persona_narrative: str = ""

    def to_system_prompt(
        self,
        segment_profile_text: str | None = None,
        rag_context: str | None = None,
    ) -> str:
        """ペルソナ用の完全な system prompt を生成する.

        'Persona Strategy' 書籍の方針に従い、AI はこの生活者そのものとして、
        一人称で、固有の癖と制約を保ちながら振る舞う。

        Args:
            segment_profile_text: 層①セグメントプロファイルのテキスト（オプション）
            rag_context: 層②RAG検索結果のコンテキスト（オプション）
        """
        sections = []

        # Role definition
        sections.append(self._build_role_section())

        # Knowledge context (persona document)
        sections.append(self._build_knowledge_section())

        # Layer ①: Segment profile (if provided)
        if segment_profile_text:
            sections.append(segment_profile_text)

        # Layer ②: RAG context (if provided)
        if rag_context:
            sections.append(rag_context)

        # Skills/capabilities
        sections.append(self._build_skills_section())

        # Constraints
        sections.append(self._build_constraints_section())

        return "\n\n".join(sections)

    def _build_role_section(self) -> str:
        return f"""# Role
あなたは{self.name}（{self.age}歳）です。{self.catchphrase}

あなたは抽象的な「生活者ユーザー」ではなく、実在する生活者データから構築された、
名前、個人的な目標、固有の癖を持つ「特定の誰か」として振る舞います。

製品開発チームやブランドとの対話において、提示された商品情報やプロモーションに対し、
自身の「ゴール」と「背景」に照らして、一人の生活者としての率直な反応を示してください。"""

    def _build_knowledge_section(self) -> str:
        demo = self.demographics
        cat = self.category_profile

        lines = [
            "# Knowledge Context（基本文書）",
            "",
            "## 識別情報",
            f"- 名前: {self.name}",
            f"- 年齢: {self.age}歳",
            f"- 性別: {_gender_ja(self.gender)}",
            f"- 年代層: {demo.age_group.value}",
            f"- 居住地: {_region_ja(demo.region.value)}",
            f"- ライフステージ: {_life_stage_ja(demo.life_stage.value)}",
            f"- 職業: {demo.occupation or '未設定'}",
            f"- 世帯年収: {demo.household_income or '未設定'}",
            f"- インフルエンサー傾向: {'はい' if demo.is_influencer else 'いいえ'}",
        ]

        # Goals
        if self.goals:
            lines.append("\n## ゴール (Goals)")
            for g in self.goals:
                priority_mark = "★" * (6 - g.priority)
                lines.append(f"- [{g.goal_type}] {g.description} {priority_mark}")

        # Factoids
        if self.factoids:
            lines.append("\n## ファクトイド (Factoids)")
            for f in self.factoids:
                source = f" ({f.data_source})" if f.data_source else ""
                lines.append(f"- [{f.category}] {f.content}{source}")

        # Category profile（購買行動）
        lines.append("\n## 購買行動")
        lines.append(f"- 関心カテゴリ: {cat.category}")
        if cat.primary_brands:
            lines.append(f"- 主要利用ブランド: {', '.join(cat.primary_brands)}")
        if cat.brand_status:
            for brand, status in cat.brand_status.items():
                lines.append(f"  - {brand}: {_brand_aware_ja(status.value)}")
        if cat.purchase_philosophy:
            lines.append(f"- 購買哲学: {cat.purchase_philosophy}")
        price_ja = {"high": "価格にシビア", "moderate": "標準的", "low": "品質重視"}
        lines.append(f"- 価格感度: {price_ja.get(cat.price_sensitivity, cat.price_sensitivity)}")
        receptivity_ja = {"early": "アーリーアダプター", "moderate": "標準的", "late": "慎重派"}
        lines.append(
            f"- 新商品受容: {receptivity_ja.get(cat.new_product_receptivity, cat.new_product_receptivity)}"
        )

        # Channel preferences
        if self.channel_preferences:
            lines.append("\n## 情報チャネル嗜好性")
            for cp in sorted(self.channel_preferences, key=lambda x: -x.receptivity):
                ch_name = _channel_ja(cp.channel.value)
                stars = "●" * cp.receptivity + "○" * (5 - cp.receptivity)
                lines.append(f"- {ch_name}: {stars} (月{cp.frequency_per_month}回)")

        # Personality
        if self.personality_traits:
            lines.append("\n## 心理的詳細・性格")
            for t in self.personality_traits:
                lines.append(f"- {t.trait_name}: {t.description}")

        # Response style
        style = self.response_style
        lines.append("\n## 回答スタイル")
        style_desc = {
            "extreme": "はっきりとした態度を示す",
            "moderate": "慎重な中間的回答が多い",
            "acquiescent": "概ね肯定的に応じる傾向",
            "balanced": "公平でバランスの取れた評価をする",
        }
        lines.append(f"- 尺度回答傾向: {style_desc.get(style.scale_usage.value, style.scale_usage.value)}")
        survey_desc = {
            "high": "アンケートに積極的",
            "moderate": "標準的",
            "low": "アンケートには淡白で短め",
        }
        lines.append(
            f"- 調査協力度: {survey_desc.get(style.survey_receptivity, style.survey_receptivity)}"
        )
        verbosity = {"low": "簡潔・端的", "medium": "適度な詳しさ", "high": "詳細で論理的"}
        lines.append(f"- 発言の詳しさ: {verbosity.get(style.free_text_verbosity, style.free_text_verbosity)}")

        return "\n".join(lines)

    def _build_skills_section(self) -> str:
        return """# Skills / Capabilities
あなたは以下の機能を提供します：

1. **ペルソナ視点でのフィードバック**: 「私はこの商品を買いたいか？」「このメッセージは響くか？」を自身のゴールに照らして回答
2. **シナリオのウォークスルー**: 広告接触や店頭での商品選択の場面を、自分の日常の中で一人称で描写
3. **購買意向の判定**: プロモーション提示後の購買意向を「必ず買いたい/たぶん買う/検討する/たぶん買わない/買わない」で判定
4. **機能評価**: 提示された施策が自分にとって「喜ぶ(+2)/役立つ(+1)/無関心(0)/困惑する(-1)」を判定
5. **競合分析**: 競合商品の情報を聞いた時の率直な反応を述べる"""

    def _build_constraints_section(self) -> str:
        return """# Constraints / Style

- **一人称での対話**: 常に「私は〜」で話す。「この生活者は〜」という三人称の分析は禁止
- **データへの忠実性**: 自分の意見はファクトイドの範囲内。データにない「想像上の便利さ」は肯定しない
- **万人受けの否定**: 「私には不要だが他の人には必要かもしれない」という妥協はしない。あくまで自分にとっての価値を主張
- **具体的な細部**: 「便利そう」でなく「土曜の朝、スーパーの帰りにスマホでSNSを見ていたら目に留まった」と語る
- **購買行動の一貫性**: 自分の購買哲学・価格感度・新商品受容度と矛盾しない判断をする"""

    def get_brand_history_summary(self, max_entries: int = 5) -> str:
        """直近のブランド接触履歴を整形する."""
        if not self.brand_history:
            return ""

        lines = ["## 最近のブランド接触履歴"]
        for exp in self.brand_history[-max_entries:]:
            ch = _channel_ja(exp.channel.value)
            intent_ja = _intent_ja(exp.purchase_intent_after.value)
            cat_str = f" ({exp.category})" if exp.category else ""
            lines.append(
                f"- [{exp.date}] {exp.brand_name}{cat_str} "
                f"via {ch} → 購買意向: {intent_ja}"
            )
            if exp.content_summary:
                lines.append(f"  内容: {exp.content_summary}")

        return "\n".join(lines)

    def get_few_shot_examples(self, max_examples: int = 5) -> str:
        """過去の回答を few-shot 例としてフォーマットする."""
        if not self.historical_responses:
            return ""

        examples = self.historical_responses[:max_examples]
        lines = ["## 過去の回答例"]
        for ex in examples:
            lines.append(f"\nQ: {ex.question_text}")
            if ex.response_value is not None:
                if isinstance(ex.response_value, list):
                    lines.append(f"A: {', '.join(str(v) for v in ex.response_value)}")
                else:
                    lines.append(f"A: {ex.response_value}")
            if ex.free_text:
                lines.append(f"A（コメント）: {ex.free_text}")

        return "\n".join(lines)

    def to_skill_md(self) -> str:
        """このペルソナの skill.md ファイル内容を生成する."""
        return f"""---
name: {self.name}
description: {self.catchphrase}
type: consumer_persona
---

{self.to_system_prompt()}

# Evaluation Criteria
- **会議の強力な発言者か？** 開発者が「{self.name}さんならどう言うだろう？」と想像できる個性があるか
- **設計に制約を与えるか？** 私の特性により「この施策はやめよう」と判断できる材料を提供できるか
- **実在感があるか？** チームが感情移入し、実在の生活者のように扱いたくなる像を描けるか
"""


# --- Helper functions（日本語名変換） ---


def _gender_ja(gender: str) -> str:
    return {"male": "男性", "female": "女性", "other": "その他"}.get(gender, gender)


def _region_ja(region: str) -> str:
    return {
        "hokkaido": "北海道",
        "tohoku": "東北",
        "kanto": "関東",
        "chubu": "中部",
        "kinki": "近畿",
        "chugoku": "中国",
        "shikoku": "四国",
        "kyushu": "九州",
    }.get(region, region)


def _life_stage_ja(life_stage: str) -> str:
    return {
        "student": "学生",
        "single_working": "独身・勤労",
        "married_no_children": "既婚・子なし",
        "married_with_children": "既婚・子育て中",
        "empty_nest": "子独立後",
        "retired": "退職後",
    }.get(life_stage, life_stage)


def _channel_ja(channel: str) -> str:
    return {
        "tv_cm": "TV CM",
        "web_ad": "Web広告",
        "sns": "SNS",
        "word_of_mouth": "口コミ",
        "store_display": "店頭ディスプレイ",
        "magazine": "雑誌",
        "influencer": "インフルエンサー",
        "search_engine": "検索エンジン",
        "ec_site": "ECサイト",
    }.get(channel, channel)


def _brand_aware_ja(status: str) -> str:
    return {
        "active_user": "現在利用中",
        "past_user": "過去に利用",
        "aware_not_used": "認知あり・未利用",
        "unaware": "非認知",
    }.get(status, status)


def _intent_ja(intent: str) -> str:
    return {
        "definitely_buy": "必ず買いたい",
        "probably_buy": "たぶん買う",
        "might_buy": "検討する",
        "probably_not": "たぶん買わない",
        "definitely_not": "買わない",
    }.get(intent, intent)
