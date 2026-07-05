import re
import os
from dataclasses import dataclass
from html import escape, unescape


try:
    import z3
except ImportError:  # pragma: no cover - exercised through disabled fallback tests.
    z3 = None


class UnsupportedExpression(Exception):
    pass


@dataclass
class SimplificationResult:
    raw: str
    z3_input: str
    z3_simplified: str
    rendered: str
    simplified: str
    raw_ast_size: int
    simplified_ast_size: int
    raw_depth: int
    simplified_depth: int
    raw_ite_count: int
    simplified_ite_count: int
    status: str
    reason: str = ''


class Z3FormulaSimplifier:
    TOKEN_RE = re.compile(
        r'\s*(<=|>=|==|!=|&&|\|\||[()+\-*,<>]=?|=|#?-?\d+|[A-Za-z_@][A-Za-z0-9_@]*|.)'
    )

    def __init__(self, enabled=None):
        self.enabled = self.default_enabled() if enabled is None else enabled
        self.variables = {}

    @staticmethod
    def is_available():
        return z3 is not None

    @staticmethod
    def default_enabled():
        return os.environ.get('MIR_DUMPER_Z3', '1').lower() not in {'0', 'false', 'no', 'off'}

    def simplify_text(self, text: str) -> SimplificationResult:
        raw = self.clean_text(text)
        if not self.enabled:
            return self.failure(raw, 'z3-disabled', 'z3 simplification disabled')
        if z3 is None:
            return self.failure(raw, 'z3-unavailable', 'z3-solver is not installed')
        try:
            expr = self.to_z3(raw)
            z3_input = self.format_z3(expr)
            simplified_expr = z3.simplify(expr)
            z3_simplified = self.format_z3(simplified_expr)
            rendered = self.render_z3(simplified_expr)
        except (UnsupportedExpression, z3.Z3Exception) as exc:
            return self.failure(raw, 'unsupported-expression', str(exc))

        raw_ast_size = self.ast_size(expr)
        simplified_ast_size = self.ast_size(simplified_expr)
        raw_ite_count = self.ast_ite_count(expr)
        simplified_ite_count = self.ast_ite_count(simplified_expr)
        raw_depth = self.ast_depth(expr)
        simplified_depth = self.ast_depth(simplified_expr)
        status = self.status(z3_input, z3_simplified, raw_ast_size, simplified_ast_size,
                             raw_ite_count, simplified_ite_count, raw_depth, simplified_depth, simplified_expr)
        return SimplificationResult(
            raw=raw,
            z3_input=z3_input,
            z3_simplified=z3_simplified,
            rendered=rendered,
            simplified=z3_simplified,
            raw_ast_size=raw_ast_size,
            simplified_ast_size=simplified_ast_size,
            raw_depth=raw_depth,
            simplified_depth=simplified_depth,
            raw_ite_count=raw_ite_count,
            simplified_ite_count=simplified_ite_count,
            status=status,
        )

    def failure(self, raw, status, reason):
        return SimplificationResult(
            raw=raw,
            z3_input='None',
            z3_simplified='None',
            rendered='None',
            simplified=raw,
            raw_ast_size=0,
            simplified_ast_size=0,
            raw_depth=0,
            simplified_depth=0,
            raw_ite_count=0,
            simplified_ite_count=0,
            status=status,
            reason=reason,
        )

    def to_z3(self, text):
        self.variables = {}
        parser = _ExpressionParser(self.tokenize(text), self)
        expr = parser.parse()
        parser.expect_end()
        return expr

    def var(self, name):
        if name not in self.variables:
            self.variables[name] = z3.Int(name)
        return self.variables[name]

    @classmethod
    def tokenize(cls, text):
        tokens = []
        index = 0
        while index < len(text):
            match = cls.TOKEN_RE.match(text, index)
            if not match:
                raise UnsupportedExpression(f'cannot tokenize near {text[index:index + 12]!r}')
            token = match.group(1)
            index = match.end()
            if token.strip():
                tokens.append(token)
        return tokens

    @staticmethod
    def clean_text(text):
        cleaned = str(text)
        cleaned = re.sub(r'<sub>(.*?)</sub>', r'_\1', cleaned)
        cleaned = re.sub(r'</?[A-Za-z][^>]*>', '', cleaned)
        cleaned = unescape(cleaned)
        replacements = {
            '¬': 'not',
            '∧': 'and',
            '∨': 'or',
            '&&': 'and',
            '||': 'or',
        }
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        return ' '.join(cleaned.split())

    @staticmethod
    def format_z3(expr):
        text = str(expr).replace('\n', ' ')
        text = re.sub(r'\s+', ' ', text)
        return (
            text.replace('If(', 'ite(')
            .replace('And(', 'and(')
            .replace('Or(', 'or(')
            .replace('Not(', 'not(')
        )

    @classmethod
    def render_z3(cls, expr):
        if z3 is None:
            return 'None'
        return cls._render_expr(expr)

    @classmethod
    def _render_expr(cls, expr):
        kind = expr.decl().kind()
        if z3.is_true(expr):
            return 'true'
        if z3.is_false(expr):
            return 'false'
        if z3.is_int_value(expr):
            return str(expr.as_long())
        if kind == z3.Z3_OP_UNINTERPRETED and expr.num_args() == 0:
            return str(expr)
        if kind == z3.Z3_OP_ITE:
            return f'ite({cls._render_expr(expr.arg(0))}, {cls._render_expr(expr.arg(1))}, {cls._render_expr(expr.arg(2))})'
        if kind == z3.Z3_OP_NOT and expr.num_args() == 1:
            child = expr.arg(0)
            comparison = cls._render_negated_comparison(child)
            if comparison:
                return comparison
            return f'not({cls._render_expr(child)})'
        if kind in {z3.Z3_OP_LT, z3.Z3_OP_LE, z3.Z3_OP_GT, z3.Z3_OP_GE, z3.Z3_OP_EQ} and expr.num_args() == 2:
            return cls._render_comparison(expr.arg(0), cls._comparison_symbol(kind), expr.arg(1))
        if kind == z3.Z3_OP_ADD:
            return cls._render_add(expr)
        if kind == z3.Z3_OP_MUL:
            return cls._render_mul(expr)
        return cls.format_z3(expr)

    @classmethod
    def _render_negated_comparison(cls, expr):
        kind = expr.decl().kind()
        if kind == z3.Z3_OP_LE:
            return cls._render_comparison(expr.arg(0), '>', expr.arg(1))
        if kind == z3.Z3_OP_LT:
            return cls._render_comparison(expr.arg(0), '>=', expr.arg(1))
        if kind == z3.Z3_OP_GE:
            return cls._render_comparison(expr.arg(0), '<', expr.arg(1))
        if kind == z3.Z3_OP_GT:
            return cls._render_comparison(expr.arg(0), '<=', expr.arg(1))
        if kind == z3.Z3_OP_EQ:
            return cls._render_comparison(expr.arg(0), '!=', expr.arg(1))
        return ''

    @classmethod
    def _render_comparison(cls, left, op, right):
        if z3.is_int_value(left) and left.as_long() == 0 and op == '<=':
            return f'{cls._render_expr(right)} >= 0'
        if z3.is_int_value(left) and left.as_long() == 0 and op == '<':
            return f'{cls._render_expr(right)} > 0'
        if z3.is_int_value(left) and left.as_long() == 0 and op == '>=':
            return f'{cls._render_expr(right)} <= 0'
        if z3.is_int_value(left) and left.as_long() == 0 and op == '>':
            return f'{cls._render_expr(right)} < 0'
        return f'{cls._render_expr(left)} {op} {cls._render_expr(right)}'

    @staticmethod
    def _comparison_symbol(kind):
        return {
            z3.Z3_OP_LT: '<',
            z3.Z3_OP_LE: '<=',
            z3.Z3_OP_GT: '>',
            z3.Z3_OP_GE: '>=',
            z3.Z3_OP_EQ: '=',
        }[kind]

    @classmethod
    def _render_add(cls, expr):
        parts = []
        for arg in expr.children():
            text = cls._render_expr(arg)
            if text.startswith('-'):
                parts.append(('-', text[1:]))
            else:
                parts.append(('+', text))
        if not parts:
            return '0'
        first_sign, first_text = parts[0]
        result = f'-{first_text}' if first_sign == '-' else first_text
        for sign, text in parts[1:]:
            result += f' {sign} {text}'
        return result

    @classmethod
    def _render_mul(cls, expr):
        children = expr.children()
        if len(children) == 2:
            left, right = children
            if z3.is_int_value(left) and left.as_long() == -1:
                return f'-{cls._render_expr(right)}'
            if z3.is_int_value(right) and right.as_long() == -1:
                return f'-{cls._render_expr(left)}'
        return ' * '.join(cls._render_expr(child) for child in children)

    @staticmethod
    def ast_size(expr):
        return 1 + sum(Z3FormulaSimplifier.ast_size(child) for child in expr.children())

    @staticmethod
    def ast_depth(expr):
        if expr.num_args() == 0:
            return 1
        return 1 + max(Z3FormulaSimplifier.ast_depth(child) for child in expr.children())

    @staticmethod
    def ast_ite_count(expr):
        current = 1 if expr.decl().kind() == z3.Z3_OP_ITE else 0
        return current + sum(Z3FormulaSimplifier.ast_ite_count(child) for child in expr.children())

    @staticmethod
    def html(text):
        return escape(str(text)) if text else 'None'

    @staticmethod
    def status_text(result):
        if result.reason and result.status in {'unsupported-expression', 'z3-disabled', 'z3-unavailable'}:
            return f'{result.status}: {escape(result.reason)}'
        return result.status

    @staticmethod
    def status(z3_input, z3_simplified, raw_ast_size, simplified_ast_size, raw_ite_count,
               simplified_ite_count, raw_depth, simplified_depth, simplified_expr):
        if z3.is_true(simplified_expr) or z3.is_false(simplified_expr) or z3.is_int_value(simplified_expr):
            return 'constant'
        if (simplified_ite_count < raw_ite_count
                or simplified_ast_size < raw_ast_size
                or simplified_depth < raw_depth):
            return 'reduced'
        if z3_simplified == z3_input:
            return 'unchanged'
        return 'normalized'


