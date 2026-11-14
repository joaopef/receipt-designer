# receipt_designer/ui/persistence.py
"""
Template persistence: save / load / autosave / crash-recovery / recent-files
and portable asset-path helpers.

All public functions accept *mw* (the MainWindow instance) where needed;
this module must NOT import main_window_impl to avoid circular imports.
"""
from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtWidgets

from ..core.models import Element, Template
from ..core.utils import (
    normalize_path,
    dedupe_paths as dedupe_recent_files,
    make_asset_path_portable,
    resolve_asset_path,
)
from .items import create_item_from_element, SERIALIZABLE_ITEM_TYPES

if TYPE_CHECKING:
    from .host_protocols import PersistenceHost

# Debug flag for autosave/recovery troubleshooting
DEBUG_AUTOSAVE = False


# ---------------------------------------------------------------------------
# Pure utility helpers (no mw dependency)
# ---------------------------------------------------------------------------
# normalize_path, dedupe_recent_files, make_asset_path_portable,
# resolve_asset_path are imported from core.utils (single source of truth).


def make_elements_portable(elements: list, template_path: str) -> list:
    """
    Process element dicts to make asset paths portable (relative where possible).

    Args:
        elements: List of element dicts (from to_dict())
        template_path: The template file path being saved to

    Returns:
        New list of element dicts with portable paths
    """
    if not template_path:
        return elements

    result = []
    for elem_dict in elements:
        elem_copy = dict(elem_dict)
        if elem_copy.get("image_path"):
            elem_copy["image_path"] = make_asset_path_portable(
                elem_copy["image_path"], template_path
            )
        result.append(elem_copy)
    return result


def resolve_element_paths(elements: list, template_path: str) -> list:
    """
    Process element dicts to resolve relative asset paths to absolute.

    Args:
        elements: List of element dicts (from template JSON)
        template_path: The template file path being loaded from

    Returns:
        New list of element dicts with resolved absolute paths
    """
    if not template_path:
        return elements

    result = []
    for elem_dict in elements:
        elem_copy = dict(elem_dict)
        if elem_copy.get("image_path"):
            elem_copy["image_path"] = resolve_asset_path(
                elem_copy["image_path"], template_path
            )
        result.append(elem_copy)
    return result


# ---------------------------------------------------------------------------
# Helpers that need mw
# ---------------------------------------------------------------------------

def _collect_elements(mw: PersistenceHost) -> list[dict]:
    """Collect all serializable elements from the scene as dicts."""
    elements = []
    for it in mw.scene.items(QtCore.Qt.AscendingOrder):
        if isinstance(it, SERIALIZABLE_ITEM_TYPES):
            if hasattr(it, "elem"):
                elements.append(it.elem.to_dict())
            elif hasattr(it, "to_element"):
                elements.append(it.to_element().to_dict())
    return elements


def _build_scene_from_template(mw: PersistenceHost) -> None:
    """Clear the scene and populate it from mw.template.elements."""
    mw.scene.clear()
    for e in mw.template.elements:
        item = create_item_from_element(e)
        item.undo_stack = mw.undo_stack
        if hasattr(item, "_resolve_text"):
            item._main_window = mw
        mw.scene.addItem(item)

    mw.update_paper()
    mw._refresh_layers_safe()
    mw._refresh_variable_panel()


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

def save_template(mw: PersistenceHost) -> None:
    """Save template to file with improved error handling."""
    path, _ = QtWidgets.QFileDialog.getSaveFileName(
        mw, "Save Template", "", "Template JSON (*.json)"
    )
    if not path:
        return

    # Ensure .json extension
    if not path.lower().endswith('.json'):
        path += '.json'

    # Collect and serialize
    try:
        elements = _collect_elements(mw)
        elements = make_elements_portable(elements, path)

        import copy
        t = copy.deepcopy(mw.template)
        t.elements = [Element.from_dict(e) for e in elements]
    except Exception as e:
        QtWidgets.QMessageBox.critical(
            mw,
            "Serialization Error",
            f"Could not convert template to JSON format:\n\n"
            f"Error: {type(e).__name__}: {e}\n\n"
            "One or more elements may have invalid data."
        )
        return

    # Write file
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(t.to_dict(), f, indent=2)
    except PermissionError:
        QtWidgets.QMessageBox.critical(
            mw,
            "Permission Denied",
            f"You don't have permission to write to:\n{path}\n\n"
            "Try saving to a different location or check folder permissions."
        )
        return
    except OSError as e:
        QtWidgets.QMessageBox.critical(
            mw,
            "Save Error",
            f"Could not save file:\n{path}\n\n"
            f"Error: {e}\n\n"
            "Check that you have enough disk space and the path is valid."
        )
        return
    except Exception as e:
        QtWidgets.QMessageBox.critical(
            mw,
            "Unexpected Error",
            f"An unexpected error occurred while saving:\n{path}\n\n"
            f"Error: {type(e).__name__}: {e}"
        )
        return

    mw.statusBar().showMessage(f"Exportado: {path}", 3000)
    update_recent_files(mw, path)


