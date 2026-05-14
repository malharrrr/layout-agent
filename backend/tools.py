import json
import copy

TOOLS = [
    {
        "name": "list_nodes",
        "description": "List all nodes on the canvas with their id, name, type, and current position/size. Call this first to understand the layout before making changes.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_node_info",
        "description": "Get full details of a specific node including position, size, style, and content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The id of the node to inspect"
                }
            },
            "required": ["node_id"]
        }
    },
    {
        "name": "move_node",
        "description": "Move a node to a new absolute pixel position. Automatically recomputes nx/ny normalized values.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "The id of the node to move"},
                "x": {"type": "number", "description": "New x position in pixels"},
                "y": {"type": "number", "description": "New y position in pixels"}
            },
            "required": ["node_id", "x", "y"]
        }
    },
    {
        "name": "resize_node",
        "description": "Resize a node to new pixel dimensions. Automatically recomputes nw/nh normalized values. For text nodes, optionally update fontSize.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "The id of the node to resize"},
                "width": {"type": "number", "description": "New width in pixels"},
                "height": {"type": "number", "description": "New height in pixels"},
                "font_size": {"type": "number", "description": "Optional: new font size in pixels (for text nodes only)"}
            },
            "required": ["node_id", "width", "height"]
        }
    },
    {
        "name": "scale_node",
        "description": "Scale a node by a factor (e.g. 1.5 = 50% larger, 0.8 = 20% smaller). Keeps the node centered. Updates position and size.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "The id of the node to scale"},
                "factor": {"type": "number", "description": "Scale factor. >1 makes larger, <1 makes smaller."},
                "anchor": {"type": "string", "enum": ["center", "top-left"], "description": "Anchor point for scaling. Default: center"}
            },
            "required": ["node_id", "factor"]
        }
    },
    {
        "name": "change_aspect_ratio",
        "description": "Change the artboard aspect ratio/dimensions (e.g. '9:16' for Stories, '1:1' for square, '16:9' for landscape). Rescales all node positions proportionally. Width is kept at 1080px by default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ratio": {
                    "type": "string",
                    "description": "Aspect ratio string like '9:16', '1:1', '16:9', '4:5'"
                }
            },
            "required": ["ratio"]
        }
    },
    {
        "name": "set_node_style",
        "description": "Update visual style properties of a node (color, fontSize, fontWeight, borderRadius, fill color, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string"},
                "style_path": {
                    "type": "string",
                    "description": "Dot-path into style object e.g. 'visual.fontSize', 'visual.color.value', 'visual.fill.value'"
                },
                "value": {"description": "New value to set"}
            },
            "required": ["node_id", "style_path", "value"]
        }
    },
    {
        "name": "batch_move",
        "description": "Move multiple nodes at once. Useful for moving grouped elements like an offer badge (circle + text) together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "moves": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "node_id": {"type": "string"},
                            "x": {"type": "number"},
                            "y": {"type": "number"}
                        },
                        "required": ["node_id", "x", "y"]
                    },
                    "description": "List of {node_id, x, y} objects"
                }
            },
            "required": ["moves"]
        }
    }
]

def execute_tool(tool_name: str, tool_input: dict, layout: dict) -> dict:
    try:
        if tool_name == "list_nodes":
            return _list_nodes(layout)
        elif tool_name == "get_node_info":
            return _get_node_info(tool_input["node_id"], layout)
        elif tool_name == "move_node":
            return _move_node(tool_input["node_id"], tool_input["x"], tool_input["y"], layout)
        elif tool_name == "resize_node":
            return _resize_node(
                tool_input["node_id"],
                tool_input["width"],
                tool_input["height"],
                tool_input.get("font_size"),
                layout
            )
        elif tool_name == "scale_node":
            return _scale_node(
                tool_input["node_id"],
                tool_input["factor"],
                tool_input.get("anchor", "center"),
                layout
            )
        elif tool_name == "change_aspect_ratio":
            return _change_aspect_ratio(tool_input["ratio"], layout)
        elif tool_name == "set_node_style":
            return _set_node_style(tool_input["node_id"], tool_input["style_path"], tool_input["value"], layout)
        elif tool_name == "batch_move":
            return _batch_move(tool_input["moves"], layout)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        return {"error": str(e)}

def _get_artboard(layout):
    root_id = layout["rootNodes"][0]
    return layout["nodes"][root_id]

def _sync_normalized(node, artboard_w, artboard_h):
    node["nx"] = node["x"] / artboard_w
    node["ny"] = node["y"] / artboard_h
    node["nw"] = node["width"] / artboard_w
    node["nh"] = node["height"] / artboard_h
    if "fontSizeRatio" in node and "style" in node:
        fs = node.get("style", {}).get("visual", {}).get("fontSize")
        if fs:
            node["fontSizeRatio"] = fs / artboard_h

