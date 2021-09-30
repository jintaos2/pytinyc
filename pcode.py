import sys
import re
import logs
from lark import Lark, Token, Tree


grammar = r"""
program:  function (_WS_NEWLINE function)* 

function: "def" _WS_INLINE  funcname [_WS_INLINE] ":"  (_WS_NEWLINE line)+

funcname: NAME

?line:      TAG                                 -> linetag
            | "@" NAME                          -> funcall
            | "print" _WS_INLINE (NAME|STRING)  -> printstmt
            | NAME [_WS_INLINE (NAME|INTEGER)]  -> opstmt
            | NAME _WS_INLINE TAG               -> jmpstmt


NAME: /[a-zA-Z][_a-zA-Z0-9]*/
STRING: /".*?(?<!\\)"/
INTEGER: /\d+/ | /0x[\da-f]+/i | /0b[01]+/i
TAG: /_[_a-zA-Z0-9]*/

_WS_INLINE: /[ \t]+/ 
_COMMENT:   /\/\/.*/                      
_WS_NEWLINE.2: (/\s/|_COMMENT)* /[\r\n]/ (/\s/|_COMMENT)*

"""
pcode_parser = Lark(grammar, start="program", lexer="standard")

# print = logs.error

class int64:
    def __init__(self, x:int = 0):
        self.x = x
    def __repr__(self):
        return str(self.x)
    def __eq__(self, i):
        return int64(self.x == i.x)
    def __lt__(self, i):
        return int64(self.x < i.x)
    def __add__(self, i):
        return int64(self.x + i.x)
    def __or__(self, i):
        return int64(self.x | i.x)    
    def __neg__(self):
        return int64(-self.x)  
    def __mul__(self, i):
        return int64(self.x * i.x)  

