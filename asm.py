import re 
import logging
import os


# 14, -2, 0xae, -0x34, 0b1110, -0b101, ...
def str2int(a:str)->int:
    
    check = re.match(r'^[+-]?(0b|0x|0o)?[abcdef0-9]+$',a,re.IGNORECASE)
    if not check:
        logger.info('[error] invaild value: {}'.format(a))
        return 0
    base = 10
    base_check = check.groups()[0]
    if base_check in ['0b','0B']:
        base = 2
    elif base_check in ['0o','0O']:
        base = 8
    elif base_check in ['0x','0X']:
        base = 16 
    try:
        return int(a,base)
    except:
        logger.info('[error] invaild value: {}'.format(a))
        return 0
"""
convert signed integer to 2's Complement
"""
def int2bin(a:int, length:int)->str:
    mask = (1 << length) - 1
    mask_ = (1 << (length-1)) - 1
    overflow = a > mask_ or a < -(mask_ + 1)
    ret = bin(a & mask)[2:]
    return '0'*(length-len(ret))+ret, overflow
"""
convert 0000000111 to bytes b'\x07\x00\x00\x00'
"""
def str2bytes(a:str):
    return int(a,2).to_bytes(4,byteorder='little')

class ASM:
    def __init__(self, code:str):
        self.lines = []    # [('xxx', line_number)]
        N = -1
        for line in code.split('\n'):
            N += 1
            line = re.split(r'#', line)[0].strip()
            if not re.search(r'\w', line):
                continue
            tag = re.match(r'[\w]+?:',line)
            if tag:
                idx = tag.span()[1]
                self.lines.append((line[:idx],N))
                line = line[idx:].strip()
                if not re.search(r'\w', line):
                    continue
            self.lines.append((line,N))
        logger.info("--------- precheck done ---------")
        for i in self.lines:
            logger.info(i)
        logger.info("--------- pseduo ---------")
        self.pseduo()
        logger.info("--------- pseduo done ---------")
        for i in self.units:
            i.show()
        for i in self.units:
            i.decode(self.tags)
        logger.info("--------- decode done ---------")
        for i in self.units:
            i.show_bytes()
        
    def pseduo(self):
        self.tags = {}
        self.mem_addr = 0
        self.units = []
        
        for line, N in self.lines:
            if re.match(r'^[A-Za-z][\w]*:$',line):
                tag_name = line[:-1]
                if tag_name in self.tags.keys():
                    logger.info("[error] tags used twice!")
                    return
                self.tags[tag_name] = self.mem_addr
            else:
                self.units.append(Unit(line, N, self.mem_addr))
                self.mem_addr = self.units[-1].next_mem_addr
        logger.info('found tags: {}'.format(self.tags))
        
