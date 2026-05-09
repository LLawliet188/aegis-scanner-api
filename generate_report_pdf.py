from __future__ import annotations

import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "DEPLOYMENT_REPORT.md"
OUTPUT = ROOT / "DEPLOYMENT_REPORT.pdf"


def _plain_text(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            continue
        line = line.replace("#", "").replace("`", "").strip()
        lines.append(line)
    return lines


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_stream(lines: list[str]) -> str:
    y = 780
    parts = ["BT", "/F1 10 Tf", "14 TL"]
    for line in lines:
        safe = _escape_pdf_text(line)
        parts.append(f"72 {y} Td ({safe}) Tj")
        y -= 14
    parts.append("ET")
    return "\n".join(parts)


def _write_pdf(pages: list[list[str]]) -> None:
    objects: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    page_refs: list[str] = []
    for page in pages:
        stream = _page_stream(page)
        content_index = len(objects) + 1
        page_index = len(objects) + 2
        objects.append(f"<< /Length {len(stream.encode('latin-1', errors='replace'))} >>\nstream\n{stream}\nendstream")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_index} 0 R >>"
        )
        page_refs.append(f"{page_index} 0 R")

    objects[1] = f"<< /Type /Pages /Kids [{' '.join(page_refs)}] /Count {len(page_refs)} >>"

    data = ["%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(part.encode("latin-1", errors="replace")) for part in data))
        data.append(f"{index} 0 obj\n{obj}\nendobj\n")

    xref_offset = sum(len(part.encode("latin-1", errors="replace")) for part in data)
    data.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.append(f"{offset:010d} 00000 n \n")
    data.append(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n")

    OUTPUT.write_bytes("".join(data).encode("latin-1", errors="replace"))


def main() -> None:
    wrapped_lines: list[str] = []
    for line in _plain_text(SOURCE.read_text(encoding="utf-8")):
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(textwrap.wrap(line, width=88) or [""])

    pages = [wrapped_lines[index : index + 50] for index in range(0, len(wrapped_lines), 50)]
    _write_pdf(pages or [["Aegis Scanner Deployment Report"]])
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
