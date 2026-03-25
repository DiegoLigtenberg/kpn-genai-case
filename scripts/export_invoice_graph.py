import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.service.graph import build_invoice_graph


def main() -> None:
    out_dir = _ROOT / "graphs"
    out_dir.mkdir(exist_ok=True)

    app = build_invoice_graph(llm_type="openai")
    graph = app.get_graph()

    mmd = graph.draw_mermaid()
    mmd_path = out_dir / "invoice_graph.mmd"
    mmd_path.write_text(mmd, encoding="utf-8")
    print(f"Wrote {mmd_path}")

    png_path = out_dir / "invoice_graph.png"
    try:
        png_bytes = graph.draw_mermaid_png()
        png_path.write_bytes(png_bytes)
        print(f"Wrote {png_path}")
    except Exception as exc:  # noqa: BLE001
        print(
            f"PNG failed ({exc}). Use the .mmd file in mermaid.live.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
