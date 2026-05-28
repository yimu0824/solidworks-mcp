"""
SolidWorks COM Bridge - Core module for interacting with SolidWorks via COM API.
Supports: opening/closing SolidWorks, document operations, feature inspection, and export.
"""
import os
import sys
import time
from typing import Optional, Any
from dataclasses import dataclass, field

import pythoncom
import win32com.client
from win32com.client import CDispatch


# ── Constants ──────────────────────────────────────────────────────────────
# Document types
swDocNONE = 0
swDocPART = 1
swDocASSEMBLY = 2
swDocDRAWING = 3

DOC_TYPE_MAP = {1: "PART", 2: "ASSEMBLY", 3: "DRAWING", 0: "NONE"}
DOC_EXT_MAP = {
    ".sldprt": swDocPART,
    ".sldasm": swDocASSEMBLY,
    ".slddrw": swDocDRAWING,
}


class SolidWorksError(Exception):
    """Errors originating from SolidWorks COM bridge."""
    pass


class SolidWorksBridge:
    """High-level bridge to SolidWorks via COM automation."""

    def __init__(self):
        self._app: Optional[CDispatch] = None

    # ── Connection ────────────────────────────────────────────────────────

    @property
    def connected(self) -> bool:
        if self._app is None:
            return False
        try:
            self._app.RevisionNumber()
            return True
        except Exception:
            self._app = None
            return False

    def connect(self, visible: bool = True) -> CDispatch:
        """Connect to running SolidWorks or start a new instance."""
        if self.connected:
            return self._app

        pythoncom.CoInitialize()
        try:
            try:
                self._app = win32com.client.GetActiveObject("SldWorks.Application")
            except Exception:
                self._app = win32com.client.Dispatch("SldWorks.Application")

            self._app.Visible = visible
            time.sleep(0.5)  # allow SolidWorks to fully load
            return self._app
        except Exception as e:
            raise SolidWorksError(f"无法连接 SolidWorks: {e}") from e

    def disconnect(self):
        """Release the COM reference."""
        if self._app is not None:
            try:
                self._app = None
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    # ── Document Operations ────────────────────────────────────────────────

    def open_document(self, filepath: str, readonly: bool = False) -> CDispatch:
        """Open a SolidWorks document and return the ModelDoc2 object."""
        self.connect()
        if not os.path.isfile(filepath):
            raise SolidWorksError(f"文件不存在: {filepath}")

        ext = os.path.splitext(filepath)[1].lower()
        doc_type = DOC_EXT_MAP.get(ext, swDocNONE)
        if doc_type == swDocNONE:
            raise SolidWorksError(f"不支持的文件类型: {ext}")

        errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)

        doc = self._app.OpenDoc6(filepath, doc_type, 0 if readonly else 2, "", errors, warnings)

        if doc is None:
            err_code = errors.value
            raise SolidWorksError(f"打开文件失败 (错误码: {err_code}): {filepath}")
        return doc

    def get_active_document(self) -> Optional[CDispatch]:
        """Return the currently active document, or None."""
        if not self.connected:
            return None
        return self._app.ActiveDoc

    def close_document(self, filepath: str):
        """Close a document by path."""
        self.connect()
        self._app.CloseDoc(filepath)

    def close_all_documents(self):
        """Close all open documents."""
        self.connect()
        self._app.CloseAllDocuments(True)

    def save_document(self, doc: CDispatch):
        """Save the given document."""
        doc.Save()

    def save_document_as(self, doc: CDispatch, new_path: str):
        """Save document to a new path."""
        doc.SaveAs3(new_path, 0, 0)

    def quit_solidworks(self):
        """Exit the SolidWorks application."""
        if self._app is not None:
            try:
                self._app.ExitApp()
            except Exception:
                pass
            self._app = None

    # ── Document Info ─────────────────────────────────────────────────────

    def get_document_info(self, doc: CDispatch) -> dict:
        """Get basic information about a document."""
        doc_type = doc.GetType()
        info = {
            "title": doc.GetTitle(),
            "path": doc.GetPathName(),
            "type": DOC_TYPE_MAP.get(doc_type, f"UNKNOWN({doc_type})"),
            "type_id": doc_type,
        }
        return info

    def get_custom_properties(self, doc: CDispatch) -> dict:
        """Read all custom properties from a document."""
        props = {}
        try:
            custom_mgr = doc.Extension.CustomPropertyManager("")
            if custom_mgr is not None:
                names = custom_mgr.GetNames()
                if names:
                    for name in names:
                        try:
                            value, resolved, _ = custom_mgr.Get5(name, False, "", "")
                            props[name] = value
                        except Exception:
                            props[name] = "<无法读取>"
        except Exception as e:
            props["_error"] = str(e)
        return props

    def get_configuration_names(self, doc: CDispatch) -> list:
        """List all configuration names in the document."""
        names = []
        try:
            config = doc.GetConfigurationNames()
            if config:
                names = list(config)
        except Exception:
            pass
        return names

    def get_active_configuration_name(self, doc: CDispatch) -> str:
        """Get the name of the active configuration."""
        try:
            return doc.ConfigurationManager.ActiveConfiguration.Name
        except Exception:
            return "<未知>"

    # ── Features ──────────────────────────────────────────────────────────

    def get_features(self, doc: CDispatch) -> list[dict]:
        """List all features in the active document."""
        features = []
        try:
            feature = doc.FirstFeature()
            while feature is not None:
                features.append({
                    "name": feature.Name,
                    "type": feature.GetTypeName2(),
                })
                feature = feature.GetNextFeature()
        except Exception as e:
            features.append({"name": "_error", "type": str(e)})
        return features

    def get_feature_by_name(self, doc: CDispatch, name: str) -> Optional[CDispatch]:
        """Get a feature by its name."""
        try:
            return doc.FeatureByName(name)
        except Exception:
            return None

    # ── Bodies ────────────────────────────────────────────────────────────

    def get_bodies(self, doc: CDispatch) -> list[dict]:
        """List all solid bodies in the document."""
        bodies = []
        try:
            bodies_v = doc.GetBodies2(0, False)  # swBodyType_e.swSolidBody = 0
            if bodies_v:
                for body in bodies_v:
                    try:
                        bodies.append({
                            "name": body.Name,
                            "visible": body.Visible,
                        })
                    except Exception:
                        bodies.append({"name": "<未知>", "visible": None})
        except Exception as e:
            bodies.append({"name": "_error", "visible": str(e)})
        return bodies

    def get_body_count(self, doc: CDispatch) -> int:
        """Return the number of solid bodies."""
        try:
            return doc.GetBodyCount(False)
        except Exception:
            return -1

    # ── Mass Properties ───────────────────────────────────────────────────

    def get_mass_properties(self, doc: CDispatch) -> dict:
        """Get mass properties of the document."""
        try:
            mp = doc.Extension.CreateMassProperty()
            if mp is None:
                return {"error": "无法创建质量属性对象"}
            mass = mp.Mass
            volume = mp.Volume
            center = (mp.CenterOfMassX, mp.CenterOfMassY, mp.CenterOfMassZ)
            return {
                "mass_kg": round(mass, 6),
                "volume_m3": round(volume, 9),
                "center_of_mass_m": tuple(round(c, 9) for c in center),
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Export ────────────────────────────────────────────────────────────

    def export_to_step(self, doc: CDispatch, output_path: str) -> str:
        """Export the document to STEP AP242 format."""
        abs_path = os.path.abspath(output_path)
        ret = doc.Extension.SaveAs(abs_path, 0, 0, None, "", 0, 0)  # swSaveAsCurrentVersion
        if not ret:
            raise SolidWorksError(f"导出 STEP 失败: {abs_path}")
        return abs_path

    def export_to_iges(self, doc: CDispatch, output_path: str) -> str:
        """Export the document to IGES format."""
        abs_path = os.path.abspath(output_path)
        ret = doc.Extension.SaveAs(abs_path, 0, 0, None, "", 0, 0)
        if not ret:
            raise SolidWorksError(f"导出 IGES 失败: {abs_path}")
        return abs_path

    def export_to_stl(self, doc: CDispatch, output_path: str, quality: str = "fine") -> str:
        """Export the document to STL format."""
        abs_path = os.path.abspath(output_path)
        # STL export options
        opts = win32com.client.Dispatch("SldWorks.StlExportOptions")
        if quality == "coarse":
            opts.Quality = 0
        elif quality == "fine":
            opts.Quality = 1
        else:
            opts.Quality = 1
        opts.OutputFileFormat = 0  # Binary
        ret = doc.Extension.SaveAs(abs_path, 0, 0, None, "", 0, 0, opts)
        if not ret:
            raise SolidWorksError(f"导出 STL 失败: {abs_path}")
        return abs_path

    # ── File Reading (without opening SolidWorks) ──────────────────────────

    @staticmethod
    def read_sw_file_info(filepath: str) -> dict:
        """Read basic info from a SolidWorks file using the SwDocumentMgr.
        This does NOT require SolidWorks GUI to be running.
        Requires: SolidWorks Document Manager DLL (swdocumentmgr.dll)
        """
        if not os.path.isfile(filepath):
            raise SolidWorksError(f"文件不存在: {filepath}")
        info = {
            "path": os.path.abspath(filepath),
            "filename": os.path.basename(filepath),
            "size_bytes": os.path.getsize(filepath),
            "extension": os.path.splitext(filepath)[1].lower(),
        }
        # Try Document Manager for deeper info
        try:
            dm = win32com.client.Dispatch("SwDocumentMgr.SwDMApplication")
            dm_cls = dm.GetDocument(filepath, 0)
            if dm_cls:
                info["dm_title"] = dm_cls.Title
                info["dm_type"] = dm_cls.GetType()
        except Exception:
            info["dm_note"] = "Document Manager 不可用 (需要安装 SolidWorks)"
        return info

    # ── Sketch / Selection / Rebuild ──────────────────────────────────────

    def rebuild(self, doc: CDispatch):
        """Force rebuild of the document."""
        doc.ForceRebuild3(True)

    def clear_selection(self, doc: CDispatch):
        """Clear the current selection."""
        doc.ClearSelection2(True)


# Singleton convenience
_bridge_instance: Optional[SolidWorksBridge] = None


def get_bridge() -> SolidWorksBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = SolidWorksBridge()
    return _bridge_instance
