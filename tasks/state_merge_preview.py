from html import escape


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
                    f'preds={len(preds)}, mapped=0',
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
                'None',
                'not applicable',
            ])
        return rows, ['join', 'predecessors', 'variable', 'merge preview', 'merge metrics', 'status'], [
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
            f'preds={len(preds)}, mapped={len(pairs)}, ite ops={max(0, len(pairs) - 1)}, '
            f'summary entries={len(pairs)}',
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


