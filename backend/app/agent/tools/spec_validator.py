from app.agent.schemas.spec import Spec


def detect_missing(spec: Spec) -> list[str]:
    missing = []

    # -------- Core Required --------
    if not spec.language:
        missing.append("language")

    if not spec.framework and not spec.backend:
        missing.append("framework")

    if not spec.core_features:
        missing.append("core_features")

    # Architecture (leaf field)
    if not spec.architecture.style:
        missing.append("architecture.style")

    # -------- Conditional Requirements --------
    features_text = " ".join(spec.core_features or []).lower()

    # Auth required
    if any(keyword in features_text for keyword in ["auth", "login", "register", "jwt", "oauth"]):
        if not spec.auth.type:
            missing.append("auth.type")

    # Database required
    if any(keyword in features_text for keyword in ["save", "store", "database", "persist", "crud"]):
        if not spec.db.type:
            missing.append("db.type")

    return missing