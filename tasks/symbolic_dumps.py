from collections import defaultdict, deque
from html import escape
from pathlib import Path


class SymbolicBranchDump:
    def __init__(self, lexemes, edges, name):
        self.lexemes = lexemes
        self.edges = edges
        self.name = name
        self.label_blocks = self.find_label_blocks()
        self.branches = self.find_branches()
        self.edge_conditions = self.build_edge_conditions()
        self.path_prefixes = self.collect_path_prefixes()

    def table(self):
        rows = []
        for info in self.branches:
            rows.append([
                self.name(info['block']),
                self.branch_text(info),
                self.edge_text(info['block'], info['true']),
                self.edge_text(info['block'], info['false']),
                self.format_paths(self.path_prefixes.get(info['block'], [])),
                'syntactic; no SMT feasibility check',
            ])
        if not rows:
            rows.append([
                'No conditional branches',
                'None',
                'None',
                'None',
                'true',
                'no ifTrue / ifFalse branch lines in this input',
            ])
        return rows, ['block', 'branch', 'true edge', 'false edge', 'path prefix', 'status'], [
            '<comment>Path prefixes are sampled syntactic acyclic prefixes. '
            'Cycles are cut and no SMT satisfiability check is performed.</comment>'
        ]

    def find_label_blocks(self):
        labels = {}
        for block, lines in enumerate(self.lexemes):
            if lines and lines[0] and lines[0][0][0] == 1:
                labels[lines[0][0][1]] = block
        return labels

    def find_branches(self):
        branches = []
        for block, lines in enumerate(self.lexemes):
            for line in lines:
                condition_at = self.index_of_type(line, 5)
                goto_at = self.index_of_type(line, 6)
                if condition_at is None or goto_at is None:
                    continue
                target = self.goto_target(line, goto_at)
                fallthrough = self.fallthrough(block, target)
                is_true_jump = line[condition_at][1]
                condition = self.format_expression(line[condition_at + 1:goto_at])
                true_target = target if is_true_jump else fallthrough
                false_target = fallthrough if is_true_jump else target
                branches.append({
                    'block': block,
                    'line': line,
                    'condition': condition or 'true',
                    'jump_kind': 'ifTrue' if is_true_jump else 'ifFalse',
                    'target': target,
                    'fallthrough': fallthrough,
                    'true': true_target,
                    'false': false_target,
                })
        return branches

    def build_edge_conditions(self):
        edge_conditions = {}
        for info in self.branches:
            condition = info['condition']
            if info['true'] is not None:
                edge_conditions[(info['block'], info['true'])] = condition
            if info['false'] is not None:
                edge_conditions[(info['block'], info['false'])] = self.negate(condition)
        return edge_conditions

    def collect_path_prefixes(self, max_paths=3):
        prefixes = defaultdict(list)
        seen_prefixes = defaultdict(set)
        if not self.edges:
            return prefixes
        queue = deque([(0, tuple(), (0,))])
        prefixes[0].append(tuple())
        seen_prefixes[0].add(tuple())
        max_depth = max(2, len(self.edges) + 1)
        while queue:
            block, conditions, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for successor in sorted(self.edges[block]):
                edge_condition = self.edge_condition(block, successor)
                next_conditions = conditions
                if edge_condition != 'true':
                    next_conditions = conditions + (edge_condition,)
                if next_conditions not in seen_prefixes[successor] and len(prefixes[successor]) < max_paths:
                    prefixes[successor].append(next_conditions)
                    seen_prefixes[successor].add(next_conditions)
                if successor not in path and len(prefixes[successor]) <= max_paths:
                    queue.append((successor, next_conditions, path + (successor,)))
        return prefixes

    def edge_condition(self, source, target):
        return self.edge_conditions.get((source, target), 'true')

    def edge_text(self, source, target):
        if target is None:
            return 'None'
        return f'{self.name(source)} &rarr; {self.name(target)}'

    def branch_text(self, info):
        return f'{info["jump_kind"]} {info["condition"]} goto {self.block_ref(info["target"])}'

    @staticmethod
    def negate(condition):
        if condition.startswith('&not;(') and condition.endswith(')'):
            return condition[6:-1]
        return f'&not;({condition})'

    def block_ref(self, block):
        return self.name(block) if block is not None else 'None'

    @staticmethod
    def format_paths(paths):
        if not paths:
            return 'true'
        formatted = []
        for path in paths:
            if path:
                formatted.append(' &and; '.join(path))
            else:
                formatted.append('true')
        return '<br>'.join(formatted)

    def fallthrough(self, block, target):
        expected = block + 1
        if expected < len(self.edges) and expected in self.edges[block]:
            return expected
        for successor in sorted(self.edges[block]):
            if successor != target:
                return successor
        return None

    def goto_target(self, line, goto_at):
        if goto_at + 1 >= len(line) or line[goto_at + 1][0] != 1:
            return None
        return self.label_blocks.get(line[goto_at + 1][1])

    @staticmethod
    def index_of_type(line, token_type):
        for index, token in enumerate(line):
            if token[0] == token_type:
                return index
        return None

    @classmethod
    def format_expression(cls, tokens):
        parts = []
        for token in tokens:
            if token[0] == 1:
                continue
            parts.append(cls.format_token(token))
        return ' '.join(part for part in parts if part)

    @staticmethod
    def format_token(token):
        kind = token[0]
        if kind == 0:
            name = escape(token[1])
            indexes = token[2]
            if type(indexes) is int:
                return f'{name}<sub>{indexes}</sub>'
            if type(indexes) is list and len(indexes) == 1:
                return f'{name}<sub>{indexes[0]}</sub>'
            return name
        if kind == 1:
            return escape(token[1])
        if kind == 2:
            if token[2] == 5:
                return f'%{escape(token[1])}'
            return escape(token[1])
        if kind == 3:
            return f'#{token[1]}'
        if kind == 4:
            return f'@{escape(token[1])}'
        if kind == 5:
            return 'ifTrue' if token[1] else 'ifFalse'
        if kind == 6:
            return 'goto'
        if kind == 7:
            return 'pass'
        return escape(str(token))


