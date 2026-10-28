"""A2UI v0.9 Component Showcase Agent for Gemini Enterprise.

Contains 6 minimal, self-contained examples — one for each core A2UI component:
1. MaterialCard      -> `build_material_card_example()`
2. MaterialButton    -> `build_material_button_example()`
3. MaterialRow       -> `build_material_row_example()`
4. RichTable         -> `build_rich_table_example()`
5. VegaChart         -> `build_vega_chart_example()`
6. Canvas            -> `build_canvas_example()`
"""

from __future__ import annotations

import json
from typing import Any, Optional
import uuid

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.tool_context import ToolContext
from google.genai import types

VERSION = "v0.9"
CATALOG_ID = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
)
MIME_TYPE = "application/json+a2ui"
SENTINEL_OPEN = "<a2a_datapart_json>"
SENTINEL_CLOSE = "</a2a_datapart_json>"


# ---------------------------------------------------------------------------
# Wire Helpers
# ---------------------------------------------------------------------------

def wrap_a2ui_message(message: dict[str, Any]) -> types.Part:
    """Wrap an A2UI v0.9 protocol message into a GenAI Part."""
    payload = json.dumps({
        "kind": "data",
        "metadata": {"mimeType": MIME_TYPE},
        "data": message,
    })
    blob_bytes = f"{SENTINEL_OPEN}{payload}{SENTINEL_CLOSE}".encode("utf-8")
    return types.Part(
        inline_data=types.Blob(mime_type="text/plain", data=blob_bytes),
        part_metadata={"mimeType": MIME_TYPE},
    )


def build_surface(
    surface_id: str,
    components: list[dict[str, Any]],
    data_model_spec: Optional[dict[str, Any]] = None,
) -> list[types.Part]:
    """Emit createSurface + updateComponents (+ optional updateDataModel for VegaChart)."""
    parts = [
        wrap_a2ui_message({
            "version": VERSION,
            "createSurface": {"surfaceId": surface_id, "catalogId": CATALOG_ID},
        }),
        wrap_a2ui_message({
            "version": VERSION,
            "updateComponents": {"surfaceId": surface_id, "components": components},
        }),
    ]
    if data_model_spec is not None:
        parts.append(
            wrap_a2ui_message({
                "version": VERSION,
                "updateDataModel": {
                    "surfaceId": surface_id,
                    "path": "/spec",
                    "value": data_model_spec,
                },
            })
        )
    return parts


def decode_a2ui_part(part: Any) -> Optional[dict[str, Any]]:
    blob = getattr(part, "inline_data", None)
    data = getattr(blob, "data", None)
    if not isinstance(data, (bytes, bytearray)):
        return None
    text = bytes(data).decode("utf-8", errors="replace").strip()
    if not text.startswith(SENTINEL_OPEN):
        return None
    payload = text[len(SENTINEL_OPEN) :].split(SENTINEL_CLOSE, 1)[0]
    try:
        envelope = json.loads(payload)
        return envelope if isinstance(envelope, dict) else None
    except ValueError:
        return None


def find_a2ui_action(parts: Any) -> Optional[dict[str, Any]]:
    for part in parts or []:
        envelope = decode_a2ui_part(part)
        if not envelope:
            continue
        inner = envelope.get("data", envelope)
        if isinstance(inner, dict) and isinstance(inner.get("action"), dict):
            return inner["action"]
    return None


# ===========================================================================
# EXAMPLE 1: MaterialCard (Inline Chat Container)
# ===========================================================================

