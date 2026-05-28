"""
SolidWorks MCP Server
Exposes SolidWorks operations as MCP tools and resources for Codex.
"""
import os
import sys
import json
import asyncio
from typing import Any

# Ensure the bridge module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from sw_bridge import SolidWorksBridge, SolidWorksError, get_bridge

# ── Server Setup ───────────────────────────────────────────────────────────
server = Server("solidworks-mcp")
bridge: SolidWorksBridge = None


def ensure_bridge():
    global bridge
    if bridge is None:
        bridge = get_bridge()
    return bridge


# ── Tools ──────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="sw_connect",
            description="连接到 SolidWorks（如果未运行则启动新实例）。可设置是否显示窗口。",
            inputSchema={
                "type": "object",
                "properties": {
                    "visible": {
                        "type": "boolean",
                        "description": "是否显示 SolidWorks 窗口（默认 true）",
                        "default": True,
                    }
                },
            },
        ),
        Tool(
            name="sw_open_document",
            description="打开 SolidWorks 文档（.sldprt / .sldasm / .slddrw）。返回文档基本信息。",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "SolidWorks 文件的完整路径",
                    },
                    "readonly": {
                        "type": "boolean",
                        "description": "是否以只读模式打开（默认 false）",
                        "default": False,
                    },
                },
                "required": ["filepath"],
            },
        ),
        Tool(
            name="sw_get_document_info",
            description="获取当前活动文档的详细信息：名称、路径、类型、配置、自定义属性、质量属性。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sw_list_features",
            description="列出当前活动文档的所有特征。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sw_list_bodies",
            description="列出当前活动文档的所有实体（solid bodies）。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sw_get_mass_properties",
            description="获取当前活动文档的质量属性（质量、体积、重心）。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sw_get_custom_properties",
            description="获取当前活动文档的所有自定义属性。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sw_export",
            description="将当前文档导出为 STEP / IGES / STL 格式。",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "导出文件的目标路径",
                    },
                    "format": {
                        "type": "string",
                        "description": "导出格式: step, iges, stl",
                        "enum": ["step", "iges", "stl"],
                    },
                    "quality": {
                        "type": "string",
                        "description": "STL 质量 (coarse / fine), 仅对 stl 格式有效",
                        "enum": ["coarse", "fine"],
                        "default": "fine",
                    },
                },
                "required": ["output_path", "format"],
            },
        ),
        Tool(
            name="sw_save",
            description="保存当前活动文档。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sw_save_as",
            description="将当前文档另存为指定路径。",
            inputSchema={
                "type": "object",
                "properties": {
                    "new_path": {
                        "type": "string",
                        "description": "另存为的目标路径",
                    },
                },
                "required": ["new_path"],
            },
        ),
        Tool(
            name="sw_close_document",
            description="关闭指定路径的文档或当前活动文档。",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "要关闭的文档路径（留空则关闭活动文档）",
                    },
                },
            },
        ),
        Tool(
            name="sw_rebuild",
            description="强制重建当前文档。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sw_read_file_info",
            description="读取 SolidWorks 文件的基本信息（无需启动 SolidWorks GUI）。",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "SolidWorks 文件路径",
                    },
                },
                "required": ["filepath"],
            },
        ),
        Tool(
            name="sw_quit",
            description="退出 SolidWorks 应用程序。",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    b = ensure_bridge()
    try:
        if name == "sw_connect":
            visible = arguments.get("visible", True)
            b.connect(visible=visible)
            return [TextContent(type="text", text="✅ 已连接到 SolidWorks")]

        elif name == "sw_open_document":
            filepath = arguments["filepath"]
            readonly = arguments.get("readonly", False)
            doc = b.open_document(filepath, readonly=readonly)
            info = b.get_document_info(doc)
            result = {
                "status": "opened",
                "document": info,
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

        elif name == "sw_get_document_info":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            info = b.get_document_info(doc)
            info["active_configuration"] = b.get_active_configuration_name(doc)
            info["configurations"] = b.get_configuration_names(doc)
            info["custom_properties"] = b.get_custom_properties(doc)
            info["body_count"] = b.get_body_count(doc)
            try:
                mp = b.get_mass_properties(doc)
                if "error" not in mp:
                    info["mass_properties"] = mp
            except Exception:
                pass
            return [TextContent(type="text", text=json.dumps(info, indent=2, ensure_ascii=False))]

        elif name == "sw_list_features":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            features = b.get_features(doc)
            return [TextContent(type="text", text=json.dumps(features, indent=2, ensure_ascii=False))]

        elif name == "sw_list_bodies":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            bodies = b.get_bodies(doc)
            return [TextContent(type="text", text=json.dumps(bodies, indent=2, ensure_ascii=False))]

        elif name == "sw_get_mass_properties":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            mp = b.get_mass_properties(doc)
            return [TextContent(type="text", text=json.dumps(mp, indent=2, ensure_ascii=False))]

        elif name == "sw_get_custom_properties":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            props = b.get_custom_properties(doc)
            return [TextContent(type="text", text=json.dumps(props, indent=2, ensure_ascii=False))]

        elif name == "sw_export":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            fmt = arguments["format"]
            output = arguments["output_path"]
            if fmt == "step":
                result_path = b.export_to_step(doc, output)
            elif fmt == "iges":
                result_path = b.export_to_iges(doc, output)
            elif fmt == "stl":
                quality = arguments.get("quality", "fine")
                result_path = b.export_to_stl(doc, output, quality)
            return [TextContent(type="text", text=f"✅ 已导出: {result_path}")]

        elif name == "sw_save":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            b.save_document(doc)
            return [TextContent(type="text", text="✅ 文档已保存")]

        elif name == "sw_save_as":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            new_path = arguments["new_path"]
            b.save_document_as(doc, new_path)
            return [TextContent(type="text", text=f"✅ 已另存为: {new_path}")]

        elif name == "sw_close_document":
            filepath = arguments.get("filepath")
            if filepath:
                b.close_document(filepath)
            else:
                doc = b.get_active_document()
                if doc is None:
                    return [TextContent(type="text", text="⚠️ 没有活动文档")]
                filepath = b.get_document_info(doc)["path"]
                b.close_document(filepath)
            return [TextContent(type="text", text=f"✅ 文档已关闭: {filepath}")]

        elif name == "sw_rebuild":
            doc = b.get_active_document()
            if doc is None:
                return [TextContent(type="text", text="⚠️ 没有活动文档")]
            b.rebuild(doc)
            return [TextContent(type="text", text="✅ 文档已重建")]

        elif name == "sw_read_file_info":
            filepath = arguments["filepath"]
            info = b.read_sw_file_info(filepath)
            return [TextContent(type="text", text=json.dumps(info, indent=2, ensure_ascii=False))]

        elif name == "sw_quit":
            b.quit_solidworks()
            return [TextContent(type="text", text="✅ SolidWorks 已退出")]

        else:
            return [TextContent(type="text", text=f"❌ 未知工具: {name}")]

    except SolidWorksError as e:
        return [TextContent(type="text", text=f"❌ SolidWorks 错误: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"❌ 意外错误: {e}")]


# ── Resources ──────────────────────────────────────────────────────────────

@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="solidworks://status",
            name="SolidWorks 状态",
            description="当前 SolidWorks 连接状态和活动文档信息",
            mimeType="application/json",
        ),
    ]


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    return [
        ResourceTemplate(
            uriTemplate="solidworks://file/{path}",
            name="SolidWorks 文件信息",
            description="读取指定 SolidWorks 文件的基本信息（无需启动 GUI）",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    b = ensure_bridge()
    if uri == "solidworks://status":
        status = {
            "connected": b.connected,
            "active_document": None,
        }
        if b.connected:
            doc = b.get_active_document()
            if doc:
                status["active_document"] = b.get_document_info(doc)
        return json.dumps(status, indent=2, ensure_ascii=False)

    elif uri.startswith("solidworks://file/"):
        filepath = uri.replace("solidworks://file/", "")
        info = b.read_sw_file_info(filepath)
        return json.dumps(info, indent=2, ensure_ascii=False)

    else:
        return json.dumps({"error": f"未知资源: {uri}"})


# ── Entry Point ────────────────────────────────────────────────────────────

def main():
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