class JoinMergePreview:
    def __init__(self, phi, dominator, name):
        self.phi = phi
        self.dominator = dominator
        self.name = name

    def table(self):
        rows = []
        for block in range(self.dominator.N):
            preds = sorted(self.dominator.pred_list[block])
            if len(preds) < 2:
                continue
            variables = sorted(self.phi.phi_args[block])
            if not variables:
                rows.append([
                    self.name(block),
                    self.format_blocks(preds),
                    'None',
                    'No phi variables placed at this join.',
                    'structural join only',
                ])
                continue
            for variable in variables:
                rows.append(self.variable_row(block, preds, variable))
        if not rows:
            rows.append([
                'No join candidates',
                'None',
                'None',
                'No blocks with multiple predecessors.',
                'not applicable',
            ])
        return rows, ['join', 'predecessors', 'variable', 'merge preview', 'status'], [
            '<comment>Merge previews are display-only. They reuse predecessor and phi data; '
            'no symbolic store is executed and no path feasibility is checked.</comment>'
        ]

    def variable_row(self, block, preds, variable):
        mapping = self.phi.phi_pred_args.get((block, variable), {})
        pairs = []
        for pred in preds:
            if pred in mapping:
                pairs.append((pred, self.version(variable, mapping[pred])))
        status = 'predecessor-mapped; no SMT check'
        if len(pairs) != len(preds):
            visible = self.visible_phi_args(block, variable)
            pairs = [(pred, value) for pred, value in zip(preds, visible)]
            status = 'partial; predecessor mapping incomplete'
        merge = self.nested_ite(pairs) if pairs else 'None'
        summary = self.value_summary(pairs) if pairs else 'None'
        return [
            self.name(block),
            self.format_blocks(preds),
            variable,
            f'{merge}<br>{summary}',
            status,
        ]

    def visible_phi_args(self, block, variable):
        for line_index, line in enumerate(self.phi.code_blocks[block]):
            if not self.phi.is_phi_line(block, line_index):
                break
            if line[-1][1] == variable:
                return [self.version(variable, index) for index in self.phi.indexes(line[-1])]
        return []

    def nested_ite(self, pairs):
        if len(pairs) == 1:
            return pairs[0][1]
        result = pairs[-1][1]
        for pred, value in reversed(pairs[:-1]):
            result = f'ite(path({self.name(pred)}), {value}, {result})'
        return result

    def value_summary(self, pairs):
        entries = [f'(path({self.name(pred)}), {value})' for pred, value in pairs]
        return '{' + ', '.join(entries) + '}'

    @staticmethod
    def version(variable, index):
        return f'{escape(variable)}<sub>{index}</sub>'

    def format_blocks(self, blocks):
        return ', '.join(self.name(block) for block in blocks) if blocks else 'None'


