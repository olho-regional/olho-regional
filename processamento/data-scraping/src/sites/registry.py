import importlib
import logging
import pkgutil
from pathlib import Path

from .base import BaseSiteHandler

logger = logging.getLogger(__name__)

_registry: dict[str, BaseSiteHandler] = {}
_loaded = False


def _load_handlers():
    """Auto-discover all handler modules in the sites package."""
    global _loaded
    if _loaded:
        return

    package_dir = Path(__file__).parent
    for finder, name, ispkg in pkgutil.iter_modules([str(package_dir)]):
        if name in ("base", "registry", "__init__"):
            continue
        try:
            module = importlib.import_module(f".{name}", package="src.sites")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseSiteHandler)
                    and attr is not BaseSiteHandler
                    and hasattr(attr, "DOMAINS")
                    and attr.DOMAINS
                ):
                    handler = attr()
                    for domain in attr.DOMAINS:
                        _registry[domain.lower()] = handler
                        logger.debug(f"Registered handler {attr.NAME} for {domain}")
        except Exception as e:
            logger.warning(f"Failed to load site handler module {name}: {e}")

    _loaded = True


def get_handler(domain: str) -> BaseSiteHandler:
    """Get the handler for a domain, or the base handler as fallback."""
    _load_handlers()
    domain = domain.lower()
    if domain in _registry:
        return _registry[domain]
    # Try without subdomain
    parts = domain.split(".")
    if len(parts) > 2:
        short = ".".join(parts[-2:])
        if short in _registry:
            return _registry[short]
    return BaseSiteHandler()
