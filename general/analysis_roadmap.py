from html import escape


ROADMAP = [
    {
        'section': 'Base MIR',
        'label': 'MIR',
        'description': 'input split into basic blocks',
        'family': 'source',
    },
    {
        'section': 'Control Flow Graph',
        'label': 'CFG',
        'description': 'successors, predecessors, and branch shape',
        'family': 'graph',
        'branches': [
            {
                'label': 'Branch queries',
                'family': 'query',
                'items': [
                    {
                        'section': 'Symbolic Branch Conditions',
                        'label': 'Branch Conditions',
                        'description': 'syntactic path and fork preview',
                    },
                    {
                        'section': 'Q_add / Q_t Approximation',
                        'label': 'Query Pressure',
                        'description': 'future branch-use estimates',
                    },
                    {
                        'section': 'Quantified Pattern Preview',
                        'label': 'Loop Pattern',
                        'description': 'bounded loop-shape inference',
                    },
                    {
                        'section': 'Symbolic Execution Scope Stubs',
                        'label': 'Scope Notes',
                        'description': 'intentionally unsupported MIR concepts',
                    },
                ],
            },
        ],
    },
    {
        'section': 'Local Value Tables',
        'label': 'Local Facts',
        'description': 'local numbering and value table rows',
        'family': 'local',
        'branches': [
            {
                'label': 'Local data flow',
                'family': 'local',
                'items': [
                    {
                        'section': 'Input / Output Sets',
                        'label': 'Input / Output',
                        'description': 'variables read before and defined in blocks',
                    },
                ],
            },
        ],
    },
    {
        'section': 'Pred / Dom / Idom / DF',
        'label': 'Dominance',
        'description': 'dominators, immediate dominators, and frontier',
        'family': 'dominance',
        'branches': [
            {
                'label': 'Derived dominance views',
                'family': 'dominance',
                'items': [
                    {
                        'section': 'Dominator Tree',
                        'label': 'Dom Tree',
                        'description': 'tree view of immediate dominators',
                    },
                    {
                        'section': 'Postdominators & Control Dependence',
                        'label': 'Postdom / CD',
                        'description': 'postdominators and control dependence',
                    },
                ],
            },
        ],
    },
    {
        'section': 'Phi Placement',
        'label': 'SSA',
        'description': 'phi placement and rename-oriented checks',
        'family': 'ssa',
        'branches': [
            {
                'label': 'SSA artifacts',
                'family': 'ssa',
                'items': [
                    {
                        'section': 'Globals & Blocks',
                        'label': 'Globals',
                        'description': 'definition blocks selected for SSA',
                    },
                    {
                        'section': 'Phi-Inserted Code',
                        'label': 'Phi Code',
                        'description': 'MIR after phi insertion',
                    },
                    {
                        'section': 'Partially Truncated SSA Form',
                        'label': 'SSA Rename',
                        'description': 'rename trace and resulting names',
                    },
                    {
                        'section': 'SSA Checks',
                        'label': 'SSA Checks',
                        'description': 'small consistency audit',
                    },
                ],
            },
            {
                'label': 'Merge previews',
                'family': 'merge',
                'items': [
                    {
                        'section': 'Join Merge Preview',
                        'label': 'Join Merge',
                        'description': 'join candidates from predecessor/phi data',
                    },
                    {
                        'section': 'State Merge Decision Preview',
                        'label': 'Merge Risk',
                        'description': 'static overlap with future hot variables',
                    },
                    {
                        'section': 'ITE-Cost Preview',
                        'label': 'ITE Cost',
                        'description': 'shallow formula-growth shape',
                    },
                ],
            },
        ],
    },
    {
        'section': 'Cycle-Based Region Reduction',
        'label': 'Regions',
        'description': 'cycle reduction and region discovery',
        'family': 'region',
        'branches': [
            {
                'label': 'Region summaries',
                'family': 'region',
                'items': [
                    {
                        'section': 'Acyclic Region Summary Preview',
                        'label': 'Acyclic Summary',
                        'description': 'straight-line region summary preview',
                    },
                    {
                        'section': 'Control Tree',
                        'label': 'Control Tree',
                        'description': 'region tree visualization',
                    },
                    {
                        'section': 'Region Classification',
                        'label': 'Classes',
                        'description': 'area, body, and loop region classes',
                    },
                ],
            },
        ],
    },
    {
        'section': 'Gen / Kill',
        'label': 'Transfer',
        'description': 'reaching-definition facts and structural transfer',
        'family': 'transfer',
        'branches': [
            {
                'label': 'Transfer detail',
                'family': 'transfer',
                'items': [
                    {
                        'section': 'Region Transfer Functions (Structural)',
                        'label': 'Region Transfer',
                        'description': 'structural transfer-function preview',
                    },
                ],
            },
        ],
    },
]


