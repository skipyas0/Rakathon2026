"""Simple flowing-text PDF writer on top of pypdf.

pypdf has no text-layout API and its standard-14 fonts can't encode Czech (č, ř, ě, ů, …), so this
writes the page content streams itself and embeds a TrueType font as a Type0/Identity-H font,
subset with fontTools (glyph IDs kept, ToUnicode map included, so text stays selectable/searchable).
"""

import io
from dataclasses import dataclass, field
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from mdt_backend.config import settings

# (regular, bold) — first pair that exists is used unless PDF_FONT / PDF_FONT_BOLD are set
FONT_CANDIDATES = [
    (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    ("/usr/share/fonts/TTF/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
]

PAGE_W, PAGE_H = 595.28, 841.89  # A4
MARGIN = 50
BLACK = (0, 0, 0)
GREY = (0.45, 0.45, 0.45)
BLUE = (0.11, 0.37, 0.75)

Color = tuple[float, float, float]


def _font_paths() -> tuple[Path, Path]:
    if settings.pdf_font:
        return settings.pdf_font, settings.pdf_font_bold or settings.pdf_font
    for regular, bold in FONT_CANDIDATES:
        if Path(regular).exists() and Path(bold).exists():
            return Path(regular), Path(bold)
    raise FileNotFoundError("No TrueType font with Czech glyphs found; set PDF_FONT/PDF_FONT_BOLD")


class _Font:
    def __init__(self, path: Path, resource: str):
        self.path, self.resource = path, resource
        self.tt = TTFont(path)
        self.cmap = self.tt.getBestCmap()
        self.scale = 1000 / self.tt["head"].unitsPerEm
        self.used: dict[int, str] = {}  # gid -> char

    def gid(self, ch: str) -> int:
        name = self.cmap.get(ord(ch)) or self.cmap.get(ord("?"), ".notdef")
        gid = self.tt.getGlyphID(name)
        self.used.setdefault(gid, ch)
        return gid

    def width(self, text: str, size: float) -> float:
        hmtx = self.tt["hmtx"]
        return (
            sum(hmtx[self.tt.getGlyphName(self.gid(c))][0] for c in text) * self.scale * size / 1000
        )

    def encode(self, text: str) -> str:
        return "<" + "".join(f"{self.gid(c):04X}" for c in text) + ">"

    def build(self, writer: PdfWriter):
        """Embed the subset font; call after all text has been laid out."""
        tt = TTFont(self.path)
        opts = subset.Options()
        opts.retain_gids = True  # content streams already reference the original glyph IDs
        opts.notdef_outline = True
        sub = subset.Subsetter(opts)
        sub.populate(unicodes={ord(c) for c in self.used.values()})
        sub.subset(tt)
        buf = io.BytesIO()
        tt.save(buf)
        data = buf.getvalue()

        file2 = DecodedStreamObject()
        file2.set_data(data)
        file2[NameObject("/Length1")] = NumberObject(len(data))
        file2 = file2.flate_encode()

        base = NameObject("/" + self.tt["name"].getDebugName(6).replace(" ", ""))
        head, hhea = self.tt["head"], self.tt["hhea"]
        s = self.scale
        cap = getattr(self.tt["OS/2"], "sCapHeight", 0) or hhea.ascent
        descriptor = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/FontDescriptor"),
                NameObject("/FontName"): base,
                NameObject("/Flags"): NumberObject(32),
                NameObject("/FontBBox"): ArrayObject(
                    FloatObject(v * s) for v in (head.xMin, head.yMin, head.xMax, head.yMax)
                ),
                NameObject("/ItalicAngle"): NumberObject(0),
                NameObject("/Ascent"): FloatObject(hhea.ascent * s),
                NameObject("/Descent"): FloatObject(hhea.descent * s),
                NameObject("/CapHeight"): FloatObject(cap * s),
                NameObject("/StemV"): NumberObject(80),
                NameObject("/FontFile2"): writer._add_object(file2),
            }
        )
        hmtx = self.tt["hmtx"]
        widths = ArrayObject()
        for gid in sorted(self.used):
            w = hmtx[self.tt.getGlyphName(gid)][0] * s
            widths += [NumberObject(gid), ArrayObject([FloatObject(round(w, 2))])]
        cid = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/CIDFontType2"),
                NameObject("/BaseFont"): base,
                NameObject("/CIDSystemInfo"): DictionaryObject(
                    {
                        NameObject("/Registry"): TextStringObject("Adobe"),
                        NameObject("/Ordering"): TextStringObject("Identity"),
                        NameObject("/Supplement"): NumberObject(0),
                    }
                ),
                NameObject("/FontDescriptor"): writer._add_object(descriptor),
                NameObject("/W"): widths,
                NameObject("/CIDToGIDMap"): NameObject("/Identity"),
            }
        )
        to_unicode = DecodedStreamObject()
        to_unicode.set_data(self._to_unicode_cmap())
        return writer._add_object(
            DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type0"),
                    NameObject("/BaseFont"): base,
                    NameObject("/Encoding"): NameObject("/Identity-H"),
                    NameObject("/DescendantFonts"): ArrayObject([writer._add_object(cid)]),
                    NameObject("/ToUnicode"): writer._add_object(to_unicode.flate_encode()),
                }
            )
        )

    def _to_unicode_cmap(self) -> bytes:
        pairs = sorted(self.used.items())
        out = [
            "/CIDInit /ProcSet findresource begin 12 dict begin begincmap",
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
            "/CMapName /Adobe-Identity-UCS def /CMapType 2 def",
            "1 begincodespacerange <0000> <FFFF> endcodespacerange",
        ]
        for i in range(0, len(pairs), 100):
            chunk = pairs[i : i + 100]
            out.append(f"{len(chunk)} beginbfchar")
            out += [f"<{g:04X}> <{ch.encode('utf-16-be').hex().upper()}>" for g, ch in chunk]
            out.append("endbfchar")
        out.append("endcmap CMapName currentdict /CMap defineresource pop end end")
        return "\n".join(out).encode()


