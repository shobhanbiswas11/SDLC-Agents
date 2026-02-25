from app.agent.schemas.spec import Spec


def detect_missing(spec: Spec) -> list[str]:
    missing = []

    # -------- Core Required --------
    if not spec.language:
        missing.append("language")

    if not spec.framework and not spec.backend:
        missing.append("framework_or_backend")

    if not spec.core_features or len(spec.core_features) == 0:
        missing.append("core_features")

    # Architecture check (correct field name)
    if not spec.architecture or not spec.architecture.style:
        missing.append("architecture")

    # Scope check (optional but useful)
    if not spec.scope:
        missing.append("scope")

    # -------- Conditional Requirements --------

    features_text = " ".join(spec.core_features or []).lower()

    # If features imply auth
    if any(keyword in features_text for keyword in ["auth", "login", "register", "jwt", "oauth"]):
        if not spec.auth or not spec.auth.type:
            missing.append("auth")

    # If features imply database
    if any(keyword in features_text for keyword in ["save", "store", "database", "persist", "crud"]):
        if not spec.db or not spec.db.type:
            missing.append("database")

    return missing