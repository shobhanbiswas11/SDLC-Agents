from .requirements_txt import RequirementsTxtParser
from .package_json import PackageJsonParser
from .pom_xml import PomXmlParser
from .cargo_toml import CargoTomlParser

_PARSERS = {
    "pypi": RequirementsTxtParser,
    "npm":  PackageJsonParser,
    "maven": PomXmlParser,
    "cargo": CargoTomlParser,
}

def get_parser(ecosystem: str):
    cls = _PARSERS.get(ecosystem)
    if not cls:
        raise ValueError(f"Unsupported ecosystem: {ecosystem}")
    return cls()
