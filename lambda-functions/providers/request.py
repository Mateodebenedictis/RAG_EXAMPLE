import json
from typing import Dict, Any


def parse_api_gateway_request_body(req: Dict[str, Any]) -> Dict[str, Any]:
    body = req.get("body", "")
    return json.loads(str(body))
