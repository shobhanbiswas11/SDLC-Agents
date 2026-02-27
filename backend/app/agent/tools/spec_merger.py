from app.agent.schemas.spec import Spec


def merge_answers_into_spec(spec: Spec, answers: dict) -> Spec:
    spec_dict = spec.model_dump()

    for key, value in answers.items():
        # Support nested fields like "architecture.style"
        keys = key.split(".")
        target = spec_dict

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

    return Spec(**spec_dict)