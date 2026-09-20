from pydantic import BaseModel, Field


class PolicyQuestionRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=3, ge=1, le=10)


class PolicySource(BaseModel):
    text: str
    source_document: str
    source_filename: str
    last_verified: str
    disclaimer: str
    relevance_score: float


class PolicyAnswerResponse(BaseModel):
    query: str
    answer_found: bool
    answer: str
    sources: list[PolicySource]
