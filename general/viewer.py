import json
import re
from datetime import datetime, timezone
from pathlib import Path

from general.template_assets import ensure_output_assets, render_template


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def path_time_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace(
        '+00:00', 'Z')


def natural_key(value: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', value)]


def count_region_steps(output_dir: Path) -> int:
    regions_dir = output_dir / 'regions'
    if not regions_dir.is_dir():
        return 0
    return len([path for path in regions_dir.iterdir() if path.suffix == '.png'])


DATASET_NAMES = {
    'test01': 'Exponentiation loop with parity branches',
    'test02': 'Long loop value-table stress case',
    'test03': 'Nested branch loop for SSA placement',
    'test04': 'Flag-driven cyclic control flow',
    'test05': 'Synthetic SSA merge graph',
    'test06': 'Synthetic nested region graph',
    'test07': 'Synthetic reverse-region graph',
    'test08': 'Synthetic gen/kill loop graph',
    'test09': 'Nested loop symbolic dump demo',
    'test10': 'Acyclic merge and region-summary demo',
}


def dataset_name(dataset_id: str, input_path: str) -> str:
    if dataset_id in DATASET_NAMES:
        return DATASET_NAMES[dataset_id]
    if input_path:
        return Path(input_path).stem.replace('_', ' ').replace('-', ' ').title()
    return dataset_id.replace('_', ' ').replace('-', ' ').title()


def write_dataset_metadata(output_dir: str, input_path: str, block_name: str, blocks_count: int,
                           sections_count: int, processed_at: str) -> None:
    output_path = Path(output_dir)
    dataset_id = output_path.name or output_path.parent.name
    name = dataset_name(dataset_id, input_path)
    metadata = {
        'id': dataset_id,
        'name': name,
        'label': f'{dataset_id}: {name}',
        'source': input_path if input_path else 'synthetic blocks / edges',
        'block_name': block_name,
        'blocks': blocks_count,
        'sections': sections_count,
        'region_steps': count_region_steps(output_path),
        'processed_at': processed_at,
        'dumped_at': now_iso(),
        'report': 'index.html',
    }
    (output_path / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    write_unified_viewer(output_path.parent)


def collect_datasets(output_root: Path) -> list:
    datasets = []
    for report_path in sorted(output_root.glob('*/index.html'), key=lambda path: natural_key(path.parent.name)):
        output_dir = report_path.parent
        metadata_path = output_dir / 'metadata.json'
        metadata = {}
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                metadata = {}
        datasets.append({
            'id': metadata.get('id', output_dir.name),
            'name': metadata.get('name') or dataset_name(output_dir.name, metadata.get('source', '')),
            'label': metadata.get('label') or f'{output_dir.name}: {dataset_name(output_dir.name, metadata.get("source", ""))}',
            'source': metadata.get('source', 'not tracked'),
            'href': f'{output_dir.name}/index.html',
            'dumped_at': metadata.get('dumped_at') or path_time_iso(report_path),
            'processed_at': metadata.get('processed_at'),
            'blocks': metadata.get('blocks'),
            'sections': metadata.get('sections'),
            'region_steps': metadata.get('region_steps', count_region_steps(output_dir)),
        })
    return datasets


def write_unified_viewer(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    ensure_output_assets(output_root)
    datasets = collect_datasets(output_root)
    manifest = {'generated_at': now_iso(), 'datasets': datasets}
    (output_root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    datasets_json = json.dumps(datasets)
    (output_root / 'index.html').write_text(
        render_template('viewer.html', datasets_json=datasets_json),
        encoding='utf-8'
    )
