"""Static high-resolution figure rendering for CrewAI Flows."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class FlowNode:
    id: str
    kind: str


@dataclass(frozen=True)
class FlowEdge:
    source: str
    target: str
    label: str = ""
    kind: str = "or"


def render_flow_png(flow: Any, output_path: Path, *, scale: int = 2) -> Path:
    """Render a Flow graph to a high-resolution PNG.

    CrewAI's interactive HTML renders the graph on a browser canvas. Browser
    exports are tied to the current viewport, so this static renderer draws from
    Flow metadata directly and produces a predictable high-DPI artifact.
    """
    nodes, edges = _extract_graph(flow)
    positions, canvas_size, node_size = _layout(nodes, edges, flow, scale=scale)

    image = Image.new("RGB", canvas_size, "#fbfbfa")
    draw = ImageDraw.Draw(image)
    _draw_grid(draw, canvas_size, scale)

    fonts = _load_fonts(scale)
    for edge in edges:
        _draw_edge(draw, edge, positions, node_size, fonts, scale)

    for node in nodes:
        _draw_node(draw, node, positions[node.id], node_size, fonts, scale)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, dpi=(240, 240))
    return output_path


def patch_png_export_button(script_path: Path, png_filename: str) -> None:
    """Point CrewAI's HTML PNG export button at the generated static PNG."""
    try:
        source = script_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return

    old = """    document.getElementById("export-png").addEventListener("click", () => {
      const script = document.createElement("script");
      script.src =
        "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";
      script.onload = () => {
        html2canvas(document.getElementById("network-container")).then(
          (canvas) => {
            const link = document.createElement("a");
            link.download = "flow.png";
            link.href = canvas.toDataURL();
            link.click();
          },
        );
      };
      document.head.appendChild(script);
    });"""
    new = f"""    document.getElementById("export-png").addEventListener("click", () => {{
      const link = document.createElement("a");
      link.download = "{png_filename}";
      link.href = "{png_filename}";
      link.click();
    }});"""
    if old in source:
        script_path.write_text(source.replace(old, new, 1), encoding="utf-8")


def _extract_graph(flow: Any) -> tuple[list[FlowNode], list[FlowEdge]]:
    listeners: dict[str, Any] = dict(getattr(flow, "_listeners", {}))
    routers = set(getattr(flow, "_routers", set()))
    router_paths: dict[str, Iterable[str]] = dict(getattr(flow, "_router_paths", {}))
    start_methods = list(getattr(flow, "_start_methods", []))

    node_ids: list[str] = []

    def add_node(node_id: str) -> None:
        if node_id and node_id not in node_ids:
            node_ids.append(node_id)

    for method in start_methods:
        add_node(method)
    for method in listeners:
        add_node(method)
    for method in routers:
        add_node(method)

    method_names = set(node_ids)
    edges: list[FlowEdge] = []

    for target, condition in listeners.items():
        condition_type, sources = _condition_sources(condition)
        for source in sources:
            if source in method_names:
                label = "AND" if condition_type == "AND" else ""
                edges.append(FlowEdge(source, target, label=label, kind=condition_type.lower()))

    for router, paths in router_paths.items():
        add_node(router)
        for path in paths:
            for target, condition in listeners.items():
                _, sources = _condition_sources(condition)
                if path in sources:
                    edges.append(FlowEdge(router, target, label=path, kind="router"))

    nodes = [
        FlowNode(
            node_id,
            "start" if node_id in start_methods else "router" if node_id in routers else "listen",
        )
        for node_id in node_ids
    ]
    return nodes, _dedupe_edges(edges)


def _condition_sources(condition: Any) -> tuple[str, list[str]]:
    if isinstance(condition, tuple) and len(condition) == 2:
        condition_type, raw_sources = condition
        return str(condition_type).upper(), list(_flatten_sources(raw_sources))
    if isinstance(condition, dict):
        condition_type = str(condition.get("type", "OR")).upper()
        return condition_type, list(_flatten_sources(condition.get("conditions", [])))
    return "OR", list(_flatten_sources(condition))