def build_material_card_example() -> list[types.Part]:
    """Simplest inline MaterialCard rendered directly in the chat stream."""
    surface_id = f"card_{uuid.uuid4().hex[:8]}"
    components = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "outlined",  # "outlined" | "elevated" | "filled"
            "children": ["card_col"],
        },
        {
            "id": "card_col",
            "component": "MaterialColumn",
            "justify": "start",
            "align": "stretch",
            "style": {"gap": "6px"},
            "children": ["card_title", "card_body"],
        },
        {
            "id": "card_title",
            "component": "MaterialText",
            "text": "PixelBook Pro — Order #1042",
            "usageHint": "h4",
        },
        {
            "id": "card_body",
            "component": "MaterialText",
            "text": "Status: **Shipped** · Estimated delivery: Tomorrow by 5:00 PM.",
            "usageHint": "body1",
        },
    ]
    return build_surface(surface_id, components)


# ===========================================================================
# EXAMPLE 2: MaterialButton (Interactive Button with Event & Context)
# ===========================================================================

def build_material_button_example() -> list[types.Part]:
    """Inline card featuring a clickable MaterialButton that triggers a backend action."""
    surface_id = f"button_{uuid.uuid4().hex[:8]}"
    components = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["btn_col"],
        },
        {
            "id": "btn_col",
            "component": "MaterialColumn",
            "justify": "start",
            "align": "start",
            "style": {"gap": "10px"},
            "children": ["btn_prompt", "approve_btn"],
        },
        {
            "id": "btn_prompt",
            "component": "MaterialText",
            "text": "Click the button below to approve purchase request **PR-900**:",
            "usageHint": "body1",
        },
        {
            "id": "approve_btn",
            "component": "MaterialButton",
            "label": "Approve PR-900",
            "variant": "raised",       # "raised" | "outlined" | "basic"
            "color": "primary",        # "primary" | "secondary"
            "leadingIcon": "check",
            "action": {
                "event": {
                    "name": "approve_request",
                    "context": {"request_id": "PR-900", "amount": "$1,299"},
                }
            },
        },
    ]
    return build_surface(surface_id, components)


# ===========================================================================
# EXAMPLE 3: MaterialRow (Horizontal Layout — Text on Left, Button on Right)
# ===========================================================================

def build_material_row_example() -> list[types.Part]:
    """MaterialRow aligning a product label and a [Details] button horizontally."""
    surface_id = f"row_{uuid.uuid4().hex[:8]}"
    components = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["product_row"],
        },
        {
            "id": "product_row",
            "component": "MaterialRow",
            "justify": "spaceBetween",  # Pushes text left and button right
            "align": "center",
            "children": ["row_text", "row_btn"],
        },
        {
            "id": "row_text",
            "component": "MaterialText",
            "text": "**PixelBook Pro** ($1,299) — 14-inch developer laptop",
            "usageHint": "body1",
        },
        {
            "id": "row_btn",
            "component": "MaterialButton",
            "label": "Details",
            "variant": "outlined",
            "color": "primary",
            "action": {
                "event": {
                    "name": "view_details",
                    "context": {"product_name": "PixelBook Pro", "price": "$1,299"},
                }
            },
        },
    ]
    return build_surface(surface_id, components)


# ===========================================================================
# EXAMPLE 4: Looker Studio RichTable (Interactive Sortable/Chartable Grid)
# ===========================================================================

def build_rich_table_example() -> list[types.Part]:
    """Looker Studio RichTable with sortable numeric columns and spec={}."""
    surface_id = f"table_{uuid.uuid4().hex[:8]}"
    components = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["table_col"],
        },
        {
            "id": "table_col",
            "component": "MaterialColumn",
            "justify": "start",
            "align": "stretch",
            "style": {"gap": "8px"},
            "children": ["table_heading", "inventory_table"],
        },
        {
            "id": "table_heading",
            "component": "MaterialText",
            "text": "Product Inventory (Sort, Filter & Chart in Looker Studio)",
            "usageHint": "subtitle1",
        },
        {
            "id": "inventory_table",
            "component": "RichTable",
            "tableData": {
                # 1. Schema uses only "STRING" or "DOUBLE"
                "schema": [
                    {"name": "Product", "dataType": "STRING"},
                    {"name": "Category", "dataType": "STRING"},
                    {"name": "Price_USD", "dataType": "DOUBLE"},
                    {"name": "Units_In_Stock", "dataType": "DOUBLE"},
                ],
                # 2. Numeric cells MUST be raw int/float (never "$1,299" strings)
                "data": [
                    {"Product": "PixelBook Pro", "Category": "Laptops", "Price_USD": 1299.0, "Units_In_Stock": 42},
                    {"Product": "Pixel Buds Studio", "Category": "Audio", "Price_USD": 199.0, "Units_In_Stock": 180},
                    {"Product": "Nest Hub Max", "Category": "Smart Home", "Price_USD": 229.0, "Units_In_Stock": 95},
                ],
                # 3. CRITICAL: spec MUST be {} (empty dict) so Looker auto-configures columns
                "spec": {},
            },
        },
    ]
    return build_surface(surface_id, components)