class HotVariableDump:
    def __init__(self, lexemes, edges, name, alpha=0.35, beta=0.5):
        self.lexemes = lexemes
        self.edges = edges
        self.name = name
        self.alpha = alpha
        self.beta = beta
        self.branch_info = SymbolicBranchDump(lexemes, edges, name)
        self.branch_uses = self.collect_branch_uses()
        self.local_dependency_branch_uses = self.collect_local_dependency_branch_uses()
        self.cfg_dependency_branch_uses = self.collect_cfg_dependency_branch_uses()
        self.versioned_dependency_branch_uses = self.collect_versioned_dependency_branch_uses()
        self.versioned_source_dependency_branch_uses = self.normalize_versioned_uses(
            self.versioned_dependency_branch_uses
        )
        self.branch_successors = self.collect_branch_successors()
        self.variables = self.collect_variables(self.branch_uses)
        self.local_dependency_variables = self.collect_variables(self.local_dependency_branch_uses)
        self.cfg_dependency_variables = self.collect_variables(self.cfg_dependency_branch_uses)
        self.versioned_dependency_variables = self.collect_variables(self.versioned_dependency_branch_uses)
        self.versioned_source_dependency_variables = self.collect_variables(
            self.versioned_source_dependency_branch_uses
        )
        self.q_t_syntactic = self.build_q_t(self.branch_uses)
        self.q_t_local_dependency = self.build_q_t(self.local_dependency_branch_uses)
        self.q_t_cfg_dependency = self.build_q_t(self.cfg_dependency_branch_uses)
        self.q_t_versioned_dependency = self.build_q_t(self.versioned_dependency_branch_uses)
        # Backward-compatible default for code paths that expect a single Q_t value.
        self.q_t = self.q_t_syntactic
        self.q_add = self.build_q_add(self.branch_uses, self.variables)
        self.q_add_local_dependency = self.build_q_add(
            self.local_dependency_branch_uses, self.local_dependency_variables
        )
        self.q_add_cfg_dependency = self.build_q_add(
            self.cfg_dependency_branch_uses, self.cfg_dependency_variables
        )
        self.q_add_versioned_dependency = self.build_q_add(
            self.versioned_dependency_branch_uses, self.versioned_dependency_variables
        )
        self.q_add_versioned_source_dependency = self.build_q_add(
            self.versioned_source_dependency_branch_uses, self.versioned_source_dependency_variables
        )

    def table(self):
        return self.make_table(
            self.q_add,
            self.q_t_syntactic,
            f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; syntactic C relation',
            '<comment>Q<sub>t</sub> and Q<sub>add</sub> follow the QCE recurrence from Efficient State Merging, '
            'with C approximated by syntactic variable occurrence in branch conditions. '
            'The dump does not estimate SMT or ite expression cost.</comment>'
        )

    def tables(self, output_dir=None):
        sections = [
            ('Syntactic branch variables', *self.table()),
            ('Local dependency variables', *self.make_table(
                self.q_add_local_dependency,
                self.q_t_local_dependency,
                f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; local dependency C relation',
                '<comment>Local dependency mode expands branch variables through assignments inside the same block. '
                'It does not propagate dependencies across CFG edges.</comment>'
            )),
            ('CFG dependency variables', *self.make_table(
                self.q_add_cfg_dependency,
                self.q_t_cfg_dependency,
                f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; cfg dependency C relation',
                '<comment>CFG dependency mode propagates assignment dependencies across CFG edges with set union at joins. '
                'It is still syntactic and does not check path feasibility.</comment>'
            )),
            ('Versioned dependency variables', *self.make_table(
                self.q_add_versioned_dependency,
                self.q_t_versioned_dependency,
                f'alpha={self.alpha:.2f}, beta={self.beta:.2f}; versioned dependency C relation',
                '<comment>Versioned dependency mode propagates source-definition versions across CFG edges. '
                'It is path-insensitive and does not check path feasibility.</comment>'
            )),
        ]
        if output_dir is not None:
            sections.append(self.algorithm_comparison_section(output_dir))
        return sections

    def algorithm_sources(self):
        return [
            ('Syntactic', self.q_add, self.q_t_syntactic),
            ('Local dependency', self.q_add_local_dependency, self.q_t_local_dependency),
            ('CFG dependency', self.q_add_cfg_dependency, self.q_t_cfg_dependency),
            ('Versioned dependency', self.q_add_versioned_dependency, self.q_t_versioned_dependency),
        ]

    def algorithm_block_masses(self):
        return [
            (label, self.block_masses(q_add_source))
            for label, q_add_source, _ in self.algorithm_sources()
        ]

    def algorithm_q_t_values(self):
        return [
            (label, q_t_source)
            for label, _, q_t_source in self.algorithm_sources()
        ]

    def block_masses(self, q_add_source):
        return [
            sum(values[block] for values in q_add_source.values() if block < len(values))
            for block in range(len(self.edges))
        ]

    def algorithm_comparison_section(self, output_dir, filename='qadd_algorithm_comparison.svg'):
        self.write_algorithm_comparison_svg(Path(output_dir) / filename)
        chart = (
            '<div class="graph-panel">'
            f'<img src="{escape(filename)}" alt="Q_add algorithm comparison">'
            '</div>'
        )
        note = (
            '<comment>Block-level Q<sub>add</sub> mass compares how widely each approximation mode propagates '
            'branch dependencies. Q<sub>t</sub> is plotted per approximation mode because some dependency '
            'relations may track different branch-query pressure. Hot-count bars use the matching mode-specific '
            'alpha * Q<sub>t</sub> threshold. This is an algorithm profile, not a correctness ranking and not a '
            'replacement for a manual oracle.</comment>'
        )
        return 'Q_add algorithm profile', [[chart]], ['chart'], [note]

    def algorithm_hot_counts(self):
        return [
            (label, self.hot_counts(q_add_source, q_t_source))
            for label, q_add_source, q_t_source in self.algorithm_sources()
        ]

    def hot_counts(self, q_add_source, q_t_source):
        counts = []
        for block in range(len(self.edges)):
            q_t = q_t_source[block] if block < len(q_t_source) else 0.0
            counts.append(sum(
                1
                for values in q_add_source.values()
                if block < len(values) and q_t and values[block] > self.alpha * q_t
            ))
        return counts

    def write_algorithm_comparison_svg(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        block_labels = [self.name(block) for block in range(len(self.edges))]
        mass_series = self.algorithm_block_masses()
        qt_series = self.algorithm_q_t_values()
        hot_series = self.algorithm_hot_counts()
        mass_values = [value for _, masses in mass_series for value in masses]
        qt_values = [value for _, values in qt_series for value in values]
        hot_values = [value for _, counts in hot_series for value in counts]
        max_mass_value = max(mass_values + qt_values) if mass_values or qt_values else 0.0
        max_hot_value = max(hot_values) if hot_values else 0

        block_count = max(1, len(block_labels))
        algorithm_count = max(1, len(mass_series))
        width = max(940, 130 + 92 * block_count)
        height = 660
        left, right = 76, 30
        top = 72
        mass_height = 305
        hot_top = 475
        hot_height = 112
        label_bottom = 48
        mass_baseline = top + mass_height
        hot_baseline = hot_top + hot_height
        plot_width = width - left - right
        mass_y_max = max_mass_value * 1.08 if max_mass_value > 0 else 1.0
        hot_y_max = max(1, max_hot_value)
        colors = ['#2563eb', '#16a34a', '#f97316', '#7c3aed']
        qt_color = '#0f172a'

        def sx(block_index):
            return left + block_index * (plot_width / block_count)

        def mass_sy(value):
            return mass_baseline - (value / mass_y_max) * mass_height

        def hot_sy(value):
            return hot_baseline - (value / hot_y_max) * hot_height

        def draw_y_axis(svg, plot_top, plot_height, baseline, y_max, label, integer_ticks=False):
            for tick in range(5):
                value = y_max * tick / 4
                y = baseline - (value / y_max) * plot_height if y_max else baseline
                svg.append(f'<line class="grid" x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}"/>')
                value_label = str(int(round(value))) if integer_ticks else self.format_number(value)
                svg.append(
                    f'<text class="label" x="{left - 8}" y="{y + 4:.2f}" text-anchor="end">{value_label}</text>'
                )
            svg.append(f'<line class="axis" x1="{left}" y1="{baseline}" x2="{width - right}" y2="{baseline}"/>')
            svg.append(f'<line class="axis" x1="{left}" y1="{plot_top}" x2="{left}" y2="{baseline}"/>')
            label_x = 20 if plot_height > 150 else 28
            svg.append(
                f'<text class="label" x="{label_x}" y="{plot_top + plot_height / 2:.2f}" '
                f'transform="rotate(-90 {label_x} {plot_top + plot_height / 2:.2f})" '
                f'text-anchor="middle">{label}</text>'
            )

        def bar_geometry():
            group_width = plot_width / block_count
            inner_width = group_width * 0.76
            gap = max(1.5, inner_width * 0.04)
            bar_width = max(2.0, (inner_width - gap * (algorithm_count - 1)) / algorithm_count)
            return group_width, inner_width, gap, bar_width

        group_width, inner_width, gap, bar_width = bar_geometry()

        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img">',
            '<title>Q_add algorithm profile</title>',
            '<style>'
            'text{font-family:Arial,sans-serif;font-size:12px;fill:#334155}'
            '.title{font-size:18px;font-weight:700;fill:#0f172a}'
            '.subtitle{font-size:12px;fill:#64748b}'
            '.section{font-size:14px;font-weight:700;fill:#0f172a}'
            '.axis{stroke:#475569;stroke-width:1}'
            '.grid{stroke:#e2e8f0;stroke-width:1}'
            '.label{font-size:11px;fill:#475569}'
            '.legend{font-size:12px;fill:#334155}'
            '.qt{fill:#0f172a;stroke:#0f172a}'
            '</style>',
            '<rect width="100%" height="100%" fill="white"/>',
            f'<text class="title" x="{left}" y="28">Q_add algorithm profile</text>',
            f'<text class="subtitle" x="{left}" y="47">alpha={self.alpha:.2f}, beta={self.beta:.2f}; Q_t and Q_add are shown per dependency mode</text>',
            f'<text class="section" x="{left}" y="{top - 18}">Q_add mass by block</text>',
            f'<text class="section" x="{left}" y="{hot_top - 18}">Hot variable count by block</text>',
        ]

        draw_y_axis(svg, top, mass_height, mass_baseline, mass_y_max, 'sum Q_add(block, var)')
        draw_y_axis(svg, hot_top, hot_height, hot_baseline, hot_y_max, 'hot variables', integer_ticks=True)

        for block_index, block_label in enumerate(block_labels):
            group_start = sx(block_index) + (group_width - inner_width) / 2
            center = sx(block_index) + group_width / 2
            svg.append(f'<text class="label" x="{center:.2f}" y="{hot_baseline + 22}" text-anchor="end" '
                       f'transform="rotate(-35 {center:.2f} {hot_baseline + 22})">{escape(block_label)}</text>')

            for algo_index, (algo_label, masses) in enumerate(mass_series):
                value = masses[block_index] if block_index < len(masses) else 0.0
                x = group_start + algo_index * (bar_width + gap)
                y = mass_sy(value)
                bar_height = mass_baseline - y
                svg.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
                    f'fill="{colors[algo_index % len(colors)]}">'
                    f'<title>{escape(block_label)} / {escape(algo_label)} mass: {value:.2f}</title>'
                    '</rect>'
                )

            for algo_index, (algo_label, counts) in enumerate(hot_series):
                value = counts[block_index] if block_index < len(counts) else 0
                x = group_start + algo_index * (bar_width + gap)
                y = hot_sy(value)
                bar_height = hot_baseline - y
                svg.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
                    f'fill="{colors[algo_index % len(colors)]}" opacity="0.82">'
                    f'<title>{escape(block_label)} / {escape(algo_label)} hot variables: {value}</title>'
                    '</rect>'
                )

        for algo_index, (algo_label, q_t_values) in enumerate(qt_series):
            qt_points = []
            x_offset = (algo_index - (algorithm_count - 1) / 2) * max(3.0, bar_width * 0.55)
            for block_index, value in enumerate(q_t_values):
                center = sx(block_index) + group_width / 2 + x_offset
                qt_points.append((center, mass_sy(value), value, block_labels[block_index]))
            if qt_points:
                points_attr = ' '.join(f'{x:.2f},{y:.2f}' for x, y, _, _ in qt_points)
                color = colors[algo_index % len(colors)]
                svg.append(
                    f'<polyline points="{points_attr}" fill="none" stroke="{color}" '
                    f'stroke-width="2.0" stroke-dasharray="4 3"/>'
                )
                for x, y, value, block_label in qt_points:
                    svg.append(
                        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="white" '
                        f'stroke="{color}" stroke-width="2">'
                        f'<title>{escape(block_label)} / {escape(algo_label)} Q_t: {value:.2f}</title>'
                        '</circle>'
                    )

        legend_x = left + 260
        legend_y = 26
        for algo_index, (algo_label, _) in enumerate(mass_series):
            x = legend_x + algo_index * 132
            svg.append(f'<rect x="{x}" y="{legend_y - 10}" width="12" height="12" fill="{colors[algo_index % len(colors)]}"/>')
            svg.append(f'<text class="legend" x="{x + 17}" y="{legend_y}">{escape(algo_label)}</text>')
        qtx = legend_x + algorithm_count * 132
        svg.append(f'<line x1="{qtx}" y1="{legend_y - 4}" x2="{qtx + 20}" y2="{legend_y - 4}" stroke="{qt_color}" stroke-width="2.0" stroke-dasharray="4 3"/>')
        svg.append(f'<circle cx="{qtx + 10}" cy="{legend_y - 4}" r="3.2" fill="white" stroke="{qt_color}" stroke-width="2"/>')
        svg.append(f'<text class="legend" x="{qtx + 27}" y="{legend_y}">Q_t per mode</text>')

        if max_mass_value <= 0:
            svg.append(f'<text x="{left + plot_width / 2:.2f}" y="{top + mass_height / 2:.2f}" '
                       f'text-anchor="middle" fill="#64748b">No Q_add dependencies detected</text>')
        if max_hot_value <= 0:
            svg.append(f'<text x="{left + plot_width / 2:.2f}" y="{hot_top + hot_height / 2:.2f}" '
                       f'text-anchor="middle" fill="#64748b">No variables pass alpha * Q_t</text>')

        svg.append(f'<text class="subtitle" x="{left}" y="{height - 18}">Solid bars: Q_add mass; dashed lines: mode-specific Q_t; lower bars: hot variables under the same mode-specific threshold.</text>')
        svg.append('</svg>')
        path.write_text('\n'.join(svg) + '\n', encoding='utf-8')

    def make_table(self, q_add_source, q_t_source, status, note=None):
        rows = []
        for block in range(len(self.edges)):
            q_t = q_t_source[block] if block < len(q_t_source) else 0.0
            q_add = {variable: values[block] for variable, values in q_add_source.items() if values[block] > 0.0}
            hot = sorted([var for var, value in q_add.items() if q_t and value > self.alpha * q_t])
            rows.append([
                self.name(block),
                self.format_number(q_t),
                ', '.join(self.format_variable_key(var) for var in hot) if hot else 'None',
                self.format_counts(q_add),
                status,
            ])
        if not rows:
            rows.append(['No blocks', 0, 'None', 'None', 'not applicable'])
        notes = [note] if note else []
        return rows, ['block', 'Q<sub>t</sub>', 'hot variables', 'Q<sub>add</sub>(block, var)', 'status'], notes

    def collect_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        for block, lines in enumerate(self.lexemes):
            for line in lines:
                condition_at = SymbolicBranchDump.index_of_type(line, 5)
                goto_at = SymbolicBranchDump.index_of_type(line, 6)
                if condition_at is None or goto_at is None:
                    continue
                for token in line[condition_at + 1:goto_at]:
                    if token[0] == 0:
                        uses[block].add(token[1])
        return uses

    def collect_local_dependency_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        for block, lines in enumerate(self.lexemes):
            dependencies = {}
            for line in lines:
                assignment_at = self.assignment_operator_index(line)
                condition_at = SymbolicBranchDump.index_of_type(line, 5)
                goto_at = SymbolicBranchDump.index_of_type(line, 6)

                if assignment_at is not None:
                    target = line[assignment_at - 1]
                    if target[0] == 0:
                        dependencies[target[1]] = self.tokens_dependencies(line[assignment_at + 1:], dependencies)

                if condition_at is not None and goto_at is not None:
                    uses[block] |= self.tokens_dependencies(line[condition_at + 1:goto_at], dependencies)
        return uses

    def collect_cfg_dependency_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        in_maps = [{} for _ in self.lexemes]
        out_maps = [{} for _ in self.lexemes]
        changed = True
        while changed:
            changed = False
            for block, lines in enumerate(self.lexemes):
                next_out, block_uses = self.transfer_dependencies(in_maps[block], lines)
                uses[block] |= block_uses
                if self.dependency_maps_differ(out_maps[block], next_out):
                    out_maps[block] = next_out
                    changed = True
                for successor in self.edges[block]:
                    merged = self.merge_dependency_maps(in_maps[successor], out_maps[block])
                    if self.dependency_maps_differ(in_maps[successor], merged):
                        in_maps[successor] = merged
                        changed = True
        return uses

    def collect_versioned_dependency_branch_uses(self):
        uses = [set() for _ in self.lexemes]
        definition_keys = self.collect_definition_keys()
        in_maps = [{} for _ in self.lexemes]
        out_maps = [{} for _ in self.lexemes]
        changed = True
        while changed:
            changed = False
            for block, lines in enumerate(self.lexemes):
                next_out, block_uses = self.transfer_versioned_dependencies(
                    in_maps[block], lines, block, definition_keys
                )
                uses[block] |= block_uses
                if self.dependency_maps_differ(out_maps[block], next_out):
                    out_maps[block] = next_out
                    changed = True
                for successor in self.edges[block]:
                    merged = self.merge_dependency_maps(in_maps[successor], out_maps[block])
                    if self.dependency_maps_differ(in_maps[successor], merged):
                        in_maps[successor] = merged
                        changed = True
        return uses

    def collect_definition_keys(self):
        counters = defaultdict(int)
        keys = {}
        for block, lines in enumerate(self.lexemes):
            for line_index, line in enumerate(lines):
                target = self.param_target(line)
                if target is None:
                    assignment_at = self.assignment_operator_index(line)
                    if assignment_at is not None and line[assignment_at - 1][0] == 0:
                        target = line[assignment_at - 1]
                if target is not None:
                    version = counters[target[1]]
                    counters[target[1]] += 1
                    keys[(block, line_index)] = (target[1], version)
        return keys

    def transfer_versioned_dependencies(self, input_map, lines, block, definition_keys):
        env = self.copy_dependency_map(input_map)
        uses = set()
        for line_index, line in enumerate(lines):
            param_target = self.param_target(line)
            if param_target is not None:
                env[param_target[1]] = {definition_keys[(block, line_index)]}

            assignment_at = self.assignment_operator_index(line)
            if assignment_at is not None:
                target = line[assignment_at - 1]
                if target[0] == 0:
                    env[target[1]] = self.versioned_tokens_dependencies(line[assignment_at + 1:], env)

            condition_at = SymbolicBranchDump.index_of_type(line, 5)
            goto_at = SymbolicBranchDump.index_of_type(line, 6)
            if condition_at is not None and goto_at is not None:
                uses |= self.versioned_tokens_dependencies(line[condition_at + 1:goto_at], env)
        return env, uses

    @staticmethod
    def param_target(line):
        for index in range(len(line) - 1):
            if line[index][0] == 2 and line[index][2] == 0 and line[index + 1][0] == 0:
                return line[index + 1]
        return None

    def transfer_dependencies(self, input_map, lines):
        env = self.copy_dependency_map(input_map)
        uses = set()
        for line in lines:
            assignment_at = self.assignment_operator_index(line)
            condition_at = SymbolicBranchDump.index_of_type(line, 5)
            goto_at = SymbolicBranchDump.index_of_type(line, 6)

            if assignment_at is not None:
                target = line[assignment_at - 1]
                if target[0] == 0:
                    env[target[1]] = self.tokens_dependencies(line[assignment_at + 1:], env)

            if condition_at is not None and goto_at is not None:
                uses |= self.tokens_dependencies(line[condition_at + 1:goto_at], env)
        return env, uses

    @staticmethod
    def copy_dependency_map(source):
        return {variable: set(dependencies) for variable, dependencies in source.items()}

    @staticmethod
    def merge_dependency_maps(left, right):
        result = HotVariableDump.copy_dependency_map(left)
        for variable, dependencies in right.items():
            result.setdefault(variable, set()).update(dependencies)
        return result

    @staticmethod
    def dependency_maps_differ(left, right):
        if left.keys() != right.keys():
            return True
        return any(left[variable] != right[variable] for variable in left)

    @staticmethod
    def assignment_operator_index(line):
        for index in range(1, len(line)):
            if line[index][0] == 2 and line[index][2] == 2:
                return index
        return None

    @classmethod
    def tokens_dependencies(cls, tokens, dependencies):
        result = set()
        for token in tokens:
            if token[0] == 0:
                result |= dependencies.get(token[1], {token[1]})
        return result

    @classmethod
    def versioned_tokens_dependencies(cls, tokens, dependencies):
        result = set()
        for token in tokens:
            if token[0] == 0:
                result |= dependencies.get(token[1], {(token[1], -1)})
        return result

    @classmethod
    def normalize_versioned_uses(cls, uses):
        return [set(cls.source_name(variable) for variable in block_uses) for block_uses in uses]

    @staticmethod
    def source_name(variable):
        if type(variable) is tuple and len(variable) == 2:
            return variable[0]
        if type(variable) is str:
            if '<sub>' in variable:
                return variable.split('<sub>', 1)[0]
            if '_' in variable and variable.rsplit('_', 1)[1].isdigit():
                return variable.rsplit('_', 1)[0]
        return variable

    @staticmethod
    def collect_variables(uses):
        return sorted(set().union(*uses) if uses else set())

    def build_q_t(self, uses):
        return self.solve_q({
            block: 1.0
            for block, block_uses in enumerate(uses)
            if block_uses
        })

    def build_q_add(self, uses, variables):
        return {
            variable: self.solve_q({
                block: 1.0 for block, block_uses in enumerate(uses) if variable in block_uses
            })
            for variable in variables
        }

    def collect_branch_successors(self):
        successors = {}
        for info in self.branch_info.branches:
            targets = []
            for target in [info['true'], info['false']]:
                if target is not None and target not in targets:
                    targets.append(target)
            if targets:
                successors[info['block']] = targets
        return successors

    def solve_q(self, cost, max_iterations=200, tolerance=0.001):
        values = [0.0 for _ in self.edges]
        for _ in range(max_iterations):
            next_values = [0.0 for _ in self.edges]
            for block in reversed(range(len(self.edges))):
                successors = sorted(self.edges[block])
                local_cost = cost.get(block, 0.0)
                if block in self.branch_successors:
                    next_values[block] = local_cost + self.beta * sum(
                        values[successor] for successor in self.branch_successors[block]
                    )
                elif len(successors) == 1:
                    next_values[block] = local_cost + values[successors[0]]
                elif successors:
                    next_values[block] = local_cost + self.beta * sum(values[successor] for successor in successors)
                else:
                    next_values[block] = 0.0
            if max(abs(next_values[idx] - values[idx]) for idx in range(len(values))) < tolerance:
                return next_values
            values = next_values
        return values

    @staticmethod
    def format_counts(counts):
        if not counts:
            return 'None'
        return ', '.join([f'{HotVariableDump.format_variable_key(var)}:{HotVariableDump.format_number(value)}'
                          for var, value in sorted(counts.items())])

    @staticmethod
    def format_variable_key(variable):
        if type(variable) is tuple and len(variable) == 2:
            name, version = variable
            if version == -1:
                return f'{escape(name)}<sub>in</sub>'
            return f'{escape(name)}<sub>{version}</sub>'
        return escape(variable)

    @staticmethod
    def format_number(value):
        if abs(value) < 0.005:
            return '0'
        return f'{value:.2f}'


