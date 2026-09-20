from fastapi import APIRouter

from app.models.policy import PolicyAnswerResponse, PolicyQuestionRequest
from app.services import policy_rag

router = APIRouter()


@router.post("/ask", response_model=PolicyAnswerResponse)
def ask(req: PolicyQuestionRequest):
    return policy_rag.answer_question(req.question, top_k=req.top_k)
