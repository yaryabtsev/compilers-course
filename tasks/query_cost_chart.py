from html import escape
from pathlib import Path


class QAddAlgorithmProfileChart:
    def __init__(self, dump):
        self.dump = dump

    @property
    def alpha(self):
        return self.dump.alpha

    @property
    def beta(self):
        return self.dump.beta

    @property
    def edges(self):
        return self.dump.edges

    def name(self, block):
        return self.dump.name(block)

    def format_number(self, value):
        return self.dump.format_number(value)

    def algorithm_block_masses(self):
        return self.dump.algorithm_block_masses()

    def algorithm_q_t_values(self):
        return self.dump.algorithm_q_t_values()

    def algorithm_hot_counts(self):
        return self.dump.algorithm_hot_counts()

    def section(self, output_dir, filename='qadd_algorithm_comparison.svg'):
        self.write_svg(Path(output_dir) / filename)
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


    def write_svg(self, path):
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

