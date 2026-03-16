from app.agent.schemas.spec import Spec
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


# ---------------------------
# Rule-Based Inference
# ---------------------------

def apply_rule_based_inference(spec: Spec) -> Spec:
    # Framework → Language mapping
    framework_language_map = {
        "fastapi": "python",
        "django": "python",
        "flask": "python",
        "express": "javascript",
        "nestjs": "typescript",
        "spring": "java",
    }

    if spec.framework and not spec.language:
        inferred = framework_language_map.get(spec.framework.lower())
        if inferred:
            spec.language = inferred

    # Backend → framework inference
    if spec.backend and not spec.framework:
        if spec.backend.lower() == "fastapi":
            spec.framework = "fastapi"
            spec.language = "python"

    return spec


# ---------------------------
# LLM-based enrichment (optional)
# ---------------------------

def llm_enrich_spec(spec: Spec) -> Spec:
    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=Spec)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are a spec completion engine.

Fill obvious missing fields based on existing spec values.
Do NOT invent complex features.
Only infer obvious technical relationships.

IMPORTANT:
- If "core_features" is empty but the spec has API endpoints,
  infer the feature names from the endpoint paths and descriptions.
- If "architecture.style" is missing, infer from the framework
  (e.g. FastAPI → microservices or modular).
- If "package_manager" is missing, infer from the language
  (e.g. python → pip, javascript → npm).

Return ONLY valid JSON.
{format_instructions}
""",
            ),
            ("human", "{spec_json}"),
        ]
        
        # , partial_variables={
        #     "format_instructions": parser.get_format_instructions()
        # },
    ).partial(
    format_instructions=parser.get_format_instructions()
)

    chain = prompt | llm | parser

    result = chain.invoke({"spec_json": spec.model_dump_json()})

    if isinstance(result, dict):
        return Spec(**result)

    return result