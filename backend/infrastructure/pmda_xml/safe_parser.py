"""Bounded XML parsing with Expat declaration callbacks before tree construction."""

import re
import xml.etree.ElementTree as ET
from typing import Never
from xml.parsers import expat

from ...application.attachment_import.import_errors import (
    ImportLimitExceeded,
    InvalidAttachment,
    UnsupportedAttachment,
)

MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_DEPTH = 256
MAX_ELEMENTS = 200000


def _decode_text(source: bytes) -> str:
    if source.startswith((b"\xff\xfe", b"\xfe\xff")):
        return source.decode("utf-16")
    if source.startswith(b"<\x00?\x00"):
        return source.decode("utf-16-le")
    if source.startswith(b"\x00<\x00?"):
        return source.decode("utf-16-be")
    declaration = re.match(
        rb'(?:\xef\xbb\xbf)?<\?xml\s[^?]*encoding\s*=\s*[\'"]([^\'"]+)[\'"]',
        source[:1024],
    )
    encoding = declaration.group(1).decode("ascii") if declaration else "utf-8-sig"
    if encoding.lower().replace("_", "-").startswith("utf-16"):
        raise UnicodeError("UTF-16 declaration without UTF-16 bytes")
    return source.decode(encoding)


def parse_source(source: bytes) -> tuple[ET.Element, list[dict[str, object]]]:
    if not source:
        raise InvalidAttachment("empty_source", "XML input is empty")
    if len(source) > MAX_SOURCE_BYTES:
        raise ImportLimitExceeded(
            "source_size_limit", "XML input exceeds the size limit"
        )
    if source.startswith((b"PK\x03\x04", b"\x1f\x8b")) or (
        b"\x00" in source[:128]
        and not source.startswith((b"\xff\xfe", b"\xfe\xff", b"<\x00", b"\x00<"))
    ):
        raise UnsupportedAttachment("unsupported_input", "Input is not supported XML")
    try:
        text = _decode_text(source)
    except UnicodeError, LookupError:
        raise InvalidAttachment("xml_parse_error", "XML encoding is invalid") from None
    if not text.lstrip("\ufeff \r\n\t").startswith("<"):
        raise UnsupportedAttachment("unsupported_input", "Input is not supported XML")
    # Unicode parsing must not hide a declaration claiming a different byte encoding.
    declared = re.match(
        r'\ufeff?<\?xml\s[^?]*encoding\s*=\s*[\'"]([^\'"]+)[\'"]', text[:1024]
    )
    utf16_bytes = source.startswith((b"\xff\xfe", b"\xfe\xff", b"<\x00", b"\x00<"))
    if (
        declared
        and declared.group(1).lower().replace("_", "-").startswith("utf-16")
        != utf16_bytes
    ):
        raise InvalidAttachment("xml_parse_error", "XML declaration and bytes disagree")
    events: list[dict[str, object]] = []
    parser = expat.ParserCreate()
    depth = 0
    count = 0

    def start(name: str, attributes: dict[str, str]) -> None:
        nonlocal depth, count
        depth += 1
        count += 1
        if depth > MAX_DEPTH:
            raise InvalidAttachment("xml_depth_limit", "XML nesting exceeds the limit")
        if count > MAX_ELEMENTS:
            raise InvalidAttachment(
                "xml_element_limit", "XML element count exceeds the limit"
            )
        events.append(
            {
                "kind": "start",
                "name": name,
                "attributes": attributes,
                "depth": depth,
                "line": parser.CurrentLineNumber,
                "column": parser.CurrentColumnNumber,
            }
        )

    def end(name: str) -> None:
        nonlocal depth
        events.append({"kind": "end", "name": name, "depth": depth})
        depth -= 1

    def forbidden(*args: object) -> Never:
        raise InvalidAttachment(
            "xml_forbidden_declaration", "DTD and entity declarations are not supported"
        )

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = forbidden
    parser.EntityDeclHandler = forbidden
    parser.ExternalEntityRefHandler = lambda *args: forbidden(*args)
    parser.ProcessingInstructionHandler = lambda target, data: events.append(
        {
            "kind": "pi",
            "target": target,
            "data": data,
            "depth": depth,
            "line": parser.CurrentLineNumber,
            "column": parser.CurrentColumnNumber,
        }
    )
    parser.CommentHandler = lambda data: events.append(
        {
            "kind": "comment",
            "data": data,
            "depth": depth,
            "line": parser.CurrentLineNumber,
            "column": parser.CurrentColumnNumber,
        }
    )
    # Only PI/comment/start/end metadata is retained; original text/tail is in tree and source.xml.
    try:
        parser.Parse(text, True)
        root = ET.fromstring(
            text,
            parser=ET.XMLParser(
                target=ET.TreeBuilder(insert_comments=True, insert_pis=True)
            ),
        )
    except expat.ExpatError, ET.ParseError, ValueError:
        raise InvalidAttachment("xml_parse_error", "XML cannot be parsed") from None
    if any(
        isinstance(element.tag, str)
        and element.tag.startswith("{http://www.w3.org/2001/XInclude}")
        for element in root.iter()
    ):
        raise InvalidAttachment(
            "xml_unsupported_structure", "XInclude is not supported"
        )
    return root, events