def _flatten_sources(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        yield from _flatten_sources(value.get("conditions", []))
        return
    if isinstance(value, Iterable):
        for item in value:
            yield from _flatten_sources(item)


def _dedupe_edges(edges: list[FlowEdge]) -> list[FlowEdge]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[FlowEdge] = []
    for edge in edges:
        key = (edge.source, edge.target, edge.label, edge.kind)
        if key not in seen:
            seen.add(key)
            result.append(edge)
    return result


def _layout(
    nodes: list[FlowNode],
    edges: list[FlowEdge],
    flow: Any,
    *,
    scale: int,
) -> tuple[dict[str, tuple[int, int]], tuple[int, int], tuple[int, int]]:
    node_ids = [node.id for node in nodes]
    starts = [method for method in getattr(flow, "_start_methods", []) if method in node_ids]
    if not starts and node_ids:
        starts = [node_ids[0]]

    outgoing: dict[str, list[FlowEdge]] = defaultdict(list)
    for edge in edges:
        outgoing[edge.source].append(edge)

    levels: dict[str, int] = {}
    queue: list[str] = []
    for start in starts:
        levels[start] = 0
        queue.append(start)

    while queue:
        source = queue.pop(0)
        for edge in outgoing.get(source, []):
            if edge.target not in levels:
                levels[edge.target] = levels[source] + 1
                queue.append(edge.target)

    for node_id in node_ids:
        if node_id not in levels:
            levels[node_id] = max(levels.values(), default=-1) + 1

    grouped: dict[int, list[str]] = defaultdict(list)
    for node_id in node_ids:
        grouped[levels[node_id]].append(node_id)

    node_w = 320 * scale
    node_h = 72 * scale
    h_gap = 50 * scale
    v_gap = 105 * scale
    margin_x = 80 * scale
    margin_y = 80 * scale
    min_width = 900 * scale
    min_height = 900 * scale
    max_items_per_row = 3
    row_gap = 48 * scale

    level_count = max(grouped.keys(), default=0) + 1
    max_columns = min(max((len(items) for items in grouped.values()), default=1), max_items_per_row)
    width = max(min_width, margin_x * 2 + max_columns * node_w + (max_columns - 1) * h_gap)
    level_heights = []
    for level in range(level_count):
        rows = max(1, math.ceil(len(grouped.get(level, [])) / max_items_per_row))
        level_heights.append(rows * node_h + (rows - 1) * row_gap)
    height = max(min_height, margin_y * 2 + sum(level_heights) + max(0, level_count - 1) * v_gap)

    positions: dict[str, tuple[int, int]] = {}
    y_cursor = margin_y
    for level in range(level_count):
        items = grouped.get(level, [])
        rows = [items[i : i + max_items_per_row] for i in range(0, len(items), max_items_per_row)] or [[]]
        for row_index, row in enumerate(rows):
            row_w = len(row) * node_w + max(0, len(row) - 1) * h_gap
            x = (width - row_w) // 2 + node_w // 2
            y = y_cursor + row_index * (node_h + row_gap) + node_h // 2
            for node_id in row:
                positions[node_id] = (x, y)
                x += node_w + h_gap
        y_cursor += level_heights[level] + v_gap

    return positions, (width, height), (node_w, node_h)


def _load_fonts(scale: int) -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    def load(candidates: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()

    regular = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    bold = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    return {
        "regular": load(regular, 18 * scale),
        "bold": load(bold, 19 * scale),
        "small": load(regular, 11 * scale),
        "label": load(regular, 12 * scale),
    }


def _draw_grid(draw: ImageDraw.ImageDraw, size: tuple[int, int], scale: int) -> None:
    step = 24 * scale
    width, height = size
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill="#ededeb", width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill="#ededeb", width=1)


def _draw_node(
    draw: ImageDraw.ImageDraw,
    node: FlowNode,
    center: tuple[int, int],
    node_size: tuple[int, int],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
    scale: int,
) -> None:
    x, y = center
    width, height = node_size
    left = x - width // 2
    top = y - height // 2
    rect = [left, top, left + width, top + height]
    radius = 14 * scale

    styles = {
        "start": ("#ff7066", "#c94238", "#ffffff"),
        "router": ("#ffffff", "#ff5a50", "#222222"),
        "listen": ("#ffffff", "#3d3d3d", "#222222"),
    }
    fill, border, text = styles[node.kind]

    shadow = [rect[0] + 5 * scale, rect[1] + 6 * scale, rect[2] + 5 * scale, rect[3] + 6 * scale]
    draw.rounded_rectangle(shadow, radius=radius, fill="#dfdfdc")
    draw.rounded_rectangle(rect, radius=radius, fill=fill, outline=border, width=3 * scale)

    kind_label = node.kind.upper()
    label_font = fonts["small"]
    label_box = draw.textbbox((0, 0), kind_label, font=label_font)
    label_w = label_box[2] - label_box[0] + 14 * scale
    label_h = label_box[3] - label_box[1] + 8 * scale
    label_rect = [left + 14 * scale, top + 10 * scale, left + 14 * scale + label_w, top + 10 * scale + label_h]
    label_fill = "#ff8a82" if node.kind == "start" else "#f4f4f3"
    label_text = "#ffffff" if node.kind == "start" else "#666666"
    draw.rounded_rectangle(label_rect, radius=5 * scale, fill=label_fill)
    draw.text(
        (label_rect[0] + 7 * scale, label_rect[1] + 3 * scale),
        kind_label,
        font=label_font,
        fill=label_text,
    )

    name_lines = _wrap_label(draw, node.id, fonts["bold"], width - 44 * scale)
    total_text_h = sum(_text_size(draw, line, fonts["bold"])[1] for line in name_lines)
    total_text_h += max(0, len(name_lines) - 1) * 4 * scale
    text_y = y - total_text_h // 2 + 12 * scale
    for line in name_lines:
        line_w, line_h = _text_size(draw, line, fonts["bold"])
        draw.text((x - line_w // 2, text_y), line, font=fonts["bold"], fill=text)
        text_y += line_h + 4 * scale


def _draw_edge(
    draw: ImageDraw.ImageDraw,
    edge: FlowEdge,
    positions: dict[str, tuple[int, int]],
    node_size: tuple[int, int],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
    scale: int,
) -> None:
    if edge.source not in positions or edge.target not in positions:
        return

    node_w, node_h = node_size
    sx, sy = positions[edge.source]
    tx, ty = positions[edge.target]
    forward = ty > sy
    color = "#ff5a50" if edge.kind in {"router", "and"} else "#222222"
    width = 3 * scale if edge.kind == "router" else 2 * scale
    dash = (12 * scale, 9 * scale) if edge.kind == "router" else None

    if forward:
        start = (sx, sy + node_h // 2)
        end = (tx, ty - node_h // 2)
        mid_y = (start[1] + end[1]) // 2
        points = [start, (sx, mid_y), (tx, mid_y), end]
    else:
        start = (sx + node_w // 2, sy)
        end = (tx + node_w // 2, ty)
        loop_x = max(sx, tx) + node_w // 2 + 70 * scale
        points = [start, (loop_x, sy), (loop_x, ty), end]

    _draw_polyline(draw, points, fill=color, width=width, dash=dash)
    _draw_arrowhead(draw, points[-2], points[-1], color, scale)

    if edge.label:
        label_at = _polyline_midpoint(points)
        _draw_edge_label(draw, edge.label, label_at, fonts["label"], scale)


def _draw_polyline(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    *,
    fill: str,
    width: int,
    dash: tuple[int, int] | None = None,
) -> None:
    for start, end in zip(points, points[1:]):
        if dash:
            _draw_dashed_segment(draw, start, end, fill=fill, width=width, dash=dash)
        else:
            draw.line([start, end], fill=fill, width=width)


def _draw_dashed_segment(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    fill: str,
    width: int,
    dash: tuple[int, int],
) -> None:
    x1, y1 = start
    x2, y2 = end
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    dash_len, gap_len = dash
    distance = 0.0
    while distance < length:
        segment_end = min(distance + dash_len, length)
        p1 = (x1 + (x2 - x1) * distance / length, y1 + (y2 - y1) * distance / length)
        p2 = (x1 + (x2 - x1) * segment_end / length, y1 + (y2 - y1) * segment_end / length)
        draw.line([p1, p2], fill=fill, width=width)
        distance += dash_len + gap_len


def _draw_arrowhead(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: str,
    scale: int,
) -> None:
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = 12 * scale
    spread = math.radians(28)
    p1 = (
        end[0] - size * math.cos(angle - spread),
        end[1] - size * math.sin(angle - spread),
    )
    p2 = (
        end[0] - size * math.cos(angle + spread),
        end[1] - size * math.sin(angle + spread),
    )
    draw.polygon([end, p1, p2], fill=fill)


def _draw_edge_label(
    draw: ImageDraw.ImageDraw,
    label: str,
    center: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    scale: int,
) -> None:
    text_w, text_h = _text_size(draw, label, font)
    pad_x = 8 * scale
    pad_y = 5 * scale
    rect = [
        center[0] - text_w // 2 - pad_x,
        center[1] - text_h // 2 - pad_y,
        center[0] + text_w // 2 + pad_x,
        center[1] + text_h // 2 + pad_y,
    ]
    draw.rounded_rectangle(rect, radius=5 * scale, fill="#ffffff", outline="#dededb", width=1 * scale)
    draw.text((center[0] - text_w // 2, center[1] - text_h // 2), label, font=font, fill="#333333")


def _polyline_midpoint(points: list[tuple[int, int]]) -> tuple[int, int]:
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    if total == 0:
        return points[0]
    target = total / 2
    walked = 0.0
    for length, start, end in zip(lengths, points, points[1:]):
        if walked + length >= target:
            ratio = (target - walked) / length if length else 0
            return (
                int(start[0] + (end[0] - start[0]) * ratio),
                int(start[1] + (end[1] - start[1]) * ratio),
            )
        walked += length
    return points[-1]


def _wrap_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    parts = text.split("_")
    tokens = [part + ("_" if index < len(parts) - 1 else "") for index, part in enumerate(parts)]
    lines: list[str] = []
    current = ""
    for token in tokens:
        candidate = current + token
        if current and _text_size(draw, candidate, font)[0] > max_width:
            lines.append(current.rstrip("_"))
            current = token
        else:
            current = candidate
    if current:
        lines.append(current.rstrip("_"))
    return lines or [text]


def _text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]
