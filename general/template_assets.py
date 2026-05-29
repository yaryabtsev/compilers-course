from pathlib import Path
from shutil import copyfile
from string import Template


TEMPLATE_DIR = Path(__file__).with_name('templates')


def render_template(name: str, **values) -> str:
    template = Template((TEMPLATE_DIR / name).read_text(encoding='utf-8'))
    return template.safe_substitute(**values)


def ensure_output_assets(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for asset_name in ['styles.css', 'theme.js', 'report.js', 'viewer.js']:
        source = TEMPLATE_DIR / asset_name
        target = output_root / asset_name
        if not target.exists() or target.read_bytes() != source.read_bytes():
            copyfile(source, target)
