import lark
from lark import Lark

_op_arith = ['op_add', 'op_sub', 'op_mul', 'op_div', 'op_mod',
          'cmp_eq', 'cmp_ne', 'cmp_gt', 'cmp_lt', 'cmp_ge', 'cmp_le',
          'op_and', 'op_or', 'op_not', 'op_neg']

_op = ['var', 'arg', 'push', 'pop', 'print', 'jz', 'jnz', 'jmp', 'ret']

class GenPcode:
    def __init__(self, filepath:str):
        with open("tinyc.lark", 'r', encoding='utf-8') as f:
            grammar = f.read()
        tinyc_parser = Lark(grammar, start="program", lexer="standard")

        with open(filepath, "r", encoding="utf8") as f:
            text = f.read()
        self.tree = tinyc_parser.parse(text)    # root = program
        self.pcodes = []                        # list of pcodes
        self.tag = 0                            # loop_0, loop_1, ...
        self.loop_tags = []                     # [(loop_0, endloop_0),...]

    def gen(self, filepath:str):
        for func in self.tree.children:
            self.function(func)
        with open(filepath, 'w+', encoding='utf-8') as f:
            for line in self.pcodes:
                f.write(line+'\n')
        

    def function(self, root: lark.Tree):
        _, name, args, body = root.children
        self._pcode(f"def {name}:",name.line)                 # function name
        for func_arg in args.children:                        # function args
            token = func_arg.children[1]
            self._pcode(f"arg {token}", token.line)
        self._call(body)
            
    def stmtblock(self, root: lark.Tree):
        for stmt in root.children:
            self._call(stmt)

    def var_declar(self, root: lark.Tree):
        token = root.children[1]
        self._pcode(f"var {token}", token.line)

    def assignstmt(self, root: lark.Tree):
        self._bottom_up(root.children[1])           # expr
        token = root.children[0]
        self._pcode(f"pop {token}", token.line)
        
    def expr_stmt(self, root):
        self._bottom_up(root.children[0])
        self._pcode("pop")

    def returnstmt(self, root):
        self._bottom_up(root.children[0])
        self._pcode("ret\n")

    def printstmt(self, root):
        token = root.children[0]
        self._pcode(f"print {token}", token.line)
        
    def ifstmt(self, root):
        curr_tag = self.tag 
        self.tag += 1
        self._pcode(f"_if_{curr_tag}")              # if(
        self._bottom_up(root.children[0])           # expr
        self._pcode(f"jz _else_{curr_tag}")         # )
        self.stmtblock(root.children[1])            # {...
        self._pcode(f"jmp _endif_{curr_tag}")       # }
        self._pcode(f"_else_{curr_tag}")            # else 
        if len(root.children) > 2: 
            self.stmtblock(root.children[2])        # {...
        self._pcode(f"_endif_{curr_tag}")           # }
        
    def whilestmt(self, root):
        curr_tag = self.tag 
        self.tag += 1 
        begin = f"_loop_{curr_tag}"
        end = f"_endloop_{curr_tag}"
        self.loop_tags.append((begin,end))
        self._pcode(begin)                          # while(
        self._bottom_up(root.children[0])           # expr
        self._pcode(f"jz {end}")                    # )
        self.stmtblock(root.children[1])            # { ... 
        self._pcode(f"jmp {begin}")                 # }
        self._pcode(end)
        self.loop_tags.pop()

    def breakstmt(self, root):
        begin, end = self.loop_tags[-1]
        self._pcode(f"jmp {end}")

    def continuestmt(self, root):
        begin, end = self.loop_tags[-1]
        self._pcode(f"jmp {begin}")

    def _bottom_up(self, root: lark.Tree):
        if root.data in ["push_immd", "push_var"]:  # leaf node
            token = root.children[0]
            self._pcode(f"push {token}", token.line)
            return 
        elif root.data == "callexpr":           # function call
            self._pcode(f"push 0")              # push ret value
            for child in root.children[1:]:     # push args
                self._bottom_up(child) 
            token = root.children[0]
            self._pcode(f"@{token}", token.line)
            return
        # else
        for child in root.children:
            self._bottom_up(child) 

        opcode = root.data          # self
        if opcode in _op_arith:
            self._pcode(opcode)
        else:
            print("[error] no such operator", opcode)

    def _call(self, root: lark.Tree):
        if hasattr(self, root.data):
            getattr(self, root.data)(root)
        else:
            print("[error] no such rule", root.data)

    def _pcode(self, s: str, n = None):
        if s[-1] != ":":
            if s[0] != "_":
                s = '        ' + s
        extra = "" if not n else f" // line: {n}"
        self.pcodes.append("{:<40}".format(s) + extra)
        print(self.pcodes[-1])

    def print_tree(self):
        print(self.tree.pretty())



if __name__ == '__main__':

    tree = GenPcode("c/tinyc.c")
    tree.gen("c/tinyc.asm")
