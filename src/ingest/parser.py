from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

ZERO_WIDTH_CHARS = "\ufeff\u200b\u200c\u200d\u202a\u202b\u202c\u202d\u202e"

CHINESE_NUMERAL = "〇零一二三四五六七八九十百千万"
ROMAN_NUMERAL = "IVXLCDM"
CHAPTER_KEYWORDS = "章节回卷篇部节"
HEADER_KEYWORDS = ("序", "前言", "自序", "引言", "后记", "跋", "序言", "代序", "代后记")
HEADER_PREFIXES = ("正文", "卷首", "本书", "正篇", "正卷")
PARAGRAPH_BREAK_MARKERS = ("——", "***", "＊＊＊", "~~~", "=== ", "---")
MULTI_BLANK_PATTERN = re.compile(r"\n\s*\n\s*\n+")

CHAPTER_PATTERNS = [
    re.compile(
        rf"^\s*(第[\s]*[{CHINESE_NUMERAL}0-9]+[\s]*[{CHAPTER_KEYWORDS}]"
        rf"(?:\s+[{CHINESE_NUMERAL}0-9]+)?)\s*[：:,，、\s．.\-—]*([^\n]*)$",
        re.MULTILINE,
    ),
    re.compile(
        rf"^\s*([{CHAPTER_KEYWORDS}][\s]*[{CHINESE_NUMERAL}0-9]+)\s*[：:,，、\s．.\-—]*([^\n]*)$",
        re.MULTILINE,
    ),
    re.compile(
        r"^\s*((?:CHAPTER|Chapter|chapter)\s+[0-9IVXLCDM]+)\s*[：:,，、\s．.\-—]*([^\n]*)$",
        re.MULTILINE,
    ),
    re.compile(
        rf"^\s*([（(][\s]*[{CHINESE_NUMERAL}0-9{ROMAN_NUMERAL}]+[\s]*[)）])\s*[：:,，、\s．.\-—]*([^\n]*)$",
        re.MULTILINE,
    ),
]

SIMPLE_HEADER_PATTERN = re.compile(
    rf"^(?:第)?[{CHINESE_NUMERAL}0-9{ROMAN_NUMERAL}]+(?:[{CHAPTER_KEYWORDS}])?$",
    re.IGNORECASE,
)

ROMAN_NUMERAL_PATTERN = re.compile(rf"^[{ROMAN_NUMERAL}]+$", re.IGNORECASE)

MAX_TITLE_LENGTH = 512
TARGET_CHUNK_SIZE = 2200
MIN_CHUNK_SIZE = 800
MAX_CHUNK_SIZE = 3600
logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    index: int
    title: str
    content: str


@dataclass
class BookMetadata:
    title: str
    author: Optional[str]
    chapters: List[Chapter]


class BookParserError(Exception):
    """Raised when a TXT file cannot be parsed into chapters."""


