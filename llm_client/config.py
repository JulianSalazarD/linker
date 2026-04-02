import json
from pathlib import Path

def load_config(data_path: str = "data.json") -> dict:
    with open(data_path, encoding="utf-8") as f:
        return json.load(f)


def build_schema_str(fields: list[dict]) -> str:
    lines = ["  {"]
    for field in fields:
        nullable = field.get("nullable", True)
        type_str = field["type"] + (" | null" if nullable else "")
        default_str = f", default={json.dumps(field['default'])}" if "default" in field else ""
        desc = field.get("description", "")
        lines.append(f'      "{field["name"]}": {type_str}{default_str}  // {desc}')
    lines.append("  }")
    return "\n".join(lines)


def load_prompt(prompt_path: str, schema: str, file_path: str, text: str) -> str:
    template = Path(prompt_path).read_text(encoding="utf-8")
    return template.format(schema=schema, file_path=file_path, text=text)
