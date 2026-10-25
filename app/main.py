
from datetime import datetime
from json import JSONDecodeError

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from app.exercises import build_messages, call_model, parse_model_output
from openai import APITimeoutError

app = FastAPI(title="企业办公 AI 助手 · Day 1")


@app.exception_handler(NotImplementedError)
async def exercise_pending(request,error):
    return JSONResponse({'detail':'当前学员函数尚未实现；请先在IDE完成本课练习。'},status_code=501)


class LeaveParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    referenceTime: datetime


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/leave/parse")
def parse_leave(request: LeaveParseRequest) -> dict:
    messages = build_messages(request.text, request.referenceTime.isoformat())
    try:
        content = call_model(messages)
    except APITimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "MODEL_TIMEOUT",
                "message": "模型服务响应超时，请稍后重试"
            }
        ) from exc

    try:
        return parse_model_output(content)
    except JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "MODEL_JSON_INVALID",
                "message": "模型输出不是合法 JSON"
            }
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "MODEL_SCHEMA_INVALID",
                "message": "输出不符合 Schema"
            }
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "MODEL_RULE_INVALID",
                "message": "输出违反日期关系规则"
            }
        ) from exc


