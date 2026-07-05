from html import escape

from tasks.branch_conditions import SymbolicBranchDump
from tasks.query_cost_estimation import HotVariableDump
from tasks.z3_simplification import Z3FormulaSimplifier


class IteCostPreview:
    def __init__(self, phi, dominator, hot_variables, name, max_expr_nodes=40):
        self.phi = phi
        self.dominator = dominator
        self.hot_variables = hot_variables
        self.name = name
        self.max_expr_nodes = max_expr_nodes
        self.branches = SymbolicBranchDump(hot_variables.lexemes, hot_variables.edges, name)
        self.simplifier = Z3FormulaSimplifier()

    def table(self):
        rows = [self.preview_row(record) for record in self.preview_records()]
        if not rows:
            rows.append(['No ITE previews', 'None', 'None', 'None', 'None',
                         '0', '0', '0', 'no merge candidates'])
        return rows, ['merge site', 'variable', 'ite preview', 'future branch',
                      'expanded branch preview', 'ite ops', 'ite depth', 'expr size', 'status'], [
            '<comment>Syntactic shallow preview only: reconstructs small two-way join expressions, '
            'substitutes at most local assignment chains, and counts visible ite nodes. It is '
            'path-insensitive and is not an SMT formula, simplifier, runtime benchmark, or solver-cost estimate.</comment>'
        ]

    def z3_merge_table(self):
        rows = []
        for record in self.preview_records():
            raw = record.get('ite_rhs')
            if not raw:
                rows.append([
                    record['site'],
                    record['variable'],
                    'None',
                    'None',
                    'None',
                    'None',
                    '0',
                    '0',
                    '0',
                    '0',
                    '0',
                    record['status'],
                ])
                continue
            result = self.simplifier.simplify_text(raw)
            rows.append(self.z3_row(record['site'], record['variable'], raw, result))
        if not rows:
            rows.append(['No merge candidates', 'None', 'None', 'None', 'None', 'None',
                         '0', '0', '0', '0', '0', '0', 'not applicable'])
        return rows, ['join', 'variable', 'raw MIR expression', 'Z3 input', 'Z3 simplified',
                      'rendered', 'input AST nodes', 'simplified AST nodes', 'input depth',
                      'simplified depth', 'ITE before', 'ITE after', 'status'], [
            '<comment>Z3 simplification is applied only to reconstructed merge expressions for display. '
            'The dependency and hot-variable merge-risk decision is unchanged.</comment>'
        ]

    def z3_table(self):
        rows = []
        for record in self.preview_records():
            raw_merge = record.get('ite_rhs')
            if raw_merge:
                rows.append(self.z3_row('merged value', record['site'], raw_merge,
                                        self.simplifier.simplify_text(raw_merge), record['variable']))
            raw_branch = record.get('expanded')
            if raw_branch:
                rows.append(self.z3_row('future branch', record['site'], raw_branch,
                                        self.simplifier.simplify_text(raw_branch), record['variable']))
        if not rows:
            rows.append(['No Z3 formulas', 'None', 'None', 'None', 'None', 'None', 'None',
                         '0', '0', '0', '0', '0', '0', 'not applicable'])
        return rows, ['context', 'site', 'variable', 'raw MIR expression', 'Z3 input',
                      'Z3 simplified', 'rendered', 'input AST nodes', 'simplified AST nodes',
                      'input depth', 'simplified depth', 'ITE before', 'ITE after', 'status'], [
            '<comment>Z3 simplification is a presentation layer over the existing ITE preview. '
            'It does not build symbolic states, call satisfiability checks, estimate solver cost, '
            'or change any QCE/CFG/SSA analysis result.</comment>'
        ]

    def z3_row(self, *args):
        if len(args) == 4:
            site, variable, raw, result = args
            prefix = [site, variable]
        else:
            context, site, raw, result, variable = args
            prefix = [context, site, variable]
        return prefix + [
            Z3FormulaSimplifier.html(raw),
            Z3FormulaSimplifier.html(result.z3_input),
            Z3FormulaSimplifier.html(result.z3_simplified),
            Z3FormulaSimplifier.html(result.rendered),
            str(result.raw_ast_size),
            str(result.simplified_ast_size),
            str(result.raw_depth),
            str(result.simplified_depth),
            str(result.raw_ite_count),
            str(result.simplified_ite_count),
            Z3FormulaSimplifier.status_text(result),
        ]

    def preview_records(self):
        records = []
        for block in range(self.dominator.N):
            preds = sorted(self.dominator.pred_list[block])
            for variable in sorted(self.phi.phi_args[block]):
                records.append(self.preview_record(block, preds, variable))
        return records

    def preview_record(self, block, preds, variable):
        base = {
            'block': block,
            'site': self.name(block),
            'variable': escape(variable),
            'ite_preview': 'None',
            'ite_rhs': None,
            'future_branch': 'None',
            'expanded': None,
            'metric_text': 'None',
            'ite_ops': '0',
            'ite_depth': '0',
            'expr_size': '0',
            'status': '',
        }
        if len(preds) != 2:
            base['status'] = f'unsupported arity: {len(preds)} predecessors'
            return base

        incoming = [(pred, self.incoming_condition(pred), self.expression_at_block_exit(pred, variable))
                    for pred in preds]
        if any(expr is None for _, _, expr in incoming):
            base['status'] = 'missing expression: source expression could not be reconstructed'
            return base

        ite_rhs = f'ite({incoming[0][1]}, {incoming[0][2]}, {incoming[1][2]})'
        ite_expr = f'{escape(variable)} = {ite_rhs}'
        future = self.future_branch(block, variable, ite_expr)
        metric_text = future['expanded'] or ite_expr
        ops, depth, size = self.metrics(metric_text)
        status = future['status']
        if size > self.max_expr_nodes:
            metric_text = self.truncate(metric_text)
            size = self.max_expr_nodes
            status = 'truncated'
        base.update({
            'ite_preview': self.truncate(ite_expr) if self.metrics(ite_expr)[2] > self.max_expr_nodes else ite_expr,
            'ite_rhs': ite_rhs,
            'future_branch': future['branch'] or 'None',
            'expanded': future['expanded'],
            'metric_text': metric_text if future['expanded'] else 'None',
            'ite_ops': str(ops),
            'ite_depth': str(depth),
            'expr_size': str(size),
            'status': status,
        })
        return base

    @staticmethod
    def preview_row(record):
        return [
            record['site'],
            record['variable'],
            record['ite_preview'],
            record['future_branch'],
            record['metric_text'],
            record['ite_ops'],
            record['ite_depth'],
            record['expr_size'],
            record['status'],
        ]

    def status_row(self, block, variable, status, reason):
        return [self.name(block), escape(variable), 'None', 'None', 'None',
                '0', '0', '0', f'{status}: {reason}']

    def expression_at_block_exit(self, block, variable):
        env = {}
        result = None
        for line in self.hot_variables.lexemes[block]:
            assignment_at = HotVariableDump.assignment_operator_index(line)
            if assignment_at is None:
                continue
            target = line[assignment_at - 1]
            if target[0] != 0:
                continue
            env[target[1]] = self.format_rhs(line[assignment_at + 1:], env, depth=2)
            if target[1] == variable:
                result = env[target[1]]
        return result

    def future_branch(self, start_block, variable, ite_assignment):
        ite_expr = ite_assignment.split(' = ', 1)[1]
        queue = [(start_block, {variable: ite_expr})]
        seen = set()
        while queue:
            block, incoming_env = queue.pop(0)
            if block in seen:
                continue
            seen.add(block)
            expr_env = dict(incoming_env)
            for line in self.hot_variables.lexemes[block]:
                assignment_at = HotVariableDump.assignment_operator_index(line)
                condition_at = SymbolicBranchDump.index_of_type(line, 5)
                goto_at = SymbolicBranchDump.index_of_type(line, 6)
                if assignment_at is not None:
                    target = line[assignment_at - 1]
                    if target[0] == 0:
                        rhs = line[assignment_at + 1:]
                        expr_env[target[1]] = self.format_rhs(rhs, expr_env, depth=2)
                if condition_at is not None and goto_at is not None:
                    tokens = line[condition_at + 1:goto_at]
                    syntactic_vars = {token[1] for token in tokens if token[0] == 0}
                    condition = self.format_condition(tokens, expr_env)
                    if 'ite(' in condition or variable in syntactic_vars:
                        return {
                            'branch': f'{self.name(block)}: {SymbolicBranchDump.format_expression(tokens)}',
                            'expanded': condition,
                            'status': 'shallow',
                        }
            for successor in sorted(self.hot_variables.edges[block] - seen):
                queue.append((successor, dict(expr_env)))
        return {'branch': None, 'expanded': None, 'status': 'no future branch'}

    def incoming_condition(self, pred):
        prefixes = self.branches.path_prefixes.get(pred, [])
        if len(prefixes) == 1:
            return SymbolicBranchDump.format_paths(prefixes)
        return f'path({self.name(pred)})'

    def format_rhs(self, tokens, env, depth):
        if len(tokens) >= 3 and tokens[0][0] == 2 and tokens[0][2] == 3:
            left = self.format_value(tokens[1], env, depth)
            right = self.format_value(tokens[2], env, depth)
            return f'{left} {escape(tokens[0][1])} {right}'
        return SymbolicBranchDump.format_expression([self.substitute_token(token, env, depth) for token in tokens])

    def format_condition(self, tokens, env):
        if len(tokens) >= 3 and tokens[1][0] == 2 and tokens[1][2] == 4:
            return f'{self.format_value(tokens[0], env, 2)} {escape(tokens[1][1])} {self.format_value(tokens[2], env, 2)}'
        return SymbolicBranchDump.format_expression([self.substitute_token(token, env, 2) for token in tokens])

    def format_value(self, token, env, depth):
        if token[0] == 0 and token[1] in env and depth > 0:
            return env[token[1]]
        return SymbolicBranchDump.format_token(token)

    def substitute_token(self, token, env, depth):
        if token[0] == 0 and token[1] in env and depth > 0:
            return [0, env[token[1]], [], False, False]
        return token

    @staticmethod
    def metrics(text):
        ops = text.count('ite(')
        depth = 0
        max_depth = 0
        idx = 0
        stack = []
        while idx < len(text):
            if text.startswith('ite(', idx):
                depth += 1
                max_depth = max(max_depth, depth)
                stack.append('ite')
                idx += 4
                continue
            if text[idx] == '(':
                stack.append('paren')
            if text[idx] == ')' and depth:
                marker = stack.pop() if stack else 'ite'
                if marker == 'ite':
                    depth -= 1
            idx += 1
        size = len(text.replace('(', ' ').replace(')', ' ').replace(',', ' ').split())
        return ops, max_depth, size

    def truncate(self, text):
        parts = text.split()
        if len(parts) <= self.max_expr_nodes:
            return text
        return ' '.join(parts[:self.max_expr_nodes]) + ' ...'
