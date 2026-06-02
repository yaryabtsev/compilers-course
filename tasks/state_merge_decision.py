from html import escape

from tasks.query_cost_estimation import HotVariableDump


class StateMergeDecisionPreview:
    def __init__(self, phi, dominator, hot_variables, name):
        self.phi = phi
        self.dominator = dominator
        self.hot_variables = hot_variables
        self.name = name
        self.entry_dependencies = self.collect_entry_dependencies()

    def table(self):
        rows = []
        for block in range(self.dominator.N):
            preds = sorted(self.dominator.pred_list[block])
            if len(preds) < 2:
                continue
            merged_vars = sorted(self.phi.phi_args[block])
            if not merged_vars:
                continue

            q_t = self.future_q_t(block)
            future_hot = self.future_hot_vars(block, q_t)
            merged_deps = self.merged_source_deps(block, merged_vars)
            risky = sorted(set(merged_deps) & set(future_hot))
            decision = self.decision(q_t, future_hot, risky)
            rows.append([
                self.name(block),
                self.format_blocks(preds),
                self.format_vars(merged_vars),
                self.format_vars(merged_deps),
                self.format_vars(future_hot),
                self.format_vars(risky),
                decision,
                self.reason(decision),
            ])

        if not rows:
            rows.append([
                'No merge decisions',
                'None',
                'None',
                'None',
                'None',
                'None',
                'not applicable',
                'no join block with phi-like merge candidates',
            ])
        return rows, ['join', 'predecessors', 'candidate merged vars', 'merged source deps',
                      'future hot vars', 'risky overlap', 'decision', 'reason'], [
            '<comment>Static preview only: uses phi candidates, CFG-dependency QCE hot variables, '
            'and path-insensitive source-dependency sets. It does not execute symbolic states, call '
            'an SMT solver, check feasibility, schedule states, or benchmark runtime cost.</comment>'
        ]

    def collect_entry_dependencies(self):
        in_maps = [{} for _ in self.hot_variables.lexemes]
        out_maps = [{} for _ in self.hot_variables.lexemes]
        changed = True
        while changed:
            changed = False
            for block, lines in enumerate(self.hot_variables.lexemes):
                next_out, _ = self.hot_variables.transfer_dependencies(in_maps[block], lines)
                if HotVariableDump.dependency_maps_differ(out_maps[block], next_out):
                    out_maps[block] = next_out
                    changed = True
                for successor in self.hot_variables.edges[block]:
                    merged = HotVariableDump.merge_dependency_maps(in_maps[successor], out_maps[block])
                    if HotVariableDump.dependency_maps_differ(in_maps[successor], merged):
                        in_maps[successor] = merged
                        changed = True
        return in_maps

    def merged_source_deps(self, block, variables):
        entry_map = self.entry_dependencies[block] if block < len(self.entry_dependencies) else {}
        deps = set()
        for variable in variables:
            deps |= entry_map.get(variable, {variable})
        return sorted(self.hot_variables.source_name(dep) for dep in deps)

    def future_q_t(self, block):
        values = self.hot_variables.q_t_cfg_dependency
        return values[block] if block < len(values) else 0.0

    def future_hot_vars(self, block, q_t):
        if not q_t:
            return []
        threshold = self.hot_variables.alpha * q_t
        result = []
        for variable, values in self.hot_variables.q_add_cfg_dependency.items():
            if block < len(values) and values[block] > threshold:
                result.append(self.hot_variables.source_name(variable))
        return sorted(set(result))

    @staticmethod
    def decision(q_t, future_hot, risky):
        if not q_t:
            return 'no-future-query'
        if not risky:
            return 'merge-friendly'
        if len(risky) < len(future_hot):
            return 'mixed'
        return 'merge-risky'

    @staticmethod
    def reason(decision):
        return {
            'no-future-query': 'Q_t is zero; no future branch pressure is visible at this join',
            'merge-friendly': 'merged dependencies do not overlap future hot variables',
            'mixed': 'some merged dependencies may flow into future branch conditions',
            'merge-risky': 'merged dependencies cover the future hot variables at this join',
        }.get(decision, 'no static decision available')

    def format_blocks(self, blocks):
        return ', '.join(self.name(block) for block in blocks) if blocks else 'None'

    @staticmethod
    def format_vars(variables):
        return ', '.join(escape(str(variable)) for variable in variables) if variables else 'None'