class _ExpressionParser:
    COMPARISONS = {'<', '<=', '>', '>=', '==', '=', '!='}

    def __init__(self, tokens, simplifier):
        self.tokens = tokens
        self.simplifier = simplifier
        self.index = 0

    def parse(self):
        return self.parse_or()

    def parse_or(self):
        expr = self.parse_and()
        while self.match_word('or'):
            expr = z3.Or(expr, self.parse_and())
        return expr

    def parse_and(self):
        expr = self.parse_not()
        while self.match_word('and'):
            expr = z3.And(expr, self.parse_not())
        return expr

    def parse_not(self):
        if self.match_word('not'):
            return z3.Not(self.parse_not())
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_additive()
        if self.peek() in self.COMPARISONS:
            op = self.advance()
            right = self.parse_additive()
            if op in ('=', '=='):
                return left == right
            if op == '!=':
                return left != right
            if op == '<':
                return left < right
            if op == '<=':
                return left <= right
            if op == '>':
                return left > right
            if op == '>=':
                return left >= right
        return left

    def parse_additive(self):
        expr = self.parse_multiplicative()
        while self.peek() in ('+', '-'):
            op = self.advance()
            right = self.parse_multiplicative()
            expr = expr + right if op == '+' else expr - right
        return expr

    def parse_multiplicative(self):
        expr = self.parse_unary()
        while self.peek() == '*':
            self.advance()
            expr = expr * self.parse_unary()
        return expr

    def parse_unary(self):
        if self.peek() == '-':
            self.advance()
            return -self.parse_unary()
        return self.parse_primary()

    def parse_primary(self):
        token = self.advance()
        if token is None:
            raise UnsupportedExpression('unexpected end of expression')
        lowered = token.lower()
        if lowered == 'true':
            return z3.BoolVal(True)
        if lowered == 'false':
            return z3.BoolVal(False)
        if re.fullmatch(r'#?-?\d+', token):
            return z3.IntVal(int(token.lstrip('#')))
        if lowered == 'ite':
            self.expect('(')
            condition = self.parse_or()
            self.expect(',')
            true_expr = self.parse_or()
            self.expect(',')
            false_expr = self.parse_or()
            self.expect(')')
            return z3.If(condition, true_expr, false_expr)
        if token == '(':
            expr = self.parse_or()
            self.expect(')')
            return expr
        if self.peek() == '(':
            raise UnsupportedExpression(f'unsupported function {token}(...)')
        if re.fullmatch(r'[A-Za-z_@][A-Za-z0-9_@]*', token):
            return self.simplifier.var(token)
        raise UnsupportedExpression(f'unsupported token {token!r}')

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else None

    def advance(self):
        token = self.peek()
        if token is not None:
            self.index += 1
        return token

    def match_word(self, word):
        if self.peek() and self.peek().lower() == word:
            self.index += 1
            return True
        return False

    def expect(self, token):
        actual = self.advance()
        if actual != token:
            raise UnsupportedExpression(f'expected {token!r}, got {actual!r}')

    def expect_end(self):
        if self.peek() is not None:
            raise UnsupportedExpression(f'unexpected token {self.peek()!r}')
