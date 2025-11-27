from pydantic import BaseModel


class CaseExample(BaseModel):
    title: str
    industry: str
    result: str
    actions: list[str]


class CaseExampleResponse(BaseModel):
    cases: list[CaseExample]