@dataclass
class Run:
    text: str
    bold: bool = False
    color: Color = BLACK


@dataclass
class PdfDoc:
    """Top-to-bottom flowing document: paragraphs of styled runs, wrapped and paginated."""

    title: str
    footer: str = ""
    pages: list[list[str]] = field(default_factory=lambda: [[]])
    y: float = PAGE_H - MARGIN

    def __post_init__(self):
        regular, bold = _font_paths()
        self.fonts = {False: _Font(regular, "/F1"), True: _Font(bold, "/F2")}

    def keep(self, height: float) -> None:
        """Start a new page unless `height` points still fit (keeps headings with their content)."""
        self._ensure(height)

    def _ensure(self, height: float) -> None:
        if self.y - height < MARGIN + 20:
            self.pages.append([])
            self.y = PAGE_H - MARGIN

    def space(self, h: float = 6) -> None:
        self.y -= h

    def rule(self, color: Color = GREY) -> None:
        self._ensure(8)
        self.y -= 4
        self.pages[-1].append(
            f"{color[0]} {color[1]} {color[2]} RG 0.5 w {MARGIN} {self.y:.2f} m "
            f"{PAGE_W - MARGIN} {self.y:.2f} l S"
        )
        self.y -= 4

    def paragraph(
        self,
        runs: list[Run] | str,
        size: float = 10,
        indent: float = 0,
        bar: Color | None = None,
        text_offset: float = 0,
    ) -> None:
        """Wrap runs to the page width. `bar` draws a coloured strip at `indent` (AI marker);
        the text starts `text_offset` further right."""
        if isinstance(runs, str):
            runs = [Run(runs)]
        x0 = MARGIN + indent + (8 if bar else 0) + text_offset
        max_w = PAGE_W - MARGIN - x0
        lines: list[list[tuple[str, Run]]] = [[]]
        width = 0.0
        for run in runs:
            for i, part in enumerate(run.text.replace("\t", " ").split("\n")):
                if i:
                    lines.append([])
                    width = 0.0
                for word in part.split(" "):
                    for token in self._split_long(word, run.bold, size, max_w):
                        pre = " " if lines[-1] else ""
                        w = self.fonts[run.bold].width(pre + token, size)
                        if lines[-1] and width + w > max_w:
                            lines.append([])
                            pre, width = "", 0.0
                            w = self.fonts[run.bold].width(token, size)
                        lines[-1].append((pre + token, run))
                        width += w
        lead = size * 1.3
        for line in lines:
            self._ensure(lead)
            self.y -= lead
            ops = self.pages[-1]
            if bar:
                # spans exactly this line's leading, so consecutive bars join regardless of size
                ops.append(
                    f"{bar[0]} {bar[1]} {bar[2]} rg {MARGIN + indent:.2f} {self.y - 3:.2f} "
                    f"2.5 {lead:.2f} re f"
                )
            x = x0
            for text, run in line:
                font = self.fonts[run.bold]
                c = run.color
                ops.append(
                    f"BT {font.resource} {size} Tf {c[0]} {c[1]} {c[2]} rg "
                    f"{x:.2f} {self.y:.2f} Td {font.encode(text)} Tj ET"
                )
                x += font.width(text, size)

    def _split_long(self, word: str, bold: bool, size: float, max_w: float) -> list[str]:
        font, out, cur = self.fonts[bold], [], ""
        for ch in word:
            if cur and font.width(cur + ch, size) > max_w:
                out.append(cur)
                cur = ""
            cur += ch
        return out + [cur]

    def save(self, path: Path) -> None:
        n = len(self.pages)
        for i, ops in enumerate(self.pages, 1):
            for text, x in ((self.footer, MARGIN), (f"Strana {i}/{n}", PAGE_W - MARGIN - 50)):
                f = self.fonts[False]
                ops.append(f"BT /F1 7 Tf 0.45 0.45 0.45 rg {x:.2f} 30 Td {f.encode(text)} Tj ET")

        writer = PdfWriter()
        fonts = DictionaryObject(
            {NameObject(f.resource): f.build(writer) for f in self.fonts.values()}
        )
        for ops in self.pages:
            page = writer.add_blank_page(PAGE_W, PAGE_H)
            content = DecodedStreamObject()
            content.set_data("\n".join(ops).encode())
            page[NameObject("/Contents")] = writer._add_object(content.flate_encode())
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): fonts})
        writer.add_metadata({"/Title": self.title, "/Producer": "MDT Copilot (pypdf)"})
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            writer.write(fh)