class BookParser:
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(self.file_path)

    @staticmethod
    def _looks_like_numeric_token(token: str) -> bool:
        stripped = token.strip("()（）．.、，：:—-")
        if not stripped:
            return False
        if all(ch in CHINESE_NUMERAL for ch in stripped):
            return True
        if stripped.isdigit():
            return True
        if ROMAN_NUMERAL_PATTERN.fullmatch(stripped):
            return True
        return False

    def _normalize_header_line(self, line: str) -> Optional[str]:
        stripped = line.strip()
        if not stripped or len(stripped) > 40:
            return None
        candidate = stripped.rstrip("：:、．.()（）-—*~　")
        if not candidate:
            return None
        no_spaces = candidate.replace(" ", "")
        if any(candidate.startswith(keyword) for keyword in HEADER_KEYWORDS):
            return candidate

        lower = candidate.lower()
        if lower.startswith("chapter"):
            return candidate.title()

        tokens = candidate.split()

        if candidate.startswith("第") and any(k in candidate for k in CHAPTER_KEYWORDS):
            if len(tokens) > 1 and self._looks_like_numeric_token(tokens[-1]):
                return f"{tokens[0]} · {tokens[-1]}"
            return tokens[0] if tokens else candidate

        if len(tokens) == 1 and self._looks_like_numeric_token(tokens[0]):
            return tokens[0]

        if (
            len(tokens) == 2
            and any(k in tokens[0] for k in CHAPTER_KEYWORDS)
            and self._looks_like_numeric_token(tokens[1])
        ):
            return f"{tokens[0]} · {tokens[1]}"

        if self._looks_like_numeric_token(no_spaces) and len(no_spaces) <= 6:
            return no_spaces

        for pattern in CHAPTER_PATTERNS:
            match = pattern.match(candidate)
            if match:
                groups = [g for g in match.groups() if g]
                title = " ".join(groups).strip()
                return title

        return None

    @staticmethod
    def _finalize_sections(sections: List["Section"], text_length: int) -> List["Section"]:
        if not sections:
            return []
        for idx, section in enumerate(sections):
            next_start = sections[idx + 1].start if idx + 1 < len(sections) else text_length
            section.end = next_start
        return sections

    def parse(self) -> BookMetadata:
        raw_text = self._read_file()
        header_title, header_author = self._extract_header(raw_text)
        sections = self._locate_sections(raw_text)
        if not sections:
            raise BookParserError(f"No chapters detected in {self.file_path}")

        chapters: List[Chapter] = []
        for idx, section in enumerate(sections):
            content = self._clean_text(raw_text[section.start : section.end])
            if not content:
                continue
            chapters.append(
                Chapter(
                    index=idx + 1,
                    title=self._sanitize_title(section.title),
                    content=content,
                )
            )

        meta = BookMetadata(
            title=header_title or self.file_path.stem,
            author=header_author,
            chapters=chapters,
        )
        return meta

    def _locate_sections(self, text: str) -> List["Section"]:
        sections = self._sections_from_matches(text)
        if sections:
            return sections

        sections = self._sections_from_simple_headers(text)
        if sections:
            logger.info("Using simple header fallback for %s", self.file_path)
            return sections

        sections = self._sections_from_paragraph_breaks(text)
        if sections:
            logger.info("Using paragraph break fallback for %s", self.file_path)
            return sections

        sections = self._sections_from_auto_chunks(text)
        if sections:
            logger.info("Using auto chunk fallback for %s", self.file_path)
        return sections

    def _sections_from_matches(self, text: str) -> List["Section"]:
        sections: List[Section] = []
        offsets = list(self._iter_line_offsets(text))
        for start, line in offsets:
            title = self._normalize_header_line(line)
            if not title:
                continue
            section_start = start + len(line)
            sections.append(Section(title=title, start=section_start, end=0))
        if len(sections) < 2:
            return []
        return self._finalize_sections(sections, len(text))

    def _sections_from_simple_headers(self, text: str) -> List["Section"]:
        headers: List[Section] = []
        offsets = self._iter_line_offsets(text)
        offsets_list = list(offsets)
        for idx, (start, line) in enumerate(offsets_list):
            stripped = line.strip()
            if not stripped:
                continue
            candidate = stripped.rstrip("：:、．.()（）-—*~　")
            if len(candidate) > 12:
                continue
            if SIMPLE_HEADER_PATTERN.fullmatch(candidate):
                prev_blank = idx > 0 and not offsets_list[idx - 1][1].strip()
                next_blank = idx + 1 < len(offsets_list) and not offsets_list[idx + 1][1].strip()
                if not (prev_blank or next_blank):
                    continue
                headers.append(
                    Section(
                        title=stripped,
                        start=start + len(line),
                        end=0,  # placeholder
                    )
                )
            elif any(keyword in stripped for keyword in HEADER_KEYWORDS):
                headers.append(
                    Section(
                        title=stripped,
                        start=start + len(line),
                        end=0,
                    )
                )
        if len(headers) < 2:
            return []
        return self._finalize_sections(headers, len(text))

    def _sections_from_paragraph_breaks(self, text: str) -> List["Section"]:
        break_positions = {match.start(): match.end() for match in MULTI_BLANK_PATTERN.finditer(text)}

        for start, line in self._iter_line_offsets(text):
            stripped = line.strip()
            if not stripped:
                continue
            if any(marker in stripped for marker in PARAGRAPH_BREAK_MARKERS):
                break_positions[start] = start + len(line)

        if not break_positions:
            return []

        sections: List[Section] = []
        last = 0
        idx = 1
        for split_start in sorted(break_positions.keys()):
            if split_start - last < MIN_CHUNK_SIZE:
                continue
            segment_end = split_start
            sections.append(
                Section(
                    title=f"段落分段 {idx:03d}",
                    start=last,
                    end=segment_end,
                )
            )
            idx += 1
            last = break_positions[split_start]

        if len(text) - last >= MIN_CHUNK_SIZE:
            sections.append(
                Section(
                    title=f"段落分段 {idx:03d}",
                    start=last,
                    end=len(text),
                )
            )

        if len(sections) < 2:
            return []
        return sections

    def _sections_from_auto_chunks(self, text: str) -> List["Section"]:
        sections: List[Section] = []
        length = len(text)
        start = 0
        chunk_index = 1
        while start < length:
            tentative_end = min(length, start + MAX_CHUNK_SIZE)
            split_point = self._find_split_point(text, start, tentative_end)
            sections.append(
                Section(
                    title=f"自动分段 {chunk_index:03d}",
                    start=start,
                    end=split_point,
                )
            )
            chunk_index += 1
            start = split_point
            while start < length and text[start].isspace():
                start += 1
        return sections

    def _find_split_point(self, text: str, start: int, max_end: int) -> int:
        length = len(text)
        search_end = min(length, max_end)
        preferred = min(length, start + TARGET_CHUNK_SIZE)
        min_pos = min(length, start + MIN_CHUNK_SIZE)
        if min_pos >= search_end:
            return search_end

        split = text.rfind("\n\n", preferred, search_end)
        if split == -1 or split <= start:
            for delimiter in ("。", "！", "？", "；", ".", "!", "?"):
                split = text.rfind(delimiter, preferred, search_end)
                if split != -1:
                    split += 1
                    break
        if split == -1 or split <= start:
            split = search_end
        return split

    @staticmethod
    def _iter_line_offsets(text: str):
        offset = 0
        for line in text.splitlines(True):
            yield offset, line
            offset += len(line)

    @staticmethod
    def _sanitize_title(title: str) -> str:
        trimmed = title.strip()
        if len(trimmed) > MAX_TITLE_LENGTH:
            logger.warning(
                "Chapter title too long (%s chars), truncating to %s",
                len(trimmed),
                MAX_TITLE_LENGTH,
            )
            return trimmed[:MAX_TITLE_LENGTH]
        return trimmed
    def _read_file(self) -> str:
        return self.file_path.read_text(encoding="utf-8", errors="ignore")

    def _extract_header(self, text: str) -> tuple[Optional[str], Optional[str]]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else self.file_path.stem
        author = None
        if len(lines) > 1:
            author_line = lines[1]
            if "著" in author_line or "作者" in author_line:
                author = author_line
        return title, author

    def _clean_text(self, text: str) -> str:
        cleaned = text.replace("\r", "")
        for ch in ZERO_WIDTH_CHARS:
            cleaned = cleaned.replace(ch, "")
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        paragraphs = [para.strip() for para in cleaned.split("\n")]
        return "\n".join([p for p in paragraphs if p])


@dataclass
class Section:
    title: str
    start: int
    end: int


__all__ = ["BookParser", "BookMetadata", "Chapter", "BookParserError"]