class Program: 
    """stack: 
            ret_value
            arg0 
            arg1
            prev_ebp   
            ret_addr   
            var0       <- ebp
            var1 
            var2
    """
    def __init__(self, filename:str):

        with open(filename, 'r', encoding='utf8') as f:
            code = f.read().strip()

        self.tree = pcode_parser.parse(code)
        self.preprocess_func()          # add some inst

        self.tags = {}                  # tag_name -> bin location
        self.preprocess_tags()

        self.pcode = []                 # instructions 
        self.preprocess_names()         # arg_name -> stack location

        self.pc = int64()               # initial pc 
        self.ebp = int64()              # base stack pointer
        self.addr = int64()             # return address    
        self.stack = []      

    def preprocess_func(self):
        """
        funcall:  
            push ret_value; push a; push b; push ebp; push pc+1; stack.size -> ebp; jmp func
        ret: 
            stack.resize(ebp); pop addr;  pop ebp; pop a; pop b; jmp addr
        """
        for func in self.tree.children:
            children_new = []
            func.n_args = 0
            for line in func.children:
                if line.data == "funcname":
                    func_name = line.children[0].value
                    children_new.append(Tree("linetag",[Token("TAG", func_name)]))
                elif line.data == "funcall":
                    func_name = line.children[0].value
                    children_new.append(Tree("opstmt", [Token("NAME", "push"), Token("REG", "@ebp")]))
                    # push pc+1;  stack.size -> ebp; jmp func
                    children_new.append(Tree("jmpstmt", [Token("NAME", "jal"), Token("TAG", func_name)]))
                elif line.data == "opstmt" and line.children[0] == "ret":
                    children_new.append(Tree("opstmt", [Token("NAME", "pop"), Token("ARG", -3-func.n_args)]))
                    children_new.append(Tree("stack", [Token("NAME", "resize")]))
                    children_new.append(Tree("opstmt", [Token("NAME", "pop"), Token("REG", "@addr")]))
                    children_new.append(Tree("opstmt", [Token("NAME", "pop"), Token("REG", "@ebp")]))
                    for i in range(func.n_args):
                        children_new.append(Tree("opstmt", [Token("NAME", "pop")]))
                    children_new.append(Tree("opstmt", [Token("NAME", "jmp"), Token("REG", "@addr")]))
                else: 
                    children_new.append(line)
                    if line.data == "opstmt" and line.children[0] == "arg":
                        func.n_args += 1
            func.children = children_new

    def preprocess_tags(self):
        n_inst = 0
        for func in self.tree.children:
            children_new = []
            func.args = {}
            curr_arg = -2
            curr_var = 0
            for line in func.children:
                if line.data == "opstmt" and line.children[0] == "arg":
                    func.args[line.children[1].value] = curr_arg - func.n_args
                    curr_arg += 1 
                elif line.data == "opstmt" and line.children[0] == "var":
                    func.args[line.children[1].value] = curr_var
                    curr_var += 1 
                    children_new.append(Tree("opstmt", [Token("NAME", "push"), Token("INTEGER", "0")]))
                    n_inst += 1 
                elif line.data == "linetag":
                    self.tags[line.children[0].value] = n_inst 
                else:
                    children_new.append(line)
                    n_inst += 1 

            func.children = children_new
            
    def preprocess_names(self):
        for func in self.tree.children:
            for line in func.children:
                if line.data == "jmpstmt":
                    line.children[1].value = self.tags[line.children[1]] 
                elif line.data == "opstmt" and len(line.children) > 1:
                    if line.children[1].type == "NAME":
                        line.children[1] = Token("ARG", func.args[line.children[1]])
                    elif line.children[1].type == "INTEGER":
                        line.children[1].value = int64(int(line.children[1].value))
                elif line.data == "printstmt" and line.children[0].type == "NAME":
                    line.children[0] = Token("ARG", func.args[line.children[0]])

                self.pcode.append(line)
                

    def op_push(self, args: list):
        val = self._getvalue(args[1])
        self.stack.append(int64(val.x))

    def op_pop(self, args:list):
        a = self.stack.pop()
        if len(args) > 1:
            self._getvalue(args[1]).x = a.x

    def op_stack(self, args:list):
        if args[0] == "resize":
            self.stack = self.stack[:self.ebp.x]   # ebp -> esp
        else: 
            print(f"invalid stack operation {args[0]}")
            
    def op_op_add(self, args: list):
        self.stack.append(self.stack.pop()+self.stack.pop())
    def op_op_sub(self, args: list):
        self.stack.append(-self.stack.pop()+self.stack.pop())
    def op_op_or(self, args: list):
        self.stack.append(self.stack.pop()|self.stack.pop())
    def op_op_mul(self, args: list):
        self.stack.append(self.stack.pop()*self.stack.pop())

    def op_cmp_lt(self, args: list):
        b = self.stack.pop()
        a = self.stack.pop()
        self.stack.append(a < b)

    def op_cmp_eq(self, args: list):
        self.stack.append(self.stack.pop() == self.stack.pop())

    def op_jz(self, args: list):
        if self.stack.pop().x == 0:
            self.pc.x = self._getvalue(args[1]).x   # tag or reg
    
    def op_jmp(self, args: list):
        self.pc.x = self._getvalue(args[1]).x       # tag or reg

    def op_jal(self, args: list):
        self.stack.append(int64(self.pc.x))
        self.ebp.x = len(self.stack)
        self.pc.x = self._getvalue(args[1]).x       # tag

    def op_print(self, args:list):
        token = args[0]
        if token.type == "STRING":
            print(f">>> {token.value}")
        elif token.type == "ARG":
            i = self._getvalue(token).x
            print(f">>> {i}")

    def run(self):
        self.stack = [int64(-1), int64(0), int64(-1)]       # return value; init_ebp;  return address;
        self.ebp.x = 3                                      # main_ebp  
        self.pc.x = self.tags["main"]                       # jmp
        print("start!")
        while self.pc.x >= 0 and len(self.stack) < 5000:
            self._run()
        print("finish!")

    def _getvalue(self, token:Token):
        if token.type == "INTEGER":
            return int64(token.value.x)
        elif token.type == "TAG":
            return int64(token.value)
        elif token.type == "ARG":
            return self.stack[self.ebp.x + token.value]
        elif token.type == "REG":
            name = token.value[1:]
            if hasattr(self, name):
                ret = getattr(self, name)
                if isinstance(ret, int64):
                    return ret 
            print(f"no such reg: {name}")
        print(f"cannot get value of {token}")
    

    def _run(self):
        inst = self.pcode[self.pc.x]
        n = inst.children[0].line
        # print("pc={:<4} ebp={:<4} esp={:<4} addr={:<4} line:{:<4} inst:{}".format(
        #             self.pc.x, self.ebp.x, len(self.stack), self.addr.x, "" if n == None else n, inst))
        self.pc.x += 1 
        if inst.data in ["opstmt", "jmpstmt"]:
            opcode = "op_" + inst.children[0].value
        elif inst.data == "stack":
            opcode = "op_stack"
        elif inst.data == "printstmt":
            opcode = "op_print"
            
        if hasattr(self, opcode):
            getattr(self,opcode)(inst.children)
        else:
            print(f"invalid opcode: {opcode}")
            self.pc.x = -1
        # print(f"stack: {self.stack}")
        


if __name__ == "__main__":
    logs._init()
    p = Program("c/tinyc.asm")
    
    # for i in p.pcode:
    #     print(i)

    p.run()

    # cpu = Cpu(sys.argv[1])

