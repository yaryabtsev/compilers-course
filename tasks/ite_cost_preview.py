from html import escape

from tasks.branch_conditions import SymbolicBranchDump
from tasks.query_cost_estimation import HotVariableDump


class IteCostPreview:
    def __init__(self, phi, dominator, hot_variables, name, max_expr_nodes=40):
        self.phi = phi
        self.dominator = dominator
        self.hot_variables = hot_variables
        self.name = name
        self.max_expr_nodes = max_expr_nodes
        self.branches = SymbolicBranchDump(hot_variables.lexemes, hot_variables.edges, name)

    def table(self):
        rows = []
        for block in range(self.dominator.N):
            preds = sorted(self.dominator.pred_list[block])
            for variable in sorted(self.phi.phi_args[block]):
                rows.append(self.preview_row(block, preds, variable))
        if not rows:
            rows.append(['No ITE previews', 'None', 'None', 'None', 'None',
                         '0', '0', '0', 'no merge candidates'])
        return rows, ['merge site', 'variable', 'ite preview', 'future branch',
                      'expanded branch preview', 'ite ops', 'ite depth', 'expr size', 'status'], [
            '<comment>Syntactic shallow preview only: reconstructs small two-way join expressions, '
            'substitutes at most local assignment chains, and counts visible ite nodes. It is '
            'path-insensitive and is not an SMT formula, simplifier, runtime benchmark, or solver-cost estimate.</comment>'
        ]

    def preview_row(self, block, preds, variable):
        if len(preds) != 2:
            return self.status_row(block, variable, 'unsupported arity', f'{len(preds)} predecessors')

        incoming = [(pred, self.incoming_condition(pred), self.expression_at_block_exit(pred, variable))
                    for pred in preds]
        if any(expr is None for _, _, expr in incoming):
            return self.status_row(block, variable, 'missing expression', 'source expression could not be reconstructed')

        ite_expr = f'{escape(variable)} = ite({incoming[0][1]}, {incoming[0][2]}, {incoming[1][2]})'
        future = self.future_branch(block, variable, ite_expr)
        metric_text = future['expanded'] or ite_expr
        ops, depth, size = self.metrics(metric_text)
        status = future['status']
        if size > self.max_expr_nodes:
            metric_text = self.truncate(metric_text)
            size = self.max_expr_nodes
            status = 'truncated'
        return [
            self.name(block),
            escape(variable),
            self.truncate(ite_expr) if self.metrics(ite_expr)[2] > self.max_expr_nodes else ite_expr,
            future['branch'] or 'None',
            metric_text if future['expanded'] else 'None',
            str(ops),
            str(depth),
            str(size),
            status,
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
