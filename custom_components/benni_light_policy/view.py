"""Panel-Registrierung für das Light-Policy-Dashboard.

Liefert das modulare Vanilla-Web-Components-Frontend unter `frontend/app/` als
statisches Verzeichnis aus (ES-Module importieren sich gegenseitig) und registriert
ein Custom-Panel in der HA-Sidebar.
"""
from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import (
    async_register_built_in_panel,
    async_remove_panel,
)
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    FRONTEND_DIR_URL,
    FRONTEND_ENTRY,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_PATH,
)

_LOGGER = logging.getLogger(__name__)

_BASE = os.path.dirname(__file__)
_APP_DIR = os.path.join(_BASE, "frontend", "app")
# Flag, das den (prozessweit einmaligen) Static-Path-Mount überlebt — async_register_
# static_paths darf pro Pfad nur einmal laufen, auch über Entry-Reloads hinweg.
_STATIC_FLAG = "_view_static_registered"
_PANEL_FLAG = "_view_panel_registered"


def _cache_bust() -> str:
    # Manifest-Version ist statisch über Branch-Updates → mtime von main.js bustet
    # den Browser-Cache bei jedem HACS-Download.
    try:
        return str(int(os.path.getmtime(os.path.join(_APP_DIR, "main.js"))))
    except OSError:
        return "0"


async def async_setup_view(hass: HomeAssistant) -> None:
    data = hass.data.setdefault(DOMAIN, {})
    if not data.get(_STATIC_FLAG):
        await hass.http.async_register_static_paths([
            # cache_headers=False → ES-Module revalidieren (kein Stale zwischen Edits).
            StaticPathConfig(FRONTEND_DIR_URL, _APP_DIR, False),
        ])
        data[_STATIC_FLAG] = True

    # Panel pro Setup (wird beim Unload entfernt). Doppelregistrierung vermeiden.
    if data.get(_PANEL_FLAG):
        return
    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL_PATH,
        require_admin=False,
        config={
            "_panel_custom": {
                "name": PANEL_ELEMENT,
                "module_url": f"{FRONTEND_ENTRY}?{_cache_bust()}",
            },
        },
    )
    data[_PANEL_FLAG] = True


def async_remove_view(hass: HomeAssistant) -> None:
    data = hass.data.setdefault(DOMAIN, {})
    if not data.get(_PANEL_FLAG):
        return
    try:
        async_remove_panel(hass, PANEL_URL_PATH)
    except Exception as err:  # noqa: BLE001 - Panel evtl. nie registriert
        _LOGGER.debug("panel remove skipped: %s", err)
    data[_PANEL_FLAG] = False
