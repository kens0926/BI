import requests
from urllib.parse import parse_qsl, urlparse, urlunparse


class ApiError(Exception):
    pass


def build_params(parameter_rows, data_row):
    params = {}
    for row in parameter_rows:
        name = row.get("parameter_name", "")
        source = row.get("source_column", "")
        default = row.get("default_value", "")
        if not name:
            continue

        row_data = {k: "" if v is None else str(v) for k, v in data_row.items()}
        if default:
            try:
                formatted = default.format_map(row_data)
            except Exception:
                formatted = default
        else:
            formatted = ""

        has_placeholder = "{" in default and "}" in default
        if has_placeholder and formatted != "":
            params[name] = formatted
        elif source and source in row_data:
            params[name] = row_data[source]
        elif formatted != "":
            params[name] = formatted
        elif default is not None and default != "":
            params[name] = default
    return params


ERROR_PHRASES = [
    "系統發生錯誤",
    "請聯絡維運團隊",
    "發生錯誤時間",
    "ip：",
]


def call_api(api_url: str, method: str, params: dict, timeout: int = 30, verify: bool = True):
    method = method.upper()
    parsed_url = urlparse(api_url)
    existing_query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
    merged_params = {**existing_query, **params}
    url_without_query = urlunparse(parsed_url._replace(query=""))

    if method == "GET":
        response = requests.get(url_without_query, params=merged_params, timeout=timeout, verify=verify)
    else:
        response = requests.request(method, url_without_query, params=merged_params, timeout=timeout, verify=verify)

    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ApiError(str(exc)) from exc

    def _contains_error_text(text: str) -> bool:
        normalized = text.replace("\u3000", " ")
        return any(phrase in normalized for phrase in ERROR_PHRASES)

    try:
        result = response.json()
        if isinstance(result, dict):
            if any(key in result for key in ("error", "message", "Message", "status")):
                message = result.get("message") or result.get("Message") or str(result)
                if _contains_error_text(message):
                    raise ApiError(f"伺服器內部錯誤：{message}")
        return result
    except ValueError:
        text = response.text.strip()
        if not text:
            return []
        if _contains_error_text(text):
            raise ApiError(f"伺服器內部錯誤：{text}")
        return text
