def main:                                // line: 3
        var i                            // line: 4
        var a                            // line: 5
        push 0                           // line: 6
        pop i                            // line: 6
_loop_0                                 
        push i                           // line: 7
        push 10                          // line: 7
        cmp_lt                          
        jz _endloop_0                   
        push i                           // line: 8
        push 1                           // line: 8
        op_add                          
        pop i                            // line: 8
_if_1                                   
        push i                           // line: 9
        push 3                           // line: 9
        cmp_eq                          
        push i                           // line: 9
        push 5                           // line: 9
        cmp_eq                          
        op_or                           
        jz _else_1                      
        jmp _loop_0                     
        jmp _endif_1                    
_else_1                                 
_endif_1                                
_if_2                                   
        push i                           // line: 12
        push 8                           // line: 12
        cmp_eq                          
        jz _else_2                      
        jmp _endloop_0                  
        jmp _endif_2                    
_else_2                                 
_endif_2                                
        push 0                          
        push i                           // line: 15
        @factor                          // line: 15
        pop a                            // line: 15
        print a                          // line: 16
        jmp _loop_0                     
_endloop_0                              
        push 0                           // line: 18
        ret
                            
def factor:                              // line: 21
        arg n                            // line: 21
_if_3                                   
        push n                           // line: 22
        push 2                           // line: 22
        cmp_lt                          
        jz _else_3                      
        push 1                           // line: 23
        ret
                            
        jmp _endif_3                    
_else_3                                 
_endif_3                                
        push n                           // line: 25
        push 0                          
        push n                           // line: 25
        push 1                           // line: 25
        op_sub                          
        @factor                          // line: 25
        op_mul                          
        ret
                            
