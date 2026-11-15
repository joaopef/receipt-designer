"""Render and install original native layouts without replacing existing work."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile
from ..core.models import Template
from ..library import LibraryRepository
from ..printing.jobs import ThermalProfile
from ..ui.print_render import prepare_print_job
from .routine import build_routine
from .practical import build_practical
from .playful import build_playful

MANIFEST = '.thermal-ideas-v1.json'


def all_templates():
    templates = build_routine() + build_practical() + build_playful()
    names = [template.name for template in templates]
    if len(names) != len(set(names)):
        raise ValueError('Collection layout names must be distinct.')
    return templates


def slug_of(template):
    return next(element.data['slug'] for element in template.elements
                if isinstance(element.data, dict)
                and element.data.get('collection') == 'thermal-ideas-v1'
                and isinstance(element.data.get('slug'), str)
                and element.data['slug'].strip())


def _write_manifest(path, data):
    descriptor, temporary = tempfile.mkstemp(prefix='.ideas-', suffix='.json', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install_collection(root: Path):
    """Return newly installed entries; existing, edited or trashed entries stay."""
    repo = LibraryRepository(Path(root))
    manifest = repo.root / MANIFEST
    installed = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    # Recover a save interrupted before its manifest update, including a layout
    # subsequently renamed by its owner. Never identify documents by title.
    for info in repo.list_layouts() + repo.list_trashed():
        try:
            existing = Template.from_dict(json.loads((info.folder / 'document.json').read_text(encoding='utf-8')))
            installed.setdefault(slug_of(existing), info.id)
        except (ValueError, FileNotFoundError, StopIteration):
            continue
    created = []
    for template in all_templates():
        slug = slug_of(template)
        if slug in installed:
            continue
        preview = prepare_print_job(template, ThermalProfile()).preview
        info = repo.save(template, preview=preview)
        installed[slug] = info.id
        _write_manifest(manifest, installed)
        created.append(info)
    return created


def export_collection(root: Path):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    exported = []
    for template in all_templates():
        slug = slug_of(template)
        document = root / (slug + '.json')
        document.write_text(json.dumps(template.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        job = prepare_print_job(template, ThermalProfile())
        job.preview.save(root / (slug + '.png'))
        exported.append({'name': template.name, 'slug': slug,
                         'height_mm': job.preview.height / 8,
                         'elements': len(template.elements), 'parts': len(job.parts)})
    (root / 'index.json').write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding='utf-8')
    return exported


def main():
    from PySide6.QtWidgets import QApplication
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library-dir', type=Path)
    parser.add_argument('--export-dir', type=Path)
    args = parser.parse_args()
    app = QApplication.instance() or QApplication([])
    if args.export_dir:
        print(json.dumps(export_collection(args.export_dir), ensure_ascii=False, indent=2))
    if args.library_dir:
        print(f'{len(install_collection(args.library_dir))} modelos novos guardados em {args.library_dir}')


if __name__ == '__main__':
    main()
