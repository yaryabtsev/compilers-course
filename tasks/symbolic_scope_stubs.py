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


