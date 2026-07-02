from fastapi import APIRouter, HTTPException
from backend.michael_ai.schema import PromptIngestRequest, AgRunIngestRequest, SynthesizeRequest
from backend.michael_ai.ingestion import ingest_michael_prompt, ingest_ag_run
from backend.michael_ai.synthesizer import synthesize_current_state, seed_initial_truths
from backend.michael_ai.prompt_builder import build_next_prompt
from backend.michael_ai.training_corpus import export_training_corpus

router = APIRouter(prefix="/api/v1/michael-ai", tags=["Michael AI Model"])

@router.post("/ingest-prompt")
def post_ingest_prompt(payload: PromptIngestRequest):
    try:
        res = ingest_michael_prompt(payload.source, payload.raw_text)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest-ag-run")
def post_ingest_ag_run(payload: AgRunIngestRequest):
    try:
        res = ingest_ag_run(
            payload.agent_role, payload.task_description, payload.status,
            payload.result, payload.raw_prompt
        )
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/current-state")
def get_current_state():
    try:
        res = synthesize_current_state()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/next-prompt")
def get_next_prompt():
    try:
        res = build_next_prompt()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/training-corpus")
def get_training_corpus():
    try:
        res = export_training_corpus()
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/synthesize")
def post_synthesize(payload: SynthesizeRequest):
    try:
        if payload.force_refresh:
            seed_initial_truths()
        res = synthesize_current_state()
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
