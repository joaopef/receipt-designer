"""Portable local layout documents, independent of the GUI and Qt.

Each UUID folder contains the current document, metadata, optional PNG preview,
and owned image resources. Saves prepare a complete sibling folder before
publishing it; an unsuccessful replacement restores the previous folder.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import sys
import tempfile
import unicodedata
from uuid import UUID, uuid4

from PIL import Image

from .core.models import Template


@dataclass(frozen=True)
class LayoutInfo:
    id: str
    name: str
    folder: Path
    thumbnail: Path | None
    updated_at: str


def _search_text(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _validate_id(layout_id: str) -> str:
    try:
        if str(UUID(layout_id)) == layout_id:
            return layout_id
    except (ValueError, TypeError, AttributeError):
        pass
    raise ValueError("Layout ID must be a canonical UUID")


def _write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


class LibraryRepository:
    """Single-writer file repository; callers may move the whole root freely.

    ``save`` accepts absolute image paths for importing external resources.
    Relative image paths on update refer to the existing layout folder; new
    imports resolve relative paths from the working directory. Stored documents
    only reference files within their own ``assets`` directory. Missing or
    escaping resources raise errors rather than silently losing their content.
    An omitted preview on update preserves the existing thumbnail.
    Owned resources retain their filenames and remain available after removal
    from the current document, since the editor's undo stack may reference them.
    """

    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._recover_replacements()

    def _remove_managed_tree(self, folder: Path) -> None:
        """Remove a transaction tree, retrying Windows ReadOnly failures only.

        Never change ACLs or follow a resource outside the transaction folder.
        Other permission/storage failures remain errors for the caller to handle.
        """
        folder = Path(folder)
        managed_name = folder.name.startswith(".staging-") or re.fullmatch(
            r"\.backup-[0-9a-f-]{36}-[0-9a-f]{32}", folder.name)
        if folder.parent != self.root or not managed_name or folder.resolve() != folder:
            raise ValueError("Cleanup requires a managed transaction folder inside the library")

        def retry_readonly(function, path, error):
            target = Path(path)
            if (not isinstance(error, PermissionError) or os.name != "nt"
                    or target.resolve() != target or not target.is_relative_to(folder)):
                raise error
            target_stat = target.stat(follow_symlinks=False)
            if (stat.S_ISREG(target_stat.st_mode) and target_stat.st_nlink > 1
                    or not target_stat.st_file_attributes & stat.FILE_ATTRIBUTE_READONLY):
                raise error
            # On Windows chmod's writable bit clears ReadOnly; it does not edit
            # ACL permissions or alter unrelated Windows file attributes.
            os.chmod(target, stat.S_IWRITE)
            function(path)

        if sys.version_info >= (3, 12):
            shutil.rmtree(folder, onexc=retry_readonly)
        else:
            def onerror(function, path, exc_info):
                retry_readonly(function, path, exc_info[1])
            shutil.rmtree(folder, onerror=onerror)

    def _recover_replacements(self) -> None:
        # A process can stop between the two directory renames on Windows.
        # Only touch our complete, identifiable transaction backups.
        for backup in self.root.glob(".backup-*"):
            match = re.fullmatch(r"\.backup-([0-9a-f-]{36})-[0-9a-f]{32}", backup.name)
            if not match or not backup.is_dir() or backup.resolve() != backup:
                continue
            try:
                destination = self._folder(match.group(1))
                if destination.exists():
                    # A prior cleanup may have removed backup metadata before
                    # encountering a locked file. A valid published document is
                    # authoritative, even when its obsolete backup is incomplete.
                    self.load(destination.name)
                    self._remove_managed_tree(backup)
                    continue
                with (backup / "metadata.json").open(encoding="utf-8") as stream:
                    metadata = json.load(stream)
                with (backup / "document.json").open(encoding="utf-8") as stream:
                    document = json.load(stream)
                if (not isinstance(metadata, dict) or metadata.get("id") != destination.name
                        or not isinstance(document, dict)):
                    continue
                os.replace(backup, destination)
            except (ValueError, OSError, KeyError, TypeError):
                continue

    def _folder(self, layout_id: str, *, trashed: bool = False) -> Path:
        layout_id = _validate_id(layout_id)
        base = self.root / ".trash" if trashed else self.root
        folder = base / layout_id
        if base.resolve() != base or folder.resolve() != folder:
            raise ValueError("Layout folders must not be symbolic links")
        return folder

    @staticmethod
    def _metadata(folder: Path) -> dict:
        with (folder / "metadata.json").open(encoding="utf-8") as stream:
            metadata = json.load(stream)
        if (not isinstance(metadata, dict)
                or not isinstance(metadata.get("name"), str)
                or not isinstance(metadata.get("updated_at"), str)):
            raise ValueError("Invalid layout metadata")
        if metadata.get("id") != folder.name:
            raise ValueError("Layout metadata ID does not match its folder")
        return metadata

    def _info(self, folder: Path) -> LayoutInfo:
        metadata = self._metadata(folder)
        preview = folder / "preview.png"
        return LayoutInfo(id=folder.name, name=metadata["name"], folder=folder,
                          thumbnail=preview if preview.is_file() else None,
                          updated_at=metadata["updated_at"])

    def list_layouts(self, query: str = "") -> list[LayoutInfo]:
        return self._list_layouts(query, trashed=False)

    def list_trashed(self, query: str = "") -> list[LayoutInfo]:
        """List recoverable layouts, including those deleted in earlier runs."""
        return self._list_layouts(query, trashed=True)

    def _list_layouts(self, query: str, *, trashed: bool) -> list[LayoutInfo]:
        query = _search_text(query)
        layouts = []
        base = self.root / ".trash" if trashed else self.root
        if base.resolve() != base:
            raise ValueError("Library trash must not be a symbolic link")
        if not base.exists():
            return []
        for folder in base.iterdir():
            if folder.name.startswith(".") or not folder.is_dir():
                continue
            try:
                folder = self._folder(folder.name, trashed=trashed)
                info = self._info(folder)
            except (ValueError, KeyError, OSError, TypeError):
                # Foreign or damaged folders remain untouched and do not hide
                # the rest of the user's library.
                continue
            if query in _search_text(info.name):
                layouts.append(info)
        return sorted(layouts, key=lambda item: (item.updated_at, item.id), reverse=True)

    @staticmethod
    def _relative_resource(value: str, folder: Path) -> Path:
        windows_path = PureWindowsPath(value)
        portable = PurePosixPath(value.replace("\\", "/"))
        if (windows_path.drive or windows_path.root or portable.is_absolute()
                or ".." in portable.parts or not portable.parts
                or portable.parts[0] != "assets"):
            raise ValueError(f"Image resource must be inside assets/: {value}")
        resource = folder.joinpath(*portable.parts).resolve()
        if not resource.is_relative_to((folder / "assets").resolve()):
            raise ValueError(f"Image resource escapes layout: {value}")
        if not resource.is_relative_to(folder):
            raise ValueError(f"Image resource escapes layout: {value}")
        if not resource.is_file():
            raise FileNotFoundError(f"Missing image resource: {value}")
        return resource

    def load(self, layout_id: str) -> Template:
        folder = self._folder(layout_id)
        self._metadata(folder)
        with (folder / "document.json").open(encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, dict):
            raise ValueError("Layout document must be a JSON object")
        elements = data.get("elements", [])
        if not isinstance(elements, list) or not all(isinstance(element, dict) for element in elements):
            raise ValueError("Layout elements must be JSON objects")
        for element in elements:
            if element.get("kind") == "image" and element.get("image_path"):
                element["image_path"] = str(self._relative_resource(element["image_path"], folder))
        return Template.from_dict(data)

    def _copy_assets(self, data: dict, stage: Path, previous: Path | None) -> None:
        assets = stage / "assets"
        copied = {}
        previous_assets = previous / "assets" if previous is not None else None
        if previous_assets is not None and previous_assets.exists():
            # Keep assets referenced by deleted items in the editor's undo
            # history. The document still has one current version; resources
            # are owned by the layout rather than by a particular snapshot.
            for resource in [previous_assets, *previous_assets.rglob("*")]:
                if resource.is_symlink() or not resource.resolve().is_relative_to(previous):
                    raise ValueError(f"Owned image resource escapes layout: {resource}")
            shutil.copytree(previous_assets, assets)
            for resource in previous_assets.rglob("*"):
                if resource.is_file():
                    copied[resource.resolve()] = resource.relative_to(previous).as_posix()
        else:
            assets.mkdir()
        for element in data.get("elements", []):
            if element.get("kind") != "image" or not element.get("image_path"):
                continue
            value = element["image_path"]
            source = Path(value).expanduser()
            if not source.is_absolute():
                # Reject drive-relative Windows paths as well as traversal.
                portable = PurePosixPath(value.replace("\\", "/"))
                windows = PureWindowsPath(value)
                if ".." in portable.parts or windows.drive or windows.root:
                    raise ValueError(f"Invalid relative image resource: {value}")
                if previous is not None:
                    source = self._relative_resource(value, previous)
                else:
                    source = Path.cwd().joinpath(*portable.parts).resolve()
            source = source.resolve()
            if not source.is_file():
                raise FileNotFoundError(f"Missing image resource: {value}")
            if source not in copied:
                relative = f"assets/{uuid4().hex}{source.suffix}"
                shutil.copy2(source, stage / relative)
                copied[source] = relative
            element["image_path"] = copied[source]

    def save(self, template: Template, *, layout_id: str | None = None,
             preview: Image.Image | None = None) -> LayoutInfo:
        previous = None
        if layout_id is not None:
            previous = self._folder(layout_id)
            old_metadata = self._metadata(previous)
        else:
            layout_id = str(uuid4())
            old_metadata = {}
        destination = self._folder(layout_id)
        data = deepcopy(template.to_dict())
        now = datetime.now(timezone.utc).isoformat()
        metadata = {"id": layout_id, "name": template.name,
                    "created_at": old_metadata.get("created_at", now), "updated_at": now}
        stage = Path(tempfile.mkdtemp(prefix=".staging-", dir=self.root))
        backup = self.root / f".backup-{layout_id}-{uuid4().hex}"
        try:
            self._copy_assets(data, stage, previous)
            _write_json(stage / "document.json", data)
            _write_json(stage / "metadata.json", metadata)
            if preview is not None:
                preview.save(stage / "preview.png", format="PNG")
            elif previous is not None and (previous / "preview.png").is_file():
                shutil.copy2(previous / "preview.png", stage / "preview.png")
            if previous is not None:
                os.replace(destination, backup)
            try:
                os.replace(stage, destination)
            except BaseException:
                if backup.exists():
                    os.replace(backup, destination)
                raise
        finally:
            if stage.exists():
                self._remove_managed_tree(stage)
        if backup.exists():
            try:
                self._remove_managed_tree(backup)
            except OSError:
                # Publishing has committed. Report the saved document correctly;
                # a locked obsolete backup can be cleaned on the next opening.
                pass
        return self._info(destination)

    def duplicate(self, layout_id: str, new_name: str) -> LayoutInfo:
        template = self.load(layout_id)
        template.name = new_name
        preview_path = self._folder(layout_id) / "preview.png"
        if preview_path.is_file():
            with Image.open(preview_path) as preview:
                return self.save(template, preview=preview.copy())
        return self.save(template)

    def rename(self, layout_id: str, new_name: str) -> LayoutInfo:
        template = self.load(layout_id)
        template.name = new_name
        return self.save(template, layout_id=layout_id)

    def trash(self, layout_id: str) -> None:
        source = self._folder(layout_id)
        destination = self._folder(layout_id, trashed=True)
        if destination.exists():
            raise FileExistsError(f"Layout already exists in trash: {layout_id}")
        destination.parent.mkdir(exist_ok=True)
        os.replace(source, destination)

    def restore(self, layout_id: str) -> LayoutInfo:
        source = self._folder(layout_id, trashed=True)
        destination = self._folder(layout_id)
        if destination.exists():
            raise FileExistsError(f"Layout already exists: {layout_id}")
        os.replace(source, destination)
        return self._info(destination)
