import json
import re
from datetime import datetime, timezone
from pathlib import Path


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


def write_dataset_metadata(output_dir: str, input_path: str, block_name: str, blocks_count: int,
                           sections_count: int, processed_at: str) -> None:
    output_path = Path(output_dir)
    dataset_id = output_path.name or output_path.parent.name
    metadata = {
        'id': dataset_id,
        'label': dataset_id,
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
            'label': metadata.get('label', output_dir.name),
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
    datasets = collect_datasets(output_root)
    manifest = {'generated_at': now_iso(), 'datasets': datasets}
    (output_root / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    datasets_json = json.dumps(datasets)
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" sizes="32x32" href="coding.png">
<link rel="stylesheet" href="styles.css">
<title>Compiler Analysis Dumps</title>
</head>
<body class="viewer-body">
<div class="viewer-shell">
<header class="viewer-topbar">
<div class="viewer-title">
<p class="eyebrow">Dump viewer</p>
<h1>Compiler analysis dumps</h1>
</div>
<div class="viewer-controls">
<label class="dataset-picker">
<span>Dataset</span>
<select id="datasetSelect"></select>
</label>
<div class="theme-toggle" aria-label="Theme">
<button type="button" data-theme-choice="light">Light</button>
<button type="button" data-theme-choice="dark">Dark</button>
<button type="button" data-theme-choice="system">System</button>
</div>
</div>
<dl class="dataset-metadata">
<div><dt>Last dumped</dt><dd id="metaDumped">-</dd></div>
<div><dt>Last processed</dt><dd id="metaProcessed">-</dd></div>
<div><dt>Source</dt><dd id="metaSource">-</dd></div>
<div><dt>Blocks</dt><dd id="metaBlocks">-</dd></div>
<div><dt>Region steps</dt><dd id="metaRegions">-</dd></div>
</dl>
</header>
<main class="viewer-main">
<iframe id="datasetFrame" class="viewer-frame" title="Selected compiler analysis dump"></iframe>
</main>
</div>
<script>
const DATASETS = {datasets_json};
const themeKey = "compiler-analysis-theme";
const datasetKey = "compiler-analysis-dataset";
const datasetSelect = document.querySelector("#datasetSelect");
const datasetFrame = document.querySelector("#datasetFrame");
const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

function resolveTheme(mode) {{
    return mode === "dark" || (mode === "system" && mediaQuery.matches) ? "dark" : "light";
}}

function updateThemeButtons(mode) {{
    document.querySelectorAll("[data-theme-choice]").forEach((button) => {{
        button.setAttribute("aria-pressed", String(button.dataset.themeChoice === mode));
    }});
}}

function applyTheme(mode, store = true) {{
    const selectedMode = mode || "system";
    document.documentElement.dataset.theme = resolveTheme(selectedMode);
    document.documentElement.dataset.themeMode = selectedMode;
    updateThemeButtons(selectedMode);
    if (store) localStorage.setItem(themeKey, selectedMode);
    if (datasetFrame.contentWindow) {{
        datasetFrame.contentWindow.postMessage({{type: "compiler-theme", mode: selectedMode}}, "*");
    }}
}}

function formatTime(value) {{
    if (!value) return "not tracked";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString(undefined, {{dateStyle: "medium", timeStyle: "medium"}});
}}

function setText(id, value) {{
    document.querySelector(id).textContent = value ?? "-";
}}

function selectDataset(index) {{
    const dataset = DATASETS[index];
    if (!dataset) return;
    datasetSelect.value = String(index);
    datasetFrame.src = dataset.href;
    setText("#metaDumped", formatTime(dataset.dumped_at));
    setText("#metaProcessed", formatTime(dataset.processed_at));
    setText("#metaSource", dataset.source || "not tracked");
    setText("#metaBlocks", dataset.blocks);
    setText("#metaRegions", dataset.region_steps);
    localStorage.setItem(datasetKey, dataset.id);
}}

DATASETS.forEach((dataset, index) => {{
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = dataset.label;
    datasetSelect.append(option);
}});

datasetSelect.addEventListener("change", () => selectDataset(Number(datasetSelect.value)));
document.querySelectorAll("[data-theme-choice]").forEach((button) => {{
    button.addEventListener("click", () => applyTheme(button.dataset.themeChoice));
}});
mediaQuery.addEventListener("change", () => {{
    if ((localStorage.getItem(themeKey) || "system") === "system") applyTheme("system", false);
}});
datasetFrame.addEventListener("load", () => applyTheme(localStorage.getItem(themeKey) || "system", false));

applyTheme(localStorage.getItem(themeKey) || "system", false);
const savedDataset = localStorage.getItem(datasetKey);
const startIndex = Math.max(0, DATASETS.findIndex((dataset) => dataset.id === savedDataset));
if (DATASETS.length) selectDataset(startIndex);
</script>
</body>
</html>
'''
    (output_root / 'index.html').write_text(html, encoding='utf-8')
