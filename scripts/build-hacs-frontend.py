#!/usr/bin/env python3
"""Deterministically combine the original Doorstation frontend into the HACS bundle."""
from pathlib import Path
r = Path(__file__).resolve().parent.parent
src = [r / "frontend/smartify-doorstation-card.js", r / "frontend/smartify-doorstation-popup.js"]
dst = r / "dist/smartify-sip-manager.js"
dst.parent.mkdir(exist_ok=True)
header = "/* Smartify SIP Manager v1.19.12 -- HACS frontend bundle: Doorstation Card v2.7.7 and Popup v3.3.9. */\n"
# Separate the scripts; both register their own custom elements.
dst.write_text(header + "\n;\n".join(p.read_text(encoding="utf-8") for p in src) + "\n", encoding="utf-8")
# Keep the app-bundled assets in sync with the HACS source on every build.
bundled = r / "smartify_sip_manager/frontend"
bundled.mkdir(parents=True, exist_ok=True)
for source in src + [dst]:
    (bundled / source.name).write_bytes(source.read_bytes())
print(f"Written {dst.relative_to(r)} ({dst.stat().st_size} bytes) and app frontend copies")