def load_template(mw: PersistenceHost) -> None:
    """Import a JSON document into the editor, retaining library identity safety."""
    path, _ = QtWidgets.QFileDialog.getOpenFileName(mw, "Importar modelo", "", "Modelos (*.json *.receipt)")
    if path:
        load_template_path(mw, path)


def load_template_path(mw: PersistenceHost, path: str) -> None:
    from . import library_page
    if not library_page.guard(mw):
        return
    try:
        with open(path, "r", encoding="utf-8") as stream:
            data = json.load(stream)
        if isinstance(data.get("elements"), list):
            data["elements"] = resolve_element_paths(data["elements"], path)
        data.pop("_autosave_original_path", None)
        data.pop("_autosave_layout_id", None)
        template = Template.from_dict(data)
        library_page.install_template(mw, template, path=path, saved=False)
        # Imported files become a new library document on Save.
        update_recent_files(mw, path)
        mw.statusBar().showMessage(f"Importado: {path}", 3000)
    except Exception as exc:
        QtWidgets.QMessageBox.critical(mw, "Não foi possível importar", str(exc))


# ---------------------------------------------------------------------------
# Autosave / Crash recovery
# ---------------------------------------------------------------------------

def mark_unsaved(mw: PersistenceHost) -> None:
    """Mark that changes have been made (called when scene changes)."""
    if hasattr(mw, "_clean_document_signature"):
        from .library_page import signature
        mw._has_unsaved_changes = signature(mw) != mw._clean_document_signature
    else:
        mw._has_unsaved_changes = True


def has_unsaved_changes(mw: PersistenceHost) -> bool:
    """The flag is a cache; model-only mutations still need recovery."""
    dirty = mw._has_unsaved_changes
    if hasattr(mw, "_clean_document_signature"):
        from .library_page import signature
        dirty = dirty or signature(mw) != mw._clean_document_signature
    mw._has_unsaved_changes = dirty
    return dirty


