import logs
import sys


ISA = [
    ['op_nop', 0],
    ['op_ld', 2],
    ['op_movi', 3],
    ['op_st', 4],
    ['op_inc', 5],
    ['op_cmpi', 6],
    ['op_bnz', 7],
    ['op_halt', 8]
]

op_decode_dir = {}   # opcode -> name
op_encode_dir = {}   # name -> opcode
op_execute_dir = {}  


for name, i in ISA:
    op_decode_dir[i] = name 
    op_encode_dir[name] = i


def uint64(x): return x & ((1 << 64) - 1)


class Cpu:
    def __init__(self):
        self.pc = 0             # program counter
        self.reg = [0]*12       # 64-bit 2's complement
        self.mem = bytearray(4) # memory

    def load_program(self, path):
        with open(path, 'rb') as f:
            self.mem = bytearray(f.read())
        self.memsize = len(self.mem)

    def step(self):
        global op_decode_dir 
        global op_execute_dir
        if self.pc < 0 or self.pc >= self.memsize or self.pc & 3:
            logs.error(f"invalid pc {self.pc}")
            sys.exit(-1)
        inst = self.mem[self.pc:self.pc+4]
        opcode = inst[0]
        if not opcode in op_decode_dir.keys():
            logs.error("invalid opcode {}".format(bin(opcode)))
            inst = bytearray(4) 
        inst_name = op_decode_dir[inst[0]]
        logs.error("pc = {:<10}, inst = {}".format(self.pc, inst_name))
        op_execute_dir[inst_name](inst)      # call executor
          

    def run(self, max_step=1000):
        for i in range(max_step):
            self.step()

    def print_regs(self):
        logs.error("---------- Registers ----------")
        logs.error("{:>3}{:>66}{:>20}{:>22}{:>22}".format(' ', 'binary', 'hex', 'unsigned', 'signed'))
        for i in self.reg:
            self.print_one_reg(i)

    def print_one_reg(self, x):
        overflow = 'no'
        if x >> 64:
            overflow = 'yes'
        # unsigned
        x = uint64(x)
        # hex
        hexadecimal = hex(x)
        # binary
        binary = '{:0>64}'.format(bin(x)[2:])
        # signed
        signed = x
        if x >> 63:  # negative
            signed = - uint64(~ x + 1)
        logs.error("{:>3}{:>66}{:>20}{:>22}{:>22}".format(overflow, binary, hexadecimal, x, signed))


    def op_nop(self, inst):
        self.pc += 4
        logs.error("nop")
        return

logs._init()
cpu = Cpu()

for name, _ in ISA:
    if hasattr(cpu,name):
        op_execute_dir[name] = getattr(cpu,name)
        logs.error('[instruction] {:<10} support'.format(name))
    else:
        op_execute_dir[name] = getattr(cpu,'op_nop')
        logs.error('[instruction] {:<10} not support'.format(name))

cpu.load_program(sys.argv[1])
logs.error(f'[bin] {sys.argv[1]} load, mem_size ={cpu.memsize}')

cpu.run()





