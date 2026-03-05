from app.agent.schemas.spec import Spec


# Fields in the Spec that are typed as List[str]
LIST_FIELDS = {"core_features", "linters"}


def _coerce_value(field_name: str, value):
    """
    Convert user-supplied clarification answers to the correct type.
    Handles:
    - String → List[str] for list fields (split by commas or newlines)
    - Passthrough for everything else
    """
    leaf = field_name.split(".")[-1]

    if leaf in LIST_FIELDS and isinstance(value, str):
        # Split by comma, semicolon, or newline and strip whitespace
        items = [
            item.strip()
            for item in value.replace(";", ",").replace("\n", ",").split(",")
            if item.strip()
        ]
        return items

    return value


def merge_answers_into_spec(spec: Spec, answers: dict) -> Spec:
    spec_dict = spec.model_dump()

    for key, value in answers.items():
        # Coerce value to the expected type
        value = _coerce_value(key, value)

        # Support nested fields like "architecture.style"
        keys = key.split(".")
        target = spec_dict

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    return Spec(**spec_dict)