def auto_save(mw: PersistenceHost) -> None:
    """Auto-save current template to temp location every 60 seconds."""
    if DEBUG_AUTOSAVE:
        print(f"[AUTOSAVE DEBUG] _auto_save called: _has_unsaved_changes={mw._has_unsaved_changes}, scene.items()={len(mw.scene.items())}")

    if not has_unsaved_changes(mw):
        if DEBUG_AUTOSAVE:
            print("[AUTOSAVE DEBUG] Skipping autosave: no unsaved changes")
        return

    temp_dir = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.TempLocation
    )
    if not temp_dir:
        print("Auto-save failed: No writable temp directory available")
        return

    autosave_path = os.path.join(temp_dir, "receipt_designer_autosave.json")

    # Serialize
    try:
        elements = _collect_elements(mw)

        if mw._current_file_path:
            elements = make_elements_portable(elements, mw._current_file_path)

        import copy
        t = copy.deepcopy(mw.template)
        t.elements = [Element.from_dict(e) for e in elements]
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        print(f"Auto-save serialization failed: {type(e).__name__}: {e}")
        return
    except Exception as e:
        print(f"Auto-save unexpected serialization error: {type(e).__name__}: {e}")
        return

    # Atomic write
    tmp_path = autosave_path + ".tmp"
    try:
        autosave_data = t.to_dict()
        if mw._current_file_path:
            autosave_data["_autosave_original_path"] = mw._current_file_path
        if getattr(mw, "current_layout_id", None):
            autosave_data["_autosave_layout_id"] = mw.current_layout_id
            autosave_data["_autosave_library_root"] = str(mw.library.root)

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(autosave_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, autosave_path)

        if DEBUG_AUTOSAVE:
            elem_count = len(elements)
            kinds = [e.get("kind", "?") for e in elements]
            print(f"[AUTOSAVE DEBUG] Autosave written successfully to: {autosave_path}")
            print(f"[AUTOSAVE DEBUG] Saved {elem_count} elements: {kinds}")

        mw.statusBar().showMessage("Auto-saved", 2000)

    except PermissionError:
        print(f"Auto-save permission denied: {autosave_path}")
    except OSError as e:
        print(f"Auto-save I/O error: {e}")
    except Exception as e:
        print(f"Auto-save unexpected write error: {type(e).__name__}: {e}")
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def load_crash_recovery(mw: PersistenceHost) -> None:
    """Check for auto-saved file on startup and offer to restore."""
    temp_dir = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.TempLocation
    )
    if not temp_dir:
        if DEBUG_AUTOSAVE:
            print("[AUTOSAVE DEBUG] No temp dir available")
        return

    autosave_path = os.path.join(temp_dir, "receipt_designer_autosave.json")

    if DEBUG_AUTOSAVE:
        print(f"[AUTOSAVE DEBUG] Checking for autosave at: {autosave_path}")
        print(f"[AUTOSAVE DEBUG] File exists: {os.path.exists(autosave_path)}")
        if os.path.exists(autosave_path):
            import datetime
            mtime = os.path.getmtime(autosave_path)
            mtime_str = datetime.datetime.fromtimestamp(mtime).isoformat()
            print(f"[AUTOSAVE DEBUG] File modified time: {mtime_str}")
            try:
                with open(autosave_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                elem_count = len(data.get("elements", []))
                kinds = [e.get("kind", "?") for e in data.get("elements", [])]
                print(f"[AUTOSAVE DEBUG] Element count: {elem_count}, kinds: {kinds}")
            except Exception as e:
                print(f"[AUTOSAVE DEBUG] Error reading autosave: {e}")

    if not os.path.exists(autosave_path):
        if DEBUG_AUTOSAVE:
            print("[AUTOSAVE DEBUG] No autosave file found, skipping recovery")
        return

    # Ask user if they want to restore
    reply = QtWidgets.QMessageBox.question(
        mw,
        "Recover Auto-saved Work?",
        "An auto-saved file was found. Would you like to restore it?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.Yes
    )

    if reply == QtWidgets.QMessageBox.Yes:
        recovery_succeeded = False
        try:
            with open(autosave_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Resolve relative asset paths using original template location
            original_path = data.pop("_autosave_original_path", None)
            if original_path and "elements" in data and isinstance(data["elements"], list):
                data["elements"] = resolve_element_paths(data["elements"], original_path)
                mw._current_file_path = original_path

            layout_id = data.pop("_autosave_layout_id", None)
            library_root = data.pop("_autosave_library_root", None)
            if library_root != str(mw.library.root):
                layout_id = None
            if layout_id:
                try:
                    mw.library.load(layout_id)
                except (FileNotFoundError, ValueError):
                    layout_id = None
            from . import library_page
            library_page.install_template(mw, Template.from_dict(data), layout_id=layout_id, path=original_path, saved=False)
            mw.statusBar().showMessage("Auto-saved work restored", 3000)
            recovery_succeeded = True

        except json.JSONDecodeError as e:
            bad_path = autosave_path + ".bad"
            try:
                os.replace(autosave_path, bad_path)
                if DEBUG_AUTOSAVE:
                    print(f"[AUTOSAVE DEBUG] Renamed corrupt autosave to: {bad_path}")
            except Exception:
                pass
            QtWidgets.QMessageBox.warning(
                mw,
                "Recovery Failed",
                f"Auto-save file is corrupted (invalid JSON):\n{e}\n\n"
                f"The file has been renamed to:\n{bad_path}"
            )
        except Exception as e:
            bad_path = autosave_path + ".bad"
            try:
                os.replace(autosave_path, bad_path)
                if DEBUG_AUTOSAVE:
                    print(f"[AUTOSAVE DEBUG] Renamed failed autosave to: {bad_path}")
            except Exception:
                pass
            QtWidgets.QMessageBox.warning(
                mw,
                "Recovery Failed",
                f"Could not restore auto-saved file:\n{e}\n\n"
                f"The file has been renamed to:\n{bad_path}"
            )

        if recovery_succeeded:
            delete_autosave_file(mw)
    else:
        # User declined - delete autosave file to avoid re-prompt
        delete_autosave_file(mw)


def delete_autosave_file(mw: PersistenceHost) -> None:
    """Delete the autosave file if it exists."""
    temp_dir = QtCore.QStandardPaths.writableLocation(
        QtCore.QStandardPaths.TempLocation
    )
    if not temp_dir:
        return

    autosave_path = os.path.join(temp_dir, "receipt_designer_autosave.json")
    try:
        if os.path.exists(autosave_path):
            os.remove(autosave_path)
            if DEBUG_AUTOSAVE:
                print(f"[AUTOSAVE DEBUG] Deleted autosave file: {autosave_path}")
    except Exception as e:
        if DEBUG_AUTOSAVE:
            print(f"[AUTOSAVE DEBUG] Failed to delete autosave file: {e}")


# ---------------------------------------------------------------------------
# Recent files
# ---------------------------------------------------------------------------

def remove_from_recent_by_normalized(mw: PersistenceHost, path_to_remove: str) -> None:
    """
    Remove a path from recent files, matching by normalized path.

    This handles cases where the stored path has different casing/slashes.
    """
    norm_to_remove = normalize_path(path_to_remove)
    recent = mw.settings.value("recent_files", [], type=list)

    updated = [p for p in recent if normalize_path(p) != norm_to_remove]

    if len(updated) != len(recent):
        mw.settings.setValue("recent_files", updated)
        refresh_recent_menu(mw)


def refresh_recent_menu(mw: PersistenceHost) -> None:
    """Refresh the Recent Files menu from settings."""
    if not hasattr(mw, 'recent_menu'):
        return

    mw.recent_menu.clear()

    recent = mw.settings.value("recent_files", [], type=list)

    if not recent:
        act_none = mw.recent_menu.addAction("(No recent files)")
        act_none.setEnabled(False)
        return

    # Show up to 10 recent files
    for path in recent[:10]:
        if not os.path.exists(path):
            continue

        filename = os.path.basename(path)
        act = mw.recent_menu.addAction(filename)
        act.setToolTip(path)
        act.triggered.connect(lambda checked, p=path: load_template_path(mw, p))

    mw.recent_menu.addSeparator()

    act_clear = mw.recent_menu.addAction("Clear Recent Files")
    act_clear.triggered.connect(lambda: clear_recent_files(mw))


def update_recent_files(mw: PersistenceHost, path: str) -> None:
    """Add a file to the recent files list with normalized deduplication."""
    if not path:
        return

    path = os.path.abspath(path)
    norm_path = normalize_path(path)

    recent = mw.settings.value("recent_files", [], type=list)

    # Remove any existing entry that normalizes to the same path
    recent = [p for p in recent if normalize_path(p) != norm_path]

    # Add to front
    recent.insert(0, path)

    # Dedupe and cap at 10
    recent = dedupe_recent_files(recent)[:10]

    mw.settings.setValue("recent_files", recent)
    refresh_recent_menu(mw)


def clear_recent_files(mw: PersistenceHost) -> None:
    """Clear the recent files list with confirmation."""
    reply = QtWidgets.QMessageBox.question(
        mw,
        "Clear Recent Files",
        "Are you sure you want to clear the recent files list?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
    )

    if reply == QtWidgets.QMessageBox.Yes:
        mw.settings.setValue("recent_files", [])
        refresh_recent_menu(mw)
        mw.statusBar().showMessage("Recent files cleared", 2000)


# ---------------------------------------------------------------------------
# Image asset copy
# ---------------------------------------------------------------------------

def copy_image_to_assets(mw: PersistenceHost, source_path: str) -> str | None:
    """
    Copy an image file into the template's assets/ folder.

    Args:
        source_path: Absolute path to the source image file

    Returns:
        Relative path to the copied file (e.g., "assets/logo.png"),
        or None if copy failed/cancelled.
    """
    import shutil

    template_path = mw._current_file_path
    if not template_path:
        return None

    try:
        template_dir = os.path.dirname(os.path.abspath(template_path))
        assets_dir = os.path.join(template_dir, "assets")

        os.makedirs(assets_dir, exist_ok=True)

        original_name = os.path.basename(source_path)
        base, ext = os.path.splitext(original_name)

        # Handle name collisions
        dest_name = original_name
        dest_path = os.path.join(assets_dir, dest_name)
        counter = 2
        while os.path.exists(dest_path):
            dest_name = f"{base}_{counter}{ext}"
            dest_path = os.path.join(assets_dir, dest_name)
            counter += 1

        shutil.copy2(source_path, dest_path)

        rel_path = os.path.relpath(dest_path, template_dir)
        return rel_path

    except Exception as e:
        QtWidgets.QMessageBox.critical(
            mw,
            "Copy Failed",
            f"Could not copy image to assets folder:\n\n{e}\n\n"
            "The original file will be linked instead."
        )
        return None
