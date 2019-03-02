
import random
import copy
import sys

from pycparser import c_ast, c_parser, c_generator

def _find_fn(ast):
    for node in ast.ext:
        if isinstance(node, c_ast.FuncDef):
            return node
    assert False, "missing function"

def _visit_subexprs(top_node, callback):
    def rec(node, toplevel=False):
        if isinstance(node, c_ast.Assignment):
            node.rvalue = rec(node.rvalue)
        elif isinstance(node, c_ast.StructRef):
            node.name = rec(node.name)
        elif isinstance(node, (c_ast.Return, c_ast.Cast)):
            node.expr = rec(node.expr)
        elif isinstance(node, (c_ast.Constant, c_ast.ID)):
            if not toplevel:
                x = callback(node)
                if x: return x
        elif isinstance(node, c_ast.UnaryOp):
            if not toplevel:
                x = callback(node)
                if x: return x
            if node.op not in ['p++', 'p--', '++', '--', '&']:
                node.expr = rec(node.expr)
        elif isinstance(node, c_ast.BinaryOp):
            if not toplevel:
                x = callback(node)
                if x: return x
            node.left = rec(node.left)
            node.right = rec(node.right)
        elif isinstance(node, c_ast.Compound):
            for sub in node.block_items or []:
                rec(sub, True)
        elif isinstance(node, (c_ast.Case, c_ast.Default)):
            for sub in node.stmts or []:
                rec(sub, True)
        elif isinstance(node, c_ast.FuncCall):
            if not toplevel:
                x = callback(node)
                if x: return x
            if node.args:
                for i in range(len(node.args.exprs)):
                    node.args.exprs[i] = rec(node.args.exprs[i])
        elif isinstance(node, c_ast.ArrayRef):
            if not toplevel:
                x = callback(node)
                if x: return x
            node.name = rec(node.name)
            node.subscript = rec(node.subscript)
        elif isinstance(node, c_ast.Decl):
            if node.init:
                node.init = rec(node.init)
        elif isinstance(node, c_ast.For):
            if node.init:
                node.init = rec(node.init)
            node.stmt = rec(node.stmt, True)
        elif isinstance(node, c_ast.TernaryOp):
            if not toplevel:
                x = callback(node)
                if x: return x
            node.cond = rec(node.cond)
            node.iftrue = rec(node.iftrue)
            node.iffalse = rec(node.iffalse)
        elif isinstance(node, (c_ast.While, c_ast.DoWhile)):
            node.stmt = rec(node.stmt, True)
        elif isinstance(node, c_ast.Switch):
            node.cond = rec(node.cond)
            node.stmt = rec(node.stmt, True)
        elif isinstance(node, c_ast.If):
            node.cond = rec(node.cond)
            if node.iftrue:
                node.iftrue = rec(node.iftrue, True)
            if node.iffalse:
                node.iffalse = rec(node.iffalse, True)
        elif isinstance(node, (c_ast.TypeDecl, c_ast.PtrDecl, c_ast.ArrayDecl,
                c_ast.Typename, c_ast.EmptyStatement)):
            pass
        else:
            print("Node with unknown type!", file=sys.stderr)
            print(node, file=sys.stderr)
            exit(1)
        return node

    rec(top_node, True)

def _insert_decl(fn, decl):
    for index, item in enumerate(fn.body.block_items):
        if not isinstance(item, c_ast.Decl):
            break
    else:
        index = len(fn.body.block_items)
    fn.body.block_items[index:index] = [decl]

def _get_block_items(block, force):
    if isinstance(block, c_ast.Compound):
        ret = block.block_items or []
        if force and not block.block_items:
            block.block_items = ret
    else:
        ret = block.stmts or []
        if force and not block.stmts:
            block.stmts = ret
    return ret

class Randomizer():
    def get_current_source(self):
        return c_generator.CGenerator().visit(self.ast)

    def permute(self):
        ast = copy.deepcopy(self.start_ast)
        fn = _find_fn(ast)
        phase = 0
        einds = {}
        sumprob = 0
        targetprob = None
        found = None
        def rec(block):
            assert isinstance(block, (c_ast.Compound, c_ast.Case, c_ast.Default))
            after = []
            past_decls = False
            items = _get_block_items(block, False)
            for index, item in enumerate(items):
                if not isinstance(item, c_ast.Decl):
                    past_decls = True
                if past_decls:
                    after.append((block, index))
                if isinstance(item, c_ast.Compound):
                    rec(item)
                elif isinstance(item, (c_ast.For, c_ast.While, c_ast.DoWhile)):
                    rec(item.stmt)
                elif isinstance(item, c_ast.If):
                    if item.iftrue:
                        rec(item.iftrue)
                    if item.iffalse:
                        rec(item.iffalse)
                elif isinstance(item, c_ast.Switch):
                    if item.stmt:
                        rec(item.stmt)
                elif isinstance(item, (c_ast.Case, c_ast.Default)):
                    rec(item)
                def visitor(expr):
                    nonlocal sumprob
                    nonlocal found
                    eind = einds.get(id(expr), 0)
                    for place in after[::-1]:
                        prob = 1 / (1 + eind)
                        if isinstance(expr, (c_ast.ID, c_ast.Constant)):
                            prob *= 0.5
                        sumprob += prob
                        if phase == 1 and found is None and sumprob > targetprob:
                            var = c_ast.ID('new_var')
                            found = (place, expr, var)
                            return var
                        eind += 1
                    einds[id(expr)] = eind
                    return None
                _visit_subexprs(item, visitor)
            after.append((block, len(items)))

        rec(fn.body)
        phase = 1
        targetprob = random.uniform(0, sumprob)
        sumprob = 0
        einds = {}
        rec(fn.body)

        assert found is not None
        location, expr, var = found
        block, index = location
        assignment = c_ast.Assignment('=', var, expr)
        items = _get_block_items(block, True)
        items[index:index] = [assignment]
        typ = c_ast.TypeDecl(declname=var.name, quals=[],
                type=c_ast.IdentifierType(names=['int']))
        decl = c_ast.Decl(name=var.name, quals=[], storage=[], funcspec=[],
                type=typ, init=None, bitsize=None)
        _insert_decl(fn, decl)
        # print("replacing:", to_c(expr))
        self.ast = ast

    def __init__(self, start_ast):
        self.start_ast = start_ast
        self.ast = self.start_ast

