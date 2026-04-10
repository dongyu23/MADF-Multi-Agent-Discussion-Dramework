from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# -------------------------------------------------------------------
# SubTask 1.1: Character Profile (角色基础档案)
# -------------------------------------------------------------------
class CharacterProfileBase(BaseModel):
    name: str = Field(..., description="角色名称")
    title: Optional[str] = Field(None, description="头衔或称呼")
    background: Optional[str] = Field(None, description="背景故事与核心人设")
    personality_traits: List[str] = Field(default_factory=list, description="性格特征标签")
    core_values: List[str] = Field(default_factory=list, description="核心价值观（宪法级硬约束）")
    speaking_style: Optional[str] = Field(None, description="说话风格（如口癖、语气）")

class CharacterProfileCreate(CharacterProfileBase):
    pass

class CharacterProfileResponse(CharacterProfileBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------------
# SubTask 1.2: Relation State (关系状态)
# -------------------------------------------------------------------
class RelationStateBase(BaseModel):
    source_character_id: int = Field(..., description="关系主体角色ID")
    target_character_id: int = Field(..., description="关系客体角色ID")
    relation_type: str = Field(..., description="关系类型（如朋友、敌人、上下级）")
    intimacy: float = Field(0.0, description="亲密度 (-1.0 到 1.0)")
    trust: float = Field(0.0, description="信任度 (-1.0 到 1.0)")
    conflict_history: List[str] = Field(default_factory=list, description="历史冲突记录概要")
    notes: Optional[str] = Field(None, description="关系备注（如关键转折事件）")

class RelationStateCreate(RelationStateBase):
    pass

class RelationStateResponse(RelationStateBase):
    id: int
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------------
# SubTask 1.3: Temporal Persona / Scene State (情景时间态)
# -------------------------------------------------------------------
class TemporalPersonaBase(BaseModel):
    character_id: int = Field(..., description="角色ID")
    current_emotion: str = Field("neutral", description="当前情绪状态（如愤怒、高兴、平静）")
    fatigue_level: float = Field(0.0, description="疲劳度 (0.0 到 1.0)，可能影响决策质量")
    current_goal: Optional[str] = Field(None, description="当前情景下的短期目标")
    current_stance: Optional[str] = Field(None, description="在当前讨论议题上的临时立场")
    attention_focus: Optional[str] = Field(None, description="当前注意力焦点（如某个事件、某个人物）")

class TemporalPersonaCreate(TemporalPersonaBase):
    pass

class TemporalPersonaResponse(TemporalPersonaBase):
    id: int
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# -------------------------------------------------------------------
# SubTask 1.4: Episodic Memory & Semantic State (情景记忆与语义状态)
# -------------------------------------------------------------------

# 语义状态 (Semantic State) - 长期抽象出来的信念与行为模式
class SemanticStateBase(BaseModel):
    character_id: int = Field(..., description="角色ID")
    beliefs: Dict[str, float] = Field(default_factory=dict, description="信念及其置信度 (0.0 到 1.0)，例如 {'世界是残酷的': 0.8}")
    behavior_patterns: List[str] = Field(default_factory=list, description="抽象出的行为模式，如 '遇到指责时习惯性反驳'")
    long_term_goals: List[str] = Field(default_factory=list, description="长期追求的目标")

class SemanticStateCreate(SemanticStateBase):
    pass

class SemanticStateResponse(SemanticStateBase):
    id: int
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# 情景记忆 (Episodic Memory) - 具体的事件记忆
class EpisodicMemoryBase(BaseModel):
    character_id: int = Field(..., description="角色ID")
    event_summary: str = Field(..., description="事件摘要")
    involved_characters: List[int] = Field(default_factory=list, description="事件中涉及的其他角色ID")
    emotional_impact: float = Field(0.0, description="情绪影响程度 (-1.0 到 1.0)")
    importance_score: float = Field(0.5, description="记忆重要性评分 (0.0 到 1.0)，决定遗忘曲线")
    context_tags: List[str] = Field(default_factory=list, description="情景标签，用于按需检索")

class EpisodicMemoryCreate(EpisodicMemoryBase):
    pass

class EpisodicMemoryResponse(EpisodicMemoryBase):
    id: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)