# ===========================================================================
# EXAMPLE 5: VegaChart (Interactive Vega-Lite Visualization + updateDataModel)
# ===========================================================================

def build_vega_chart_example() -> list[types.Part]:
    """VegaChart bound to /spec via a 3rd updateDataModel protocol message."""
    surface_id = f"chart_{uuid.uuid4().hex[:8]}"
    components = [
        {
            "id": "root",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["chart_col"],
        },
        {
            "id": "chart_col",
            "component": "MaterialColumn",
            "justify": "start",
            "align": "stretch",
            "style": {"gap": "8px"},
            "children": ["chart_title", "sales_chart"],
        },
        # Gemini Enterprise ignores Vega-Lite's internal title, so place a MaterialText above it
        {
            "id": "chart_title",
            "component": "MaterialText",
            "text": "Quarterly Product Revenue ($K)",
            "usageHint": "subtitle1",
        },
        {
            "id": "sales_chart",
            "component": "VegaChart",
            "spec": {"path": "/spec"},  # Binds to updateDataModel path="/spec"
            "height": 320,
        },
    ]

    vega_lite_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {
            "values": [
                {"product": "PixelBook Pro", "revenue_k": 540},
                {"product": "Pixel Buds Studio", "revenue_k": 310},
                {"product": "Nest Hub Max", "revenue_k": 420},
            ]
        },
        "mark": {"type": "bar", "cornerRadiusEnd": 4, "tooltip": True},
        "encoding": {
            "x": {"field": "product", "type": "nominal", "title": "Product"},
            "y": {"field": "revenue_k", "type": "quantitative", "title": "Revenue ($K)"},
            "color": {"field": "product", "type": "nominal", "legend": None},
        },
    }
    return build_surface(surface_id, components, data_model_spec=vega_lite_spec)


# ===========================================================================
# EXAMPLE 6: Canvas (Right-Hand Side Panel Drawer)
# ===========================================================================

def build_canvas_example() -> list[types.Part]:
    """Side-panel Canvas with launcher chip and single MaterialColumn wrapper."""
    surface_id = f"canvas_{uuid.uuid4().hex[:8]}"
    components = [
        {
            "id": "root",
            "component": "Canvas",
            "cardTitle": "Product Catalog",  # <= 20 chars so tab header doesn't truncate
            "cardDescription": "3 products · Interactive side-panel view",
            "cardIcon": "table_chart",
            "autoOpen": False,               # Renders launcher chip in chat; user clicks to open drawer
            # CRITICAL: Canvas must have ONLY ONE child (a single MaterialColumn)
            # to avoid the 825px equal-share vertical flex-stretch bug!
            "children": ["canvas_main_col"],
        },
        {
            "id": "canvas_main_col",
            "component": "MaterialColumn",
            "justify": "start",
            "align": "stretch",
            "style": {"padding": "16px 20px", "gap": "16px"},
            "children": ["canvas_header_row", "canvas_summary_card"],
        },
        {
            "id": "canvas_header_row",
            "component": "MaterialRow",
            "justify": "spaceBetween",
            "align": "center",
            "children": ["canvas_title", "canvas_export_btn"],
        },
        {
            "id": "canvas_title",
            "component": "MaterialText",
            "text": "Executive Product Summary",
            "usageHint": "h4",
        },
        {
            "id": "canvas_export_btn",
            "component": "MaterialButton",
            "label": "Approve Catalog",
            "variant": "raised",
            "color": "primary",
            "action": {
                "event": {
                    "name": "approve_request",
                    "context": {"request_id": "CATALOG-2026", "amount": "$1,727"},
                }
            },
        },
        {
            "id": "canvas_summary_card",
            "component": "MaterialCard",
            "appearance": "outlined",
            "children": ["canvas_card_text"],
        },
        {
            "id": "canvas_card_text",
            "component": "MaterialText",
            "text": "This side-panel **Canvas** keeps dense tables, charts, and multi-section workflows out of the narrow chat column.",
            "usageHint": "body1",
        },
    ]
    return build_surface(surface_id, components)