class Unit:
    
    vaild_pseduo = ['.word','.dword','.addr', '.string', '.byte']
    
    def __init__(self, content, N, mem_addr):
        self.mem_addr = mem_addr 
        self.next_mem_addr = mem_addr
        self.content = content 
        self.line_num = N
        self.binary = bytes()
        if content[0] == '.':
            self.types = 'data' 
            self.handle_data()
        else:  # is instruction
            self.mem_addr = (self.mem_addr + 3) >> 2 << 2  # aligned 4 bytes
            self.types = 'instruction'
            self.next_mem_addr = self.mem_addr + 4
            
    def handle_data(self):
        r = re.match(r'(.[\w]+?)[\s]+([\S].*)', self.content)
        if not r or len(r.groups()) != 2:
            logger.info(f"[error:{self.line_num}] invalid line: {self.content}")
            return
        name = r.groups()[0]
        values = re.split(r'[\s,]+',r.groups()[1])
        if not name in self.vaild_pseduo:
            logger.info(f'[error:{self.line_num}] invaild pesduo: {name}')
            return
        if name == '.addr':
            self.next_mem_addr = str2int(values[0])
            if self.next_mem_addr < self.mem_addr:
                logger.info(f'[error:{self.line_num}] address too small: {self.next_mem_addr}')
                return 
            self.binary = b'\x00' * (self.next_mem_addr - self.mem_addr) 
        elif name == '.byte':
            bins = [ (str2int(i)&0xff).to_bytes(length=1,byteorder='little',signed=False)  for i in values]
            self.next_mem_addr = self.mem_addr + len(bins)
            for i in bins:
                self.binary += i
        elif name == '.word':
            bins = [ (str2int(i)&0xffffffff).to_bytes(length=4,byteorder='little',signed=False)  for i in values]
            self.mem_addr = (self.mem_addr + 3) >> 2 << 2       # aligned 4 bytes
            self.next_mem_addr = self.mem_addr + len(bins) * 4
            for i in bins:
                self.binary += i
        elif name == '.dword':
            bins = [ (str2int(i)&0xffffffffffffffff).to_bytes(length=8,byteorder='little',signed=False)  for i in values]
            self.mem_addr = (self.mem_addr + 3) >> 2 << 2       # aligned 4 bytes
            self.next_mem_addr = self.mem_addr + len(bins) * 8
            for i in bins:
                self.binary += i     
        elif name == '.string':        # unicode
            str_converted = values[0][1:-1].encode().decode('unicode_escape')
            bins = [ (ord(i)&0xffffffff).to_bytes(length=4,byteorder='little',signed=False)  for i in str_converted]
            bins.append(b'\x00'*4)     # endpoint
            self.mem_addr = (self.mem_addr + 3) >> 2 << 2       # aligned 4 bytes
            self.next_mem_addr = self.mem_addr + len(bins) * 4
            for i in bins:
                self.binary += i            
        logger.info(f"[line:{self.line_num}\tmem:{self.mem_addr}] {name}:{self.binary.hex()}")
            
    
    def show(self):
        logger.info(f"{self.mem_addr}\t: {self.content}")
    def show_bytes(self):
        if self.types == 'instruction':
            b = '{:0>32b}'.format(int.from_bytes(self.binary,byteorder='little',signed=False))
            logger.info(f"[{self.mem_addr}\t: {self.content}]\t{b}")
        
    def decode(self, tags):
        if self.types == 'data':
            return 
        # instruction 
        self.tags = tags 
        r = re.match(r'([\w]+)[\s]+(.*)',self.content)
        if not r or len(r.groups()) != 2:
            logger.info(f"[error line:{self.line_num}\t] invaild instruction: {self.content}")
            return 
        self.inst_body = r.groups()[1]
        case = r.groups()[0]
        if case == 'addi':
            self.I_type('000')
        elif case == 'slti':
            self.I_type('010')
        elif case == 'sltiu':
            self.I_type('011')
        elif case == 'xori':
            self.I_type('100')
        elif case == 'ori':
            self.I_type('110')
        elif case == 'andi':
            self.I_type('111')
        elif case == 'slli':
            self.S_type('001','000000')
        elif case == 'srli':
            self.S_type('101','000000')
        elif case == 'srai':
            self.S_type('101','010000')
        elif case == 'lui':
            self.U_type('0110111')
        elif case == 'auipc':
            self.U_type('0010111')
        elif case == 'add':
            self.R_type('000','0000000')
        elif case == 'sub':
            self.R_type('000','0100000')
        elif case == 'sll':
            self.R_type('001','0000000')
        elif case == 'slt':
            self.R_type('010','0000000')
        elif case == 'sltu':
            self.R_type('011','0000000')
        elif case == 'xor':
            self.R_type('100','0000000')
        elif case == 'srl':
            self.R_type('101','0000000')
        elif case == 'sra':
            self.R_type('101','0100000')
        elif case == 'or':
            self.R_type('110','0000000')
        elif case == 'and':
            self.R_type('111','0000000')
        elif case == 'jal':
            self.J_jal()
        elif case == 'jalr':
            self.J_jalr()
        elif case == 'beq':
            self.B_type('000')
        elif case == 'bne':
            self.B_type('001')
        elif case == 'blt':
            self.B_type('100')
        elif case == 'bge':
            self.B_type('101')
        elif case == 'bltu':
            self.B_type('110')
        elif case == 'bgeu':
            self.B_type('111')
        elif case == 'lb':
            self.Load('000')
        elif case == 'lbu':
            self.Load('100')
        elif case == 'lw':
            self.Load('010')
        elif case == 'lwu':
            self.Load('110')
        elif case == 'ld':
            self.Load('011')
        elif case == 'sb':
            self.Store('000')
        elif case == 'sw':
            self.Store('010')
        elif case == 'sd':
            self.Store('011')
        else:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return 




    """  
    addi: imm12, rs1, 000, rd, 0010011
    slti:  010 
    sltiu: 011 
    xori:  100 
    ori:   110
    andi:  111
    """
    def I_type(self, funct3:str):
        ops = re.split(r'[\s,]+',self.inst_body)
        if len(ops) != 3:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return 
        rd = self.decode_reg(ops[0])
        rs1 = self.decode_reg(ops[1])
        immd, overflow = int2bin(str2int(ops[2]),12)
        if overflow:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return 
        self.binary = str2bytes(immd + rs1 + funct3 + rd + '0010011')     
    """
    slli: 000000 imm6 rs1 001 rd 0010011
    srli: 000000 imm6 rs1 101 rd 0010011
    slli: 010000 imm6 rs1 101 rd 0010011
    """
    def S_type(self, funct3:str, funct6:str):
        ops = re.split(r'[\s,]+',self.inst_body)
        if len(ops) != 3:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return 
        rd = self.decode_reg(ops[0])
        rs1 = self.decode_reg(ops[1])
        immd, overflow = int2bin(str2int(ops[2]),7)
        immd = immd[1:]                
        if overflow:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return 
        self.binary = str2bytes(funct6 + immd + rs1 + funct3 + rd + '0010011') 
    """
    lui:   imm[31:12] rd 0110111
    auipc: imm[31:12] rd 0010111
    """
    def U_type(self, opcode:str):
        ops = re.split(r'[\s,]+',self.inst_body)
        if len(ops) != 2:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return         
        rd = self.decode_reg(ops[0])
        if ops[1] in self.tags:
            immd = self.tags[ops[1]]
        else:
            immd = str2int(ops[1])
        immd, _ = int2bin(immd,32)
        immd = immd[0:20]
        self.binary = str2bytes(immd  + rd + opcode) 
        
    """
    add: 0000000 rs2 rs1 000 rd 0110011
    sub: 0100000         000           # sub rd, rs1, rs2: rs1-rs2 
    sll: 0000000         001
    slt: 0000000         010
    sltu:0000000         011
    xor: 0000000         100
    srl: 0000000         101
    sra: 0100000         101
    or : 0000000         110
    and: 0000000         111
    """
    def R_type(self, funct3:str, funct7:str):
        ops = re.split(r'[\s,]+',self.inst_body)
        if len(ops) != 3:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return 
        rd = self.decode_reg(ops[0])
        rs1 = self.decode_reg(ops[1])
        rs2 = self.decode_reg(ops[2])
        self.binary = str2bytes(funct7 + rs2 + rs1 + funct3 + rd + '0110011') 
    """
    jal: imm[21:2] rd 1101111
    jalr:imm[13:2] rs1 000 rd 1100111
    """
    def J_jal(self):
        ops = re.split(r'[\s,]+',self.inst_body)
        if len(ops) != 2:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return         
        rd = self.decode_reg(ops[0])
        if ops[1] in self.tags:
            immd = self.tags[ops[1]] - self.mem_addr
        else:
            immd = str2int(ops[1]) & (~0b11)
        if immd > (1 << 21)-1 or immd < -(1<<21):
            logger.info(f"[error line:{self.line_num}]\timmd overflow: {self.content}")
            return       
        immd, _ = int2bin(immd,32)
        immd = immd[-21-1:-2]
        self.binary = str2bytes(immd  + rd + '1101111') 
    def J_jalr(self):
        ops = re.split(r'[\s,]+',self.inst_body)
        if len(ops) != 3:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return         
        rd = self.decode_reg(ops[0])
        rs1 = self.decode_reg(ops[1])
        if ops[2] in self.tags:
            immd = self.tags[ops[2]] - self.mem_addr
        else:
            immd = str2int(ops[2]) & (~0b11)
        if immd > (1 << 13)-1 or immd < -(1<<13):
            logger.info(f"[error line:{self.line_num}]\timmd overflow: {self.content}")
            return       
        immd, _ = int2bin(immd,32)
        immd = immd[-13-1:-2]
        self.binary = str2bytes(immd  + rs1 + '000' + rd + '1100111') 
    """
    beq: imm[13:7] rs2 rs1 000 imm[6:2] 1100011
    """
    def B_type(self, funct3:str):
        ops = re.split(r'[\s,]+',self.inst_body)
        if len(ops) != 3:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return         
        rs1 = self.decode_reg(ops[0])
        rs2 = self.decode_reg(ops[1])
        if ops[2] in self.tags:
            immd = self.tags[ops[2]] - self.mem_addr
        else:
            immd = str2int(ops[2]) & (~0b11)
        if immd > (1 << 13)-1 or immd < -(1<<13):
            logger.info(f"[error line:{self.line_num}]\timmd overflow: {self.content}")
            return       
        immd, _ = int2bin(immd,32)
        immd1 = immd[-13-1:-7]
        immd2 = immd[-6-1:-2]
        self.binary = str2bytes(immd1  + rs2 + rs1 + funct3 + immd2 + '1100011')   
    """
    lb: imm[11:0] rs1 000 rd 0000011   # mem[rs1 + immd] -> rd
    lbu:100
    lw: 010
    lwu:110
    ld: 011
    """
    def Load(self, funct3:str):
        ops = re.split(r'[\s,()]+',self.inst_body)
        if len(ops) != 4:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return   
        rd = self.decode_reg(ops[0])
        rs1 = self.decode_reg(ops[2]) 
        if ops[1] in self.tags:
            immd = self.tags[ops[1]]  
        else:
            immd = str2int(ops[1])   
        immd, _ = int2bin(immd,12)  
        self.binary = str2bytes(immd  + rs1 + funct3 + rd + '0000011')
    """
    sb: imm[11:5] rs2 rs1 000 imm[4:0] 0100011
    sw: 010
    sd: 011
    """
    def Store(self, funct3:str):
        ops = re.split(r'[\s,()]+',self.inst_body)
        if len(ops) != 4:
            logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
            return   
        rs2 = self.decode_reg(ops[0])
        rs1 = self.decode_reg(ops[2]) 
        if ops[1] in self.tags:
            immd = self.tags[ops[1]]  
        else:
            immd = str2int(ops[1])   
        immd, _ = int2bin(immd,12)  
        immd1 = immd[-11-1:-5]
        immd2 = immd[-4-1:]
        self.binary = str2bytes(immd1  + rs2 + rs1 + funct3 + immd2 + '0100011')
    
    def error_inst(self):
        logger.info(f"[error line:{self.line_num}]\tinvaild instruction: {self.content}")
        return 
    def decode_reg(self, a:str):
        try:
            return int2bin(int(a[1:]),6)[0][1:]
        except:
            logger.info('[error] wrong register name: '+a)
            return '00000'
        

        


logger = logging.getLogger()
logger.setLevel(logging.INFO)
# file
fh = logging.FileHandler(os.path.join(os.path.abspath(os.path.dirname(__file__)), "asm.log"), mode='w')
fh.setLevel(logging.INFO)
# formatter = logging.Formatter("%(asctime)s (line:%(lineno)d) %(message)s ",'%Y/%m/%d %I:%M:%S')
formatter = logging.Formatter("[line:%(lineno)d] %(message)s ")
fh.setFormatter(formatter)
logger.addHandler(fh)
# console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.info(">>>> start")


with open("test.asm", 'r', encoding='utf-8') as f:
    test = ASM(f.read())
