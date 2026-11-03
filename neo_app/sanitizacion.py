import re


_PATRON_API_KEY = re.compile(
    r"([?&]api_key=)[^&#\s'\"<>]+",
    flags=re.IGNORECASE,
)


def sanitizar_api_keys(valor):
    if isinstance(valor, str):
        return _PATRON_API_KEY.sub(r"\1REDACTED", valor)
    if isinstance(valor, dict):
        return {
            clave: sanitizar_api_keys(contenido)
            for clave, contenido in valor.items()
        }
    if isinstance(valor, list):
        return [sanitizar_api_keys(elemento) for elemento in valor]
    return valor
