#!/usr/bin/env python3
"""
export_xlsx.py - convert the ranked submission CSV into a formatted .xlsx
=========================================================================

The OFFICIAL submission to the portal must be the CSV (the spec lists .xlsx as
an auto-reject). This script just produces a nicely formatted Excel copy of the
same ranking for sharing / human review.

It writes a valid .xlsx using only the Python standard library (an .xlsx is an
Open-Packaging-Conventions zip of XML parts) - no openpyxl / pandas required,
so it runs offline like the rest of the project.

    python export_xlsx.py --in ./data/output/submission.csv --out ./data/output/submission.xlsx
"""

from __future__ import annotations

import argparse
import csv
import os
import zipfile


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def _col(idx: int) -> str:
    """0-based column index -> Excel column letter (A, B, ... Z, AA, ...)."""
    s = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        s = chr(65 + rem) + s
    return s


CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Ranked Candidates" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# styles: xf 0 default | xf 1 bold header | xf 2 number 0.0000
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="1"><numFmt numFmtId="164" formatCode="0.0000"/></numFmts>
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
  </fonts>
  <fills count="3">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF0B6BCB"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1">
      <alignment horizontal="center"/></xf>
    <xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
  </cellXfs>
</styleSheet>"""


def _cell(ref: str, value, kind: str, style: int) -> str:
    s = f' s="{style}"' if style else ""
    if kind == "n":
        return f'<c r="{ref}"{s}><v>{value}</v></c>'
    return (f'<c r="{ref}"{s} t="inlineStr">'
            f'<is><t xml:space="preserve">{_esc(str(value))}</t></is></c>')


def build_sheet(header, rows) -> str:
    # column schema: candidate_id(str), rank(int), score(num 0.0000), reasoning(str)
    kinds = ["s", "n", "n", "s"]
    styles_data = [0, 0, 2, 0]

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')
    out.append('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">')
    last = f"{_col(len(header)-1)}{len(rows)+1}"
    out.append(f'<dimension ref="A1:{last}"/>')
    out.append('<sheetViews><sheetView workbookViewId="0">'
               '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
               '</sheetView></sheetViews>')
    out.append('<sheetFormatPr defaultRowHeight="15"/>')
    out.append('<cols>'
               '<col min="1" max="1" width="16" customWidth="1"/>'
               '<col min="2" max="2" width="7"  customWidth="1"/>'
               '<col min="3" max="3" width="10" customWidth="1"/>'
               '<col min="4" max="4" width="120" customWidth="1"/>'
               '</cols>')
    out.append("<sheetData>")

    # header row
    out.append('<row r="1">')
    for c, name in enumerate(header):
        out.append(_cell(f"{_col(c)}1", name, "s", 1))
    out.append("</row>")

    # data rows
    for i, row in enumerate(rows, start=2):
        out.append(f'<row r="{i}">')
        for c, raw in enumerate(row):
            ref = f"{_col(c)}{i}"
            if kinds[c] == "n":
                out.append(_cell(ref, raw, "n", styles_data[c]))
            else:
                out.append(_cell(ref, raw, "s", styles_data[c]))
        out.append("</row>")

    out.append("</sheetData>")
    out.append(f'<autoFilter ref="A1:{_col(len(header)-1)}{len(rows)+1}"/>')
    out.append("</worksheet>")
    return "".join(out)


def csv_to_xlsx(csv_path: str, xlsx_path: str) -> int:
    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader = list(csv.reader(fh))
    header, data = reader[0], reader[1:]

    # coerce rank->int, score->float so Excel treats them as numbers
    norm = []
    for r in data:
        cid, rank, score, reasoning = r[0], r[1], r[2], r[3]
        norm.append([cid, int(rank), float(score), reasoning])

    sheet = build_sheet(header, norm)
    os.makedirs(os.path.dirname(os.path.abspath(xlsx_path)), exist_ok=True)
    with zipfile.ZipFile(xlsx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("xl/workbook.xml", WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        z.writestr("xl/styles.xml", STYLES)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return len(norm)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Convert ranked submission CSV to XLSX.")
    p.add_argument("--in", dest="inp", default=os.path.join("data", "output", "submission.csv"))
    p.add_argument("--out", dest="out", default=os.path.join("data", "output", "submission.xlsx"))
    args = p.parse_args(argv)

    if not os.path.exists(args.inp):
        print(f"ERROR: input CSV not found: {args.inp}")
        return 2
    n = csv_to_xlsx(args.inp, args.out)
    print(f"Wrote {n} ranked candidates -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
