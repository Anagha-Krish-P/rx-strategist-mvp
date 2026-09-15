import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rx_strategist.drug_lookup")

TIMEOUT_SECONDS = 8
RXNORM_RXCUI_URL = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
RXNORM_APPROX_URL = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"
RXNORM_RELATED_URL = "https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
USER_AGENT = "rx-strategist-mvp/1.0"

_CACHE: Dict[str, dict] = {}


def clear_lookup_cache() -> None:
    _CACHE.clear()


def lookup_drug(name: str) -> dict:
    normalized = (name or "").strip().lower()
    empty = _empty_result(name, error="Empty drug name." if not normalized else None)
    if not normalized:
        return empty
    cached = _CACHE.get(normalized)
    if cached is not None:
        return cached

    errors: List[str] = []
    rxcui = None
    ingredients: List[str] = []
    try:
        rxcui = _rxnorm_rxcui(name)
        if rxcui:
            ingredients = _rxnorm_ingredients(rxcui)
    except Exception as exc:
        logger.warning("RxNorm lookup failed for %s: %s", name, exc)
        errors.append(f"RxNorm: {exc}")

    fda: Dict[str, Any] = {}
    try:
        fda = _openfda_label(name, ingredients)
    except Exception as exc:
        logger.warning("openFDA lookup failed for %s: %s", name, exc)
        errors.append(f"openFDA: {exc}")

    ingredients = list(
        dict.fromkeys(
            ingredients + list(fda.get("ingredients") or [])
        )
    )
    indications_text = str(fda.get("indications_text") or "").strip()
    dosage_text = str(fda.get("dosage_text") or "").strip()
    sources = []
    if rxcui:
        sources.append("rxnorm")
    if fda.get("resolved"):
        sources.append("openfda")
    resolved = bool(rxcui or fda.get("resolved"))
    result = {
        "name": name,
        "resolved": resolved,
        "rxcui": rxcui,
        "ingredients": ingredients,
        "indications_text": indications_text,
        "dosage_text": dosage_text,
        "source": "/".join(sources) if sources else None,
        "error": "; ".join(errors) if errors and not resolved else (None if resolved else ("; ".join(errors) or "Drug not found in RxNorm or openFDA.")),
    }
    _CACHE[normalized] = result
    return result


def _empty_result(name: str, error: Optional[str] = None) -> dict:
    return {
        "name": name,
        "resolved": False,
        "rxcui": None,
        "ingredients": [],
        "indications_text": "",
        "dosage_text": "",
        "source": None,
        "error": error,
    }


def _fetch_json(url: str, timeout: float = TIMEOUT_SECONDS) -> dict:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"Timed out fetching {url}") from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected JSON payload from {url}")
    return data


def _rxnorm_rxcui(name: str) -> Optional[str]:
    exact_url = f"{RXNORM_RXCUI_URL}?name={urllib.parse.quote(name)}"
    data = _fetch_json(exact_url)
    ids = ((data.get("idGroup") or {}).get("rxnormId")) or []
    if ids:
        return str(ids[0])

    approx_url = f"{RXNORM_APPROX_URL}?term={urllib.parse.quote(name)}&maxEntries=1"
    approx = _fetch_json(approx_url)
    candidates = ((approx.get("approximateGroup") or {}).get("candidate")) or []
    if not candidates:
        return None
    rxcui = candidates[0].get("rxcui")
    return str(rxcui) if rxcui else None


def _rxnorm_ingredients(rxcui: str) -> List[str]:
    url = RXNORM_RELATED_URL.format(rxcui=urllib.parse.quote(str(rxcui))) + "?tty=IN"
    data = _fetch_json(url)
    names: List[str] = []
    for group in ((data.get("relatedGroup") or {}).get("conceptGroup")) or []:
        for concept in group.get("conceptProperties") or []:
            label = str(concept.get("name") or "").strip()
            if label:
                names.append(label)
    return list(dict.fromkeys(names))


def _openfda_label(name: str, ingredients: List[str]) -> dict:
    queries = [
        f'openfda.brand_name:"{name}"',
        f'openfda.generic_name:"{name}"',
        f'openfda.substance_name:"{name}"',
    ]
    for ingredient in ingredients[:3]:
        queries.append(f'openfda.substance_name:"{ingredient}"')
        queries.append(f'openfda.generic_name:"{ingredient}"')

    last_error = None
    for query in queries:
        encoded = urllib.parse.quote(query)
        url = f"{OPENFDA_LABEL_URL}?search={encoded}&limit=1"
        try:
            data = _fetch_json(url)
        except Exception as exc:
            last_error = exc
            continue
        results = data.get("results") or []
        if not results:
            continue
        record = results[0]
        openfda = record.get("openfda") or {}
        fda_ingredients = list(openfda.get("substance_name") or []) + list(
            _first_list(record.get("active_ingredient"))
        )
        return {
            "resolved": True,
            "ingredients": [item for item in fda_ingredients if str(item).strip()],
            "indications_text": _first_text(record.get("indications_and_usage")),
            "dosage_text": _first_text(record.get("dosage_and_administration")),
        }
    if last_error and not queries:
        raise last_error
    return {"resolved": False, "ingredients": [], "indications_text": "", "dosage_text": ""}


def _first_list(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _first_text(value) -> str:
    items = _first_list(value)
    if not items:
        return ""
    text = str(items[0]).strip()
    if len(text) > 1200:
        return text[:1200].rstrip() + "…"
    return text
