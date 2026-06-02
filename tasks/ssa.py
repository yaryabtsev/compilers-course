import copy
from collections import defaultdict


class Phi:
    def __init__(self, code_blocks, dominator):
        self.dominator = dominator
        self.code_blocks = []
        self.N = len(code_blocks)
        for i in range(self.N):
            if not dominator.available[i]:
                self.code_blocks.append([])
            else:
                self.code_blocks.append(copy.deepcopy(code_blocks[i]))
        self.globs = set()
        self.phis = set()
        self.blocks = defaultdict(set)
        self.phi_args = [set() for _ in range(self.N)]
        self.phi_pred_args = defaultdict(dict)
        # self.phis: List[dict]
        self.counter = defaultdict(int)
        self.stack = defaultdict(list)

    def globals_blocks(self):
        spoiler = []
        line_num = 1
        for node in range(self.N):
            spoiler += [['tab', 0], ['block', node], '<gb1>-block:</gb1>']
            def_block = set()
            spoiler += [['tab', 1], '<gb2>def<sub>',
                        ['block', node], '</sub>&nbsp;:&nbsp;</gb2>', ['set', copy.deepcopy(def_block)]]
            for line in self.code_blocks[node]:
                spoiler += [['tab', 2], ['line', [line], line_num]]
                for word in line:
                    if word[0] == 0 and not word[3] and word[1] not in def_block:
                        spoiler += [['tab', 3], '<gb3>Globals&nbsp;:&nbsp;</gb3>',
                                    ['set', copy.deepcopy(self.globs)],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['set', {word[1]}]]
                        self.globs.add(word[1])
                for word in line:
                    if word[0] == 0 and word[3]:
                        spoiler += [['tab', 3], '<gb2>def<sub>',
                                    ['block', node], '</sub>&nbsp;:&nbsp;</gb2>', ['set', copy.deepcopy(def_block)],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['set', {word[1]}]]
                        def_block.add(word[1])
                        spoiler += [['tab', 3], '<gb4>Blocks(<gb5>', word[1], '</gb5>)&nbsp;:&nbsp;</gb4>',
                                    ['block-set', copy.deepcopy(self.blocks[word[1]])],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['block-set', {node}]]
                        self.blocks[word[1]].add(node)
                line_num += 1
        return spoiler[1:]

    def locate(self) -> list:
        spoiler = []
        for var in self.globs:
            spoiler += [['tab', 0], f'<l id="1">variable</l>&nbsp;<w0>{var}</w0>:']
            work_list = list(self.blocks[var])
            spoiler += [['tab', 1], '<l id="2">WorkList</l> : ', ['block-set', copy.deepcopy(work_list)]]
            item = 0
            n = len(work_list)
            while item < n:
                for df in self.dominator.df_list[work_list[item]]:
                    if var not in self.phi_args[df]:
                        self.insert(df, var)
                        spoiler += [['tab', 1], '<l id="3">insert</l>&nbsp;', ['phi', f'{var}'],
                                    '&nbsp;in&nbsp;', ['block', df], '<gb1>-block:</gb1>']
                        self.phi_args[df].add(var)
                        self.phis.add(var)
                    if df not in work_list:
                        spoiler += [['tab', 1], '<l id="2">WorkList</l> : ', ['block-set', copy.deepcopy(work_list)],
                                    '&nbsp;<disj>&#8744;</disj>&nbsp;', ['set', {df}]]
                        work_list.append(df)
                        n += 1
                item += 1
        # self.phis = [{var: [0, []] for var in sorted(self.phi_args[block])} for block in range(self.dominator.N)]
        return spoiler[1:]

    def table_new_phi(self):
        columns = ["block ="] + list(range(self.N))
        table = []
        for var in sorted(self.blocks):
            row = [var]
            for i in range(self.N):
                if var in self.phi_args[i]:
                    row.append(True)
                else:
                    row.append(False)
            table.append(row)
        return table, columns

    def rename(self, block: int, tabs: int = 0) -> list:
        spoiler = [['tab', tabs], '<r id="1">Rename(', ['block', block], ')</r>:']
        self.rename_phi(block, tabs, spoiler)
        self.rename_instructions(block, tabs, spoiler)
        for successor in self.dominator.edges[block]:
            self.fill(block, successor, tabs, spoiler)
        for successor in self.dominator.dom_edges[block]:
            spoiler += self.rename(successor, tabs + 1)
            spoiler += [['tab', tabs + 2], '<r id="2">return to ', ['block', block], ';</r>']
        # show_table(self.stack_table())
        self.clean(block, tabs, spoiler)
        # show_table(self.stack_table())
        return spoiler

    def table_gb(self):
        columns = ["var ="] + sorted(self.blocks)
        table = []
        row = ["Blocks(var)"]
        for var in columns[1:]:
            if self.blocks[var]:
                row.append(self.blocks[var])
            else:
                row.append('None')
        table.append(row)
        row = ["is Global"]
        for var in columns[1:]:
            row.append(var in self.globs)
        table.append(row)
        return table, columns

    def checks(self):
        tracked = set(self.phis)
        all_vars = set()
        missing_defs = []
        missing_uses = []
        duplicate_defs = []
        phi_arity = []
        definitions = defaultdict(list)

        for block in range(self.N):
            for line_idx in range(len(self.code_blocks[block])):
                line = self.code_blocks[block][line_idx]
                if self.is_phi_line(block, line_idx):
                    var = line[-1]
                    args = self.indexes(var)
                    expected = len(self.dominator.pred_list[block])
                    if len(args) != expected:
                        phi_arity.append(f'{var[1]} in block {block}: {len(args)} / {expected}')
                for word in line:
                    if word[0] != 0:
                        continue
                    all_vars.add(word[1])
                    if word[1] not in tracked:
                        continue
                    indexes = self.indexes(word)
                    location = f'block {block}, line {line_idx + 1}'
                    if word[3]:
                        if not indexes:
                            missing_defs.append(f'{word[1]} at {location}')
                        for idx in indexes:
                            definitions[(word[1], idx)].append(location)
                    elif not word[4] and not indexes:
                        missing_uses.append(f'{word[1]} at {location}')

        for (var, idx), locations in definitions.items():
            if len(locations) > 1:
                duplicate_defs.append(f'{var}<sub>{idx}</sub>: {", ".join(locations)}')

        untracked = sorted(all_vars - tracked)
        rows = [
            ['SSA rename scope', 'partial' if tracked else 'none', self.format_names(tracked)],
            ['Untracked variables', 'not renamed', self.format_names(untracked)],
            ['Tracked definitions named', not missing_defs, self.format_notes(missing_defs)],
            ['Tracked uses named', not missing_uses, self.format_notes(missing_uses)],
            ['Unique tracked definitions', not duplicate_defs, self.format_notes(duplicate_defs)],
            ['Phi arity matches predecessors', not phi_arity, self.format_notes(phi_arity)],
        ]
        return rows, ['check', 'status', 'details'], [
            '<comment>Checks are scoped to variables selected by phi placement; '
            'other variables remain in the original MIR naming style.</comment>'
        ]

    @staticmethod
    def indexes(word):
        if type(word[2]) is int:
            return [word[2]]
        return list(word[2])

    @staticmethod
    def format_names(names):
        if not names:
            return 'None'
        return ', '.join([f'<w0>{name}</w0>' for name in sorted(names)])

    @staticmethod
    def format_notes(notes):
        if not notes:
            return 'ok'
        return '<br>'.join(notes)

    def rename_phi(self, block, tabs, spoiler):
        spoiler += [['tab', tabs + 1], '<r id="5">rename &phi;-functions:</r>']
        i = 0
        while self.is_phi_line(block, i):
            var = self.code_blocks[block][i][-1]
            self.code_blocks[block][i][-3][2].append(self.new_name(var[1]))
            spoiler.append(self.line(block, i))
            i += 1
        if i == 0:
            spoiler += [['tab', tabs + 2], '<r id="4">no &phi;-functions</r>']
        self.stack_snapshot(tabs + 2, spoiler)

    def rename_instructions(self, block, tabs, spoiler):
        spoiler += [['tab', tabs + 1], 'rename instructions:']
        i = 0
        while self.is_phi_line(block, i):
            i += 1
        flag = False
        while i < len(self.code_blocks[block]):
            for word in self.code_blocks[block][i][::-1]:
                if word[0] == 0 and word[1] in self.phis:
                    flag = True
                    if not self.stack[word[1]]:
                        self.new_name(word[1])
                    if not word[3]:
                        word[2].append(self.stack[word[1]][-1])
                    else:
                        word[2].append(self.new_name(word[1]))
            spoiler.append(self.line(block, i))
            i += 1
        if not flag:
            spoiler += [['tab', tabs + 2], '<r id="4">no instructions</r>']
        self.stack_snapshot(tabs + 2, spoiler)

    def clean(self, block, tabs, spoiler):
        spoiler += [['tab', tabs + 1], 'clean():']
        cleaned = False
        for line in self.code_blocks[block]:
            for word in line:
                if word[0] == 0 and word[3] and self.stack[word[1]]:
                    self.stack[word[1]].pop()
                    cleaned = True
        if not cleaned:
            spoiler += ['nothing to clean']
        self.stack_snapshot(tabs + 2, spoiler)

    def is_phi_line(self, node, i):
        return i < len(self.code_blocks[node]) and self.code_blocks[node][i] and \
               self.code_blocks[node][i][-1] and self.code_blocks[node][i][-1][0] == 0 \
               and self.code_blocks[node][i][-1][4]

    def fill(self, predecessor, successor, tabs, spoiler):
        spoiler += [['tab', tabs + 1], '<r id="3">fill(', ['block', successor], ')</r>:']
        i = 0
        while self.is_phi_line(successor, i):
            var = self.code_blocks[successor][i][-1]
            if not self.stack[var[1]]:
                self.new_name(var[1])
            idx = self.stack[var[1]][-1]
            self.phi_pred_args[(successor, var[1])][predecessor] = idx
            if idx not in var[2]:
                var[2].append(idx)
                var[2].sort()
            spoiler.append(self.line(successor, i))
            i += 1
        if i == 0:
            spoiler += ['<r id="4">no &phi;-functions</r>']
        self.stack_snapshot(tabs + 2, spoiler)

    def stack_snapshot(self, tabs, spoiler):
        active = []
        for var in sorted(self.stack):
            if self.stack[var]:
                active.append(f'<w0>{var}</w0>:[{", ".join(map(str, self.stack[var]))}]')
        if not active:
            spoiler += [['tab', tabs], '<r id="6">stack</r> : empty']
        else:
            spoiler += [['tab', tabs], '<r id="6">stack</r> : ', ',&nbsp;'.join(active)]

    def new_name(self, var):
        idx = self.counter[var]
        self.counter[var] += 1
        self.stack[var].append(idx)
        return idx

    def insert(self, df, var):
        new_line = [[0, var, [], True, False], [2, '<--', 2, False], [0, var, [], False, True]]
        if self.code_blocks[df] and self.code_blocks[df][0] and self.code_blocks[df][0][0] and \
                self.code_blocks[df][0][0][
                    0] == 1:
            new_line = [self.code_blocks[df][0][0]] + new_line
            self.code_blocks[df][0] = self.code_blocks[df][0][1:]
        self.code_blocks[df] = [new_line] + self.code_blocks[df]

    def line(self, successor, i):
        return ['line', [self.code_blocks[successor][i]],
                sum([len(self.code_blocks[block]) for block in range(successor)]) + i + 1]