def render_analysis_roadmap(titles: list[str], notes: list[str]) -> str:
    section_ids = {title: index for index, title in enumerate(titles)}
    note_by_title = {title: notes[index] for index, title in enumerate(titles) if index < len(notes)}
    stages = '\n'.join(_render_stage(stage, section_ids, note_by_title) for stage in ROADMAP)
    return (
        '<nav class="analysis-roadmap" aria-labelledby="analysis-roadmap-title">\n'
        '<div class="roadmap-header">\n'
        '<div>\n'
        '<p id="analysis-roadmap-title">Analysis Roadmap</p>\n'
        '<small>analysis flow and derived dumps</small>\n'
        '</div>\n'
        '<div class="roadmap-legend" aria-label="Roadmap status legend">\n'
        '<span data-status="available">available</span>\n'
        '<span data-status="empty">empty</span>\n'
        '<span data-status="warning">warning</span>\n'
        '<span data-status="not-applicable">n/a</span>\n'
        '</div>\n'
        '</div>\n'
        f'<ol class="roadmap-path">\n{stages}\n</ol>\n'
        '</nav>'
    )


def _render_stage(stage: dict, section_ids: dict[str, int], note_by_title: dict[str, str]) -> str:
    branches = stage.get('branches', [])
    family = stage.get('family', 'default')
    branch_html = ''.join(_render_branch(branch, section_ids, note_by_title, family) for branch in branches)
    return (
        f'<li class="roadmap-stage" data-family="{escape(family)}">\n'
        f'{_render_node(stage, section_ids, note_by_title, "roadmap-main-node", family)}\n'
        f'{branch_html}\n'
        '</li>'
    )


def _render_branch(branch: dict, section_ids: dict[str, int], note_by_title: dict[str, str],
                   parent_family: str) -> str:
    family = branch.get('family', parent_family)
    items = '\n'.join(
        '<li>' + _render_node(item, section_ids, note_by_title, 'roadmap-branch-node', family) + '</li>'
        for item in branch.get('items', [])
    )
    if not items:
        return ''
    return (
        f'<details class="roadmap-branch" data-family="{escape(family)}" open>\n'
        f'<summary>{escape(branch.get("label", "Related dumps"))}</summary>\n'
        f'<ol class="roadmap-branch-list">\n{items}\n</ol>\n'
        '</details>\n'
    )


def _render_node(item: dict, section_ids: dict[str, int], note_by_title: dict[str, str], class_name: str,
                 family: str) -> str:
    section = item.get('section', '')
    title_id = section_ids.get(section)
    available = title_id is not None
    href = f'#title-{title_id}' if available else '#'
    status = 'available' if available else 'not-applicable'
    label = item.get('label') or section
    description = item.get('description') or note_by_title.get(section, '')
    title = section if available else f'{section} is not present in this report'
    disabled = '' if available else ' is-disabled'
    return (
        f'<a class="roadmap-node {class_name}{disabled}" href="{href}" '
        f'data-family="{escape(family)}" data-section-title="{escape(section)}" '
        f'data-status="{status}" title="{escape(title)}">\n'
        '<span class="roadmap-node-top">\n'
        f'<span class="roadmap-node-label">{escape(label)}</span>\n'
        f'<span class="roadmap-status">{_status_label(status)}</span>\n'
        '</span>\n'
        f'<span class="roadmap-node-desc">{escape(description)}</span>\n'
        '</a>'
    )


def _status_label(status: str) -> str:
    return {
        'available': 'available',
        'empty': 'empty',
        'warning': 'warning',
        'not-applicable': 'n/a',
    }.get(status, status)
