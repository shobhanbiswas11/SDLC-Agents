class GenerationError(Exception):
    """Raised when generated output is incomplete or invalid."""
    pass


def validate_generation(tree: list[str], files: dict[str, str]) -> None:
    """
    Validate that every file path in the tree has a corresponding entry
    in the generated files dict.

    Raises GenerationError if any files are missing.
    """
    missing = [path for path in tree if path not in files]

    if missing:
        raise GenerationError(
            f"Generation incomplete — {len(missing)} file(s) missing from "
            f"generated output: {missing}"
        )

    print(f"[Validator] All {len(tree)} files accounted for. ✓")