class UnsupportedSymbolicStageDump:
    def table(self):
        rows = [
            ['Array transformations', 'stub',
             'current MIR has no array read/write syntax or array values',
             'keep as documentation-only placeholder'],
            ['Function summaries', 'stub',
             'current MIR has param/return but no call instruction, callee identity, or call graph',
             'keep as documentation-only placeholder'],
            ['Heap/list/shape execution', 'out of scope',
             'current MIR has no heap allocation, fields, references, aliases, or predicates',
             'do not expand parser for this dump-first task'],
            ['Compiled symbolic execution', 'out of scope',
             'project is not compiling LLVM/C/Java into a symbolic executor',
             'no implementation planned'],
        ]
        return rows, ['family', 'status', 'why unavailable', 'current action'], [
            '<comment>These paper families are intentionally marked as stubs or out of scope until the input '
            'language already supports the required concepts.</comment>'
        ]


class AcyclicRegionSummaryPreview:
    def __init__(self, lexemes, edges, post_dominator, name):
        self.lexemes = lexemes
        self.edges = edges
        self.post_dominator = post_dominator
        self.name = name
        self.branches = SymbolicBranchDump(lexemes, edges, name)

    def table(self):
        rows = []
        for branch in self.branches.branches:
            entry = branch['block']
            if entry >= len(self.post_dominator.ipdom_list):
                continue
            exit_block = self.post_dominator.ipdom_list[entry]
            if exit_block in (-1, entry):
                continue
            nodes = self.region_nodes(entry, exit_block)
            if not nodes:
                continue
            cyclic = self.has_cycle(nodes)
            preview = self.path_preview(entry, exit_block, nodes) if not cyclic else 'not emitted'
            status = ('syntactic acyclic summary; no SMT/store execution'
                      if not cyclic else 'cycle detected; transition: incomplete loop / resume normal dump')
            rows.append([
                self.name(entry),
                self.name(exit_block),
                self.format_blocks(sorted(nodes)),
                not cyclic,
                preview,
                status,
            ])
        if not rows:
            rows.append([
                'No acyclic region candidates',
                'None',
                'None',
                False,
                'None',
                'no conditional block with a usable immediate postdominator',
            ])
        return rows, ['entry', 'exit', 'nodes', 'loop-free', 'path summary preview', 'status'], [
            '<comment>Region summaries are syntactic previews inspired by veritesting-style regions. '
            'They do not execute stores, solve formulas, or replace the existing region reduction.</comment>'
        ]

    def region_nodes(self, entry, exit_block):
        nodes = set()
        stack = [entry]
        while stack:
            node = stack.pop()
            if node == exit_block or node in nodes:
                continue
            nodes.add(node)
            for successor in sorted(self.edges[node]):
                if successor != exit_block:
                    stack.append(successor)
        return nodes

    def has_cycle(self, nodes):
        visiting = set()
        visited = set()

        def visit(node):
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for successor in self.edges[node]:
                if successor in nodes and visit(successor):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in sorted(nodes))

    def path_preview(self, entry, exit_block, nodes, max_paths=4):
        paths = []

        def walk(node, conditions, seen):
            if len(paths) >= max_paths:
                return
            if node == exit_block:
                paths.append(conditions)
                return
            if node in seen:
                return
            next_seen = seen | {node}
            for successor in sorted(self.edges[node]):
                if successor != exit_block and successor not in nodes:
                    continue
                condition = self.branches.edge_condition(node, successor)
                next_conditions = conditions
                if condition != 'true':
                    next_conditions = conditions + [condition]
                walk(successor, next_conditions, next_seen)

        walk(entry, [], set())
        if not paths:
            return 'no acyclic path preview'
        formatted = []
        for index, conditions in enumerate(paths, start=1):
            path_condition = ' &and; '.join(conditions) if conditions else 'true'
            formatted.append(f'path {index}: {path_condition} &rarr; {self.name(exit_block)}')
        if len(paths) == max_paths:
            formatted.append('path list truncated')
        return '<br>'.join(formatted)

    def format_blocks(self, blocks):
        return ', '.join(self.name(block) for block in blocks) if blocks else 'None'
