"""Render the SupportInboxFlow diagram to artifacts/flow_diagram.html.

``Flow.plot`` returns the absolute path of an HTML file in a freshly
created ``tempfile.mkdtemp`` directory, along with sibling CSS/JS assets.
We copy the whole triple into ``artifacts/`` so the chapter figure lives
in a stable location the reader can open from their file manager.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from gmail_support_flow.flow import SupportInboxFlow


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    out_dir = PROJECT_ROOT / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_html = Path(SupportInboxFlow().plot("flow_diagram.html", show=False))
    for src in tmp_html.parent.iterdir():
        shutil.copy2(src, out_dir / src.name)
    print(f"[plot] wrote {out_dir / 'flow_diagram.html'}")


if __name__ == "__main__":
    main()