# ===========================================================================
# ADK Tool & Callbacks Wiring All 6 Examples
# ===========================================================================

BUILDERS = {
    "card": build_material_card_example,
    "button": build_material_button_example,
    "row": build_material_row_example,
    "table": build_rich_table_example,
    "chart": build_vega_chart_example,
    "canvas": build_canvas_example,
}


def show_component_demo(component_type: str, tool_context: ToolContext) -> dict[str, str]:
    """Render one of the 6 A2UI component examples.

    Args:
        component_type: One of 'card', 'button', 'row', 'table', 'chart', or 'canvas'.
    """
    key = component_type.strip().lower()
    if key not in BUILDERS:
        key = "card"
    tool_context.state["pending_demo"] = key
    return {"status": "ok", "rendered_component": key}


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Handle inbound MaterialButton clicks and strip A2UI wire JSON from history."""
    contents = getattr(llm_request, "contents", None) or []

    if contents and contents[-1].role == "user":
        action = find_a2ui_action(contents[-1].parts)
        if action:
            name = action.get("name")
            ctx = action.get("context", {})
            if name == "approve_request":
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part.from_text(
                                text=f"Approved **{ctx.get('request_id')}** ({ctx.get('amount')})."
                            )
                        ],
                    )
                )
            if name == "view_details":
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part.from_text(
                                text=f"Showing details for **{ctx.get('product_name')}** ({ctx.get('price')})."
                            ),
                            *build_material_card_example(),
                        ],
                    )
                )

    for content in contents:
        if not content.parts:
            continue
        cleaned = [p for p in content.parts if decode_a2ui_part(p) is None]
        for p in cleaned:
            if getattr(p, "part_metadata", None) is not None:
                p.part_metadata = None
        content.parts = cleaned or [types.Part.from_text(text="(interactive UI action)")]

    return None


def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Attach the requested A2UI component demo to the model's final response."""
    if not llm_response.content or not llm_response.content.parts or llm_response.partial:
        return None
    if any(getattr(p, "function_call", None) for p in llm_response.content.parts):
        return None

    demo_key = callback_context.state.get("pending_demo")
    if isinstance(demo_key, str) and demo_key in BUILDERS:
        callback_context.state["pending_demo"] = None
        try:
            llm_response.content.parts.extend(BUILDERS[demo_key]())
        except Exception:
            pass
    return None


root_agent = Agent(
    name="a2ui_component_showcase_agent",
    model="gemini-3.8-flash",
    description="Showcases MaterialCard, MaterialButton, MaterialRow, RichTable, VegaChart, and Canvas.",
    instruction=(
        "You demonstrate the 6 core A2UI v0.9 components in Gemini Enterprise. "
        "Call `show_component_demo(component_type=...)` with one of: "
        "'card' (MaterialCard), 'button' (MaterialButton), 'row' (MaterialRow), "
        "'table' (Looker Studio RichTable), 'chart' (VegaChart), or 'canvas' (Canvas). "
        "Keep your text response to one short sentence."
    ),
    tools=[show_component_demo],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