def _list_nodes(layout):
    artboard = _get_artboard(layout)
    rows = []
    for nid, node in layout["nodes"].items():
        if node["type"] == "artboard":
            continue
        rows.append({
            "id": nid,
            "name": node.get("name", ""),
            "type": node.get("type", ""),
            "x": round(node.get("x", 0), 1),
            "y": round(node.get("y", 0), 1),
            "width": round(node.get("width", 0), 1),
            "height": round(node.get("height", 0), 1),
            "content": node.get("data", {}).get("content", "") if node["type"] == "text" else None
        })
    return {
        "artboard_size": f"{artboard['width']}x{artboard['height']}",
        "nodes": rows
    }

def _get_node_info(node_id, layout):
    if node_id not in layout["nodes"]:
        return {"error": f"Node {node_id} not found"}
    return {"node": layout["nodes"][node_id]}

def _move_node(node_id, x, y, layout):
    if node_id not in layout["nodes"]:
        return {"error": f"Node {node_id} not found"}
    artboard = _get_artboard(layout)
    node = layout["nodes"][node_id]
    node["x"] = x
    node["y"] = y
    _sync_normalized(node, artboard["width"], artboard["height"])
    return {"success": True, "node_id": node_id, "x": x, "y": y}

def _resize_node(node_id, width, height, font_size, layout):
    if node_id not in layout["nodes"]:
        return {"error": f"Node {node_id} not found"}
    artboard = _get_artboard(layout)
    node = layout["nodes"][node_id]
    node["width"] = width
    node["height"] = height
    if font_size is not None and "style" in node:
        node["style"]["visual"]["fontSize"] = font_size
    _sync_normalized(node, artboard["width"], artboard["height"])
    return {"success": True, "node_id": node_id, "width": width, "height": height}

def _scale_node(node_id, factor, anchor, layout):
    if node_id not in layout["nodes"]:
        return {"error": f"Node {node_id} not found"}
    artboard = _get_artboard(layout)
    node = layout["nodes"][node_id]
    old_w, old_h = node["width"], node["height"]
    new_w = old_w * factor
    new_h = old_h * factor
    if anchor == "center":
        cx = node["x"] + old_w / 2
        cy = node["y"] + old_h / 2
        node["x"] = cx - new_w / 2
        node["y"] = cy - new_h / 2
    node["width"] = new_w
    node["height"] = new_h
    if "style" in node and "fontSize" in node.get("style", {}).get("visual", {}):
        node["style"]["visual"]["fontSize"] = round(node["style"]["visual"]["fontSize"] * factor, 1)
    _sync_normalized(node, artboard["width"], artboard["height"])
    return {"success": True, "node_id": node_id, "new_width": new_w, "new_height": new_h}

def _change_aspect_ratio(ratio, layout):
    parts = ratio.strip().split(":")
    if len(parts) != 2:
        return {"error": "Invalid ratio format. Use W:H e.g. '9:16'"}
    rw, rh = float(parts[0]), float(parts[1])
    artboard = _get_artboard(layout)
    old_w = artboard["width"]
    old_h = artboard["height"]
    new_w = 1080.0
    new_h = round(new_w * rh / rw, 2)
    scale_x = new_w / old_w
    scale_y = new_h / old_h
    artboard["width"] = new_w
    artboard["height"] = new_h
    
    artboard["data"]["preset"] = f"custom-{ratio.replace(':', 'x')}"
    
    for nid, node in layout["nodes"].items():
        if node.get("parentId") == artboard["id"] and node["type"] != "artboard":
            node["x"] = node["x"] * scale_x
            node["y"] = node["y"] * scale_y
            node["width"] = node["width"] * scale_x
            node["height"] = node["height"] * scale_y
            if "style" in node and "fontSize" in node.get("style", {}).get("visual", {}):
                node["style"]["visual"]["fontSize"] = round(
                    node["style"]["visual"]["fontSize"] * min(scale_x, scale_y), 1
                )
            _sync_normalized(node, new_w, new_h)
    return {"success": True, "old_size": f"{old_w}x{old_h}", "new_size": f"{new_w}x{new_h}"}

def _set_node_style(node_id, style_path, value, layout):
    if node_id not in layout["nodes"]:
        return {"error": f"Node {node_id} not found"}
    node = layout["nodes"][node_id]
    keys = style_path.split(".")
    obj = node.get("style", {})
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = value
    return {"success": True, "node_id": node_id, "style_path": style_path, "value": value}

def _batch_move(moves, layout):
    results = []
    for m in moves:
        r = _move_node(m["node_id"], m["x"], m["y"], layout)
        results.append(r)
    return {"success": True, "results": results}