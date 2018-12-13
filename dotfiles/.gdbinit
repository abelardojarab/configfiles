# INSTALL INSTRUCTIONS: save as ~/.gdbinit

# __________________gdb options_________________

# C++ related beautifiers (optional)
set print pretty on
set print object on
set print static-members on
set print vtbl on
set print demangle on
set demangle-style gnu-v3
set print sevenbit-strings off

# set to 1 to enable 64bits target by default (32bit is the default)
set $64BITS = 1

set confirm off
set verbose off
set prompt \033[31mgdb$ \033[0m

set output-radix 0x10
set input-radix 0x10

# These make gdb never pause in its output
set height 0
set width 0

# Display instructions in Intel format
set disassembly-flavor intel

set $SHOW_CONTEXT = 1
set $SHOW_NEST_INSN = 0

set $CONTEXTSIZE_STACK = 6
set $CONTEXTSIZE_DATA  = 8
set $CONTEXTSIZE_CODE  = 8

# set to 0 to remove display of objectivec messages (default is 1)
set $SHOWOBJECTIVEC = 1
# set to 0 to remove display of cpu registers (default is 1)
set $SHOWCPUREGISTERS = 1
# set to 1 to enable display of stack (default is 0)
set $SHOWSTACK = 0
# set to 1 to enable display of data window (default is 0)
set $SHOWDATAWIN = 0

# ______________window size control___________
define contextsize-stack
    if $argc != 1
        help contextsize-stack
    else
        set $CONTEXTSIZE_STACK = $arg0
    end
end
document contextsize-stack
Set stack dump window size to NUM lines.
Usage: contextsize-stack NUM
end


define contextsize-data
    if $argc != 1
        help contextsize-data
    else
        set $CONTEXTSIZE_DATA = $arg0
    end
end
document contextsize-data
Set data dump window size to NUM lines.
Usage: contextsize-data NUM
end


define contextsize-code
    if $argc != 1
        help contextsize-code
    else
        set $CONTEXTSIZE_CODE = $arg0
    end
end
document contextsize-code
Set code window size to NUM lines.
Usage: contextsize-code NUM
end

# _____________breakpoint aliases_____________
define bpl
    info breakpoints
end
document bpl
List all breakpoints.
end

define bp
    if $argc != 1
        help bp
    else
        break $arg0
    end
end
document bp
Set breakpoint.
Usage: bp LOCATION
LOCATION may be a line number, function name, or "*" and an address.

To break on a symbol you must enclose symbol name inside "".
Example:
bp "[NSControl stringValue]"
Or else you can use directly the break command (break [NSControl stringValue])
end


define bpc
    if $argc != 1
        help bpc
    else
        clear $arg0
    end
end
document bpc
Clear breakpoint.
Usage: bpc LOCATION
LOCATION may be a line number, function name, or "*" and an address.
end


define bpe
    if $argc != 1
        help bpe
    else
        enable $arg0
    end
end
document bpe
Enable breakpoint with number NUM.
Usage: bpe NUM
end


define bpd
    if $argc != 1
        help bpd
    else
        disable $arg0
    end
end
document bpd
Disable breakpoint with number NUM.
Usage: bpd NUM
end


define bpt
    if $argc != 1
        help bpt
    else
        tbreak $arg0
    end
end
document bpt
Set a temporary breakpoint.
Will be deleted when hit!
Usage: bpt LOCATION
LOCATION may be a line number, function name, or "*" and an address.
end


define bpm
    if $argc != 1
        help bpm
    else
        awatch $arg0
    end
end
document bpm
Set a read/write breakpoint on EXPRESSION, e.g. *address.
Usage: bpm EXPRESSION
end


define bhb
    if $argc != 1
        help bhb
    else
        hb $arg0
    end
end
document bhb
Set hardware assisted breakpoint.
Usage: bhb LOCATION
LOCATION may be a line number, function name, or "*" and an address.
end




# ______________process information____________
define argv
    show args
end
document argv
Print program arguments.
end


define stack
    if $argc == 0
        info stack
    end
    if $argc == 1
        info stack $arg0
    end
    if $argc > 1
        help stack
    end
end
document stack
Print backtrace of the call stack, or innermost COUNT frames.
Usage: stack <COUNT>
end


define frame
    info frame
    info args
    info locals
end
document frame
Print stack frame.
end


define flags
# OF (overflow) flag
    if (($eflags >> 0xB) & 1)
        printf "O "
        set $_of_flag = 1
    else
        printf "o "
        set $_of_flag = 0
    end
    if (($eflags >> 0xA) & 1)
        printf "D "
    else
        printf "d "
    end
    if (($eflags >> 9) & 1)
        printf "I "
    else
        printf "i "
    end
    if (($eflags >> 8) & 1)
        printf "T "
    else
        printf "t "
    end
# SF (sign) flag
    if (($eflags >> 7) & 1)
        printf "S "
        set $_sf_flag = 1
    else
        printf "s "
        set $_sf_flag = 0
    end
# ZF (zero) flag
    if (($eflags >> 6) & 1)
        printf "Z "
    set $_zf_flag = 1
    else
        printf "z "
    set $_zf_flag = 0
    end
    if (($eflags >> 4) & 1)
        printf "A "
    else
        printf "a "
    end
# PF (parity) flag
    if (($eflags >> 2) & 1)
        printf "P "
    set $_pf_flag = 1
    else
        printf "p "
    set $_pf_flag = 0
    end
# CF (carry) flag
    if ($eflags & 1)
        printf "C "
    set $_cf_flag = 1
    else
        printf "c "
    set $_cf_flag = 0
    end
    printf "\n"
end
document flags
Print flags register.
end


define eflags
    printf "     OF <%d>  DF <%d>  IF <%d>  TF <%d>",\
           (($eflags >> 0xB) & 1), (($eflags >> 0xA) & 1), \
           (($eflags >> 9) & 1), (($eflags >> 8) & 1)
    printf "  SF <%d>  ZF <%d>  AF <%d>  PF <%d>  CF <%d>\n",\
           (($eflags >> 7) & 1), (($eflags >> 6) & 1),\
           (($eflags >> 4) & 1), (($eflags >> 2) & 1), ($eflags & 1)
    printf "     ID <%d>  VIP <%d> VIF <%d> AC <%d>",\
           (($eflags >> 0x15) & 1), (($eflags >> 0x14) & 1), \
           (($eflags >> 0x13) & 1), (($eflags >> 0x12) & 1)
    printf "  VM <%d>  RF <%d>  NT <%d>  IOPL <%d>\n",\
           (($eflags >> 0x11) & 1), (($eflags >> 0x10) & 1),\
           (($eflags >> 0xE) & 1), (($eflags >> 0xC) & 3)
end
document eflags
Print eflags register.
end


define reg
 if ($64BITS == 1)
# 64bits stuff
    printf "  "
    echo \033[32m
    printf "RAX:"
    echo \033[0m
    printf " 0x%016lX  ", $rax
    echo \033[32m
    printf "RBX:"
    echo \033[0m
    printf " 0x%016lX  ", $rbx
    echo \033[32m
    printf "RCX:"
    echo \033[0m
    printf " 0x%016lX  ", $rcx
    echo \033[32m
    printf "RDX:"
    echo \033[0m
    printf " 0x%016lX  ", $rdx
    echo \033[1m\033[4m\033[31m
    flags
    echo \033[0m
    printf "  "
    echo \033[32m
    printf "RSI:"
    echo \033[0m
    printf " 0x%016lX  ", $rsi
    echo \033[32m
    printf "RDI:"
    echo \033[0m
    printf " 0x%016lX  ", $rdi
    echo \033[32m
    printf "RBP:"
    echo \033[0m
    printf " 0x%016lX  ", $rbp
    echo \033[32m
    printf "RSP:"
    echo \033[0m
    printf " 0x%016lX  ", $rsp
    echo \033[32m
    printf "RIP:"
    echo \033[0m
    printf " 0x%016lX\n  ", $rip
    echo \033[32m
    printf "R8 :"
    echo \033[0m
    printf " 0x%016lX  ", $r8
    echo \033[32m
    printf "R9 :"
    echo \033[0m
    printf " 0x%016lX  ", $r9
    echo \033[32m
    printf "R10:"
    echo \033[0m
    printf " 0x%016lX  ", $r10
    echo \033[32m
    printf "R11:"
    echo \033[0m
    printf " 0x%016lX  ", $r11
    echo \033[32m
    printf "R12:"
    echo \033[0m
    printf " 0x%016lX\n  ", $r12
    echo \033[32m
    printf "R13:"
    echo \033[0m
    printf " 0x%016lX  ", $r13
    echo \033[32m
    printf "R14:"
    echo \033[0m
    printf " 0x%016lX  ", $r14
    echo \033[32m
    printf "R15:"
    echo \033[0m
    printf " 0x%016lX\n  ", $r15
    echo \033[32m
    printf "CS:"
    echo \033[0m
    printf " %04X  ", $cs
    echo \033[32m
    printf "DS:"
    echo \033[0m
    printf " %04X  ", $ds
    echo \033[32m
    printf "ES:"
    echo \033[0m
    printf " %04X  ", $es
    echo \033[32m
    printf "FS:"
    echo \033[0m
    printf " %04X  ", $fs
    echo \033[32m
    printf "GS:"
    echo \033[0m
    printf " %04X  ", $gs
    echo \033[32m
    printf "SS:"
    echo \033[0m
    printf " %04X", $ss
    echo \033[0m
# 32bits stuff
 else
    printf "  "
    echo \033[32m
    printf "EAX:"
    echo \033[0m
    printf " 0x%08X  ", $eax
    echo \033[32m
    printf "EBX:"
    echo \033[0m
    printf " 0x%08X  ", $ebx
    echo \033[32m
    printf "ECX:"
    echo \033[0m
    printf " 0x%08X  ", $ecx
    echo \033[32m
    printf "EDX:"
    echo \033[0m
    printf " 0x%08X  ", $edx
    echo \033[1m\033[4m\033[31m
    flags
    echo \033[0m
    printf "  "
    echo \033[32m
    printf "ESI:"
    echo \033[0m
    printf " 0x%08X  ", $esi
    echo \033[32m
    printf "EDI:"
    echo \033[0m
    printf " 0x%08X  ", $edi
    echo \033[32m
    printf "EBP:"
    echo \033[0m
    printf " 0x%08X  ", $ebp
    echo \033[32m
    printf "ESP:"
    echo \033[0m
    printf " 0x%08X  ", $esp
    echo \033[32m
    printf "EIP:"
    echo \033[0m
    printf " 0x%08X\n  ", $eip
    echo \033[32m
    printf "CS:"
    echo \033[0m
    printf " %04X  ", $cs
    echo \033[32m
    printf "DS:"
    echo \033[0m
    printf " %04X  ", $ds
    echo \033[32m
    printf "ES:"
    echo \033[0m
    printf " %04X  ", $es
    echo \033[32m
    printf "FS:"
    echo \033[0m
    printf " %04X  ", $fs
    echo \033[32m
    printf "GS:"
    echo \033[0m
    printf " %04X  ", $gs
    echo \033[32m
    printf "SS:"
    echo \033[0m
    printf " %04X", $ss
    echo \033[0m
 end
# call smallregisters
    smallregisters
# display conditional jump routine
    if ($64BITS == 1)
     printf "\t\t\t\t"
    end
    # dumpjump
    printf "\n"
end
document reg
Print CPU registers.
end

define smallregisters
 if ($64BITS == 1)
#64bits stuff
    # from rax
    set $eax = $rax & 0xffffffff
    set $ax = $rax & 0xffff
    set $al = $ax & 0xff
    set $ah = $ax >> 8
    # from rbx
    set $bx = $rbx & 0xffff
    set $bl = $bx & 0xff
    set $bh = $bx >> 8
    # from rcx
    set $ecx = $rcx & 0xffffffff
    set $cx = $rcx & 0xffff
    set $cl = $cx & 0xff
    set $ch = $cx >> 8
    # from rdx
    set $edx = $rdx & 0xffffffff
    set $dx = $rdx & 0xffff
    set $dl = $dx & 0xff
    set $dh = $dx >> 8
    # from rsi
    set $esi = $rsi & 0xffffffff
    set $si = $rsi & 0xffff
    # from rdi
    set $edi = $rdi & 0xffffffff
    set $di = $rdi & 0xffff
#32 bits stuff
 else
    # from eax
    set $ax = $eax & 0xffff
    set $al = $ax & 0xff
    set $ah = $ax >> 8
    # from ebx
    set $bx = $ebx & 0xffff
    set $bl = $bx & 0xff
    set $bh = $bx >> 8
    # from ecx
    set $cx = $ecx & 0xffff
    set $cl = $cx & 0xff
    set $ch = $cx >> 8
    # from edx
    set $dx = $edx & 0xffff
    set $dl = $dx & 0xff
    set $dh = $dx >> 8
    # from esi
    set $si = $esi & 0xffff
    # from edi
    set $di = $edi & 0xffff
 end

end
document smallregisters
Create the 16 and 8 bit cpu registers (gdb doesn't have them by default)
And 32bits if we are dealing with 64bits binaries
end

define func
    if $argc == 0
        info functions
    end
    if $argc == 1
        info functions $arg0
    end
    if $argc > 1
        help func
    end
end
document func
Print all function names in target, or those matching REGEXP.
Usage: func <REGEXP>
end


define var
    if $argc == 0
        info variables
    end
    if $argc == 1
        info variables $arg0
    end
    if $argc > 1
        help var
    end
end
document var
Print all global and static variable names (symbols), or those matching REGEXP.
Usage: var <REGEXP>
end


define lib
    info sharedlibrary
end
document lib
Print shared libraries linked to target.
end


define sig
    if $argc == 0
        info signals
    end
    if $argc == 1
        info signals $arg0
    end
    if $argc > 1
        help sig
    end
end
document sig
Print what debugger does when program gets various signals.
Specify a SIGNAL as argument to print info on that signal only.
Usage: sig <SIGNAL>
end


define threads
    info threads
end
document threads
Print threads in target.
end


define dis
    if $argc == 0
        disassemble
    end
    if $argc == 1
        disassemble $arg0
    end
    if $argc == 2
        disassemble $arg0 $arg1
    end
    if $argc > 2
        help dis
    end
end
document dis
Disassemble a specified section of memory.
Default is to disassemble the function surrounding the PC (program counter)
of selected frame. With one argument, ADDR1, the function surrounding this
address is dumped. Two arguments are taken as a range of memory to dump.
Usage: dis <ADDR1> <ADDR2>
end




# __________hex/ascii dump an address_________
define ascii_char
    if $argc != 1
        help ascii_char
    else
        # thanks elaine :)
        set $_c = *(unsigned char *)($arg0)
        if ($_c < 0x20 || $_c > 0x7E)
            printf "."
        else
            printf "%c", $_c
        end
    end
end
document ascii_char
Print ASCII value of byte at address ADDR.
Print "." if the value is unprintable.
Usage: ascii_char ADDR
end


define hex_quad
    if $argc != 1
        help hex_quad
    else
        printf "%02X %02X %02X %02X %02X %02X %02X %02X", \
               *(unsigned char*)($arg0), *(unsigned char*)($arg0 + 1),     \
               *(unsigned char*)($arg0 + 2), *(unsigned char*)($arg0 + 3), \
               *(unsigned char*)($arg0 + 4), *(unsigned char*)($arg0 + 5), \
               *(unsigned char*)($arg0 + 6), *(unsigned char*)($arg0 + 7)
    end
end
document hex_quad
Print eight hexadecimal bytes starting at address ADDR.
Usage: hex_quad ADDR
end

define hexdump
    if $argc != 1
        help hexdump
    else
        echo \033[1m
        if ($64BITS == 1)
         printf "0x%016lX : ", $arg0
        else
         printf "0x%08X : ", $arg0
        end
        echo \033[0m
        hex_quad $arg0
        echo \033[1m
        printf " - "
        echo \033[0m
        hex_quad $arg0+8
        printf " "
        echo \033[1m
        ascii_char $arg0+0x0
        ascii_char $arg0+0x1
        ascii_char $arg0+0x2
        ascii_char $arg0+0x3
        ascii_char $arg0+0x4
        ascii_char $arg0+0x5
        ascii_char $arg0+0x6
        ascii_char $arg0+0x7
        ascii_char $arg0+0x8
        ascii_char $arg0+0x9
        ascii_char $arg0+0xA
        ascii_char $arg0+0xB
        ascii_char $arg0+0xC
        ascii_char $arg0+0xD
        ascii_char $arg0+0xE
        ascii_char $arg0+0xF
        echo \033[0m
        printf "\n"
    end
end
document hexdump
Display a 16-byte hex/ASCII dump of memory at address ADDR.
Usage: hexdump ADDR
end


# _______________data window__________________
define ddump
    if $argc != 1
        help ddump
    else
        echo \033[34m
        if ($64BITS == 1)
         printf "[0x%04X:0x%016lX]", $ds, $data_addr
        else
         printf "[0x%04X:0x%08X]", $ds, $data_addr
        end
    echo \033[34m
    printf "------------------------"
    printf "-------------------------------"
    if ($64BITS == 1)
     printf "-------------------------------------"
    end

    echo \033[1;34m
    printf "[data]\n"
        echo \033[0m
        set $_count = 0
        while ($_count < $arg0)
            set $_i = ($_count * 0x10)
            hexdump $data_addr+$_i
            set $_count++
        end
    end
end
document ddump
Display NUM lines of hexdump for address in $data_addr global variable.
Usage: ddump NUM
end


define dd
    if $argc != 1
        help dd
    else
        if ((($arg0 >> 0x18) == 0x40) || (($arg0 >> 0x18) == 0x08) || (($arg0 >> 0x18) == 0xBF))
            set $data_addr = $arg0
            ddump 0x10
        else
            printf "Invalid address: %08X\n", $arg0
        end
    end
end
document dd
Display 16 lines of a hex dump of address starting at ADDR.
Usage: dd ADDR
end


define datawin
 if ($64BITS == 1)
    if ((($rsi >> 0x18) == 0x40) || (($rsi >> 0x18) == 0x08) || (($rsi >> 0x18) == 0xBF))
        set $data_addr = $rsi
    else
        if ((($rdi >> 0x18) == 0x40) || (($rdi >> 0x18) == 0x08) || (($rdi >> 0x18) == 0xBF))
            set $data_addr = $rdi
        else
            if ((($rax >> 0x18) == 0x40) || (($rax >> 0x18) == 0x08) || (($rax >> 0x18) == 0xBF))
                set $data_addr = $rax
            else
                set $data_addr = $rsp
            end
        end
    end

 else
    if ((($esi >> 0x18) == 0x40) || (($esi >> 0x18) == 0x08) || (($esi >> 0x18) == 0xBF))
        set $data_addr = $esi
    else
        if ((($edi >> 0x18) == 0x40) || (($edi >> 0x18) == 0x08) || (($edi >> 0x18) == 0xBF))
            set $data_addr = $edi
        else
            if ((($eax >> 0x18) == 0x40) || (($eax >> 0x18) == 0x08) || (($eax >> 0x18) == 0xBF))
                set $data_addr = $eax
            else
                set $data_addr = $esp
            end
        end
    end
 end
    ddump $CONTEXTSIZE_DATA
end
document datawin
Display valid address from one register in data window.
Registers to choose are: esi, edi, eax, or esp.
end

# _______________process context______________
# initialize variable
set $displayobjectivec = 0

define context
    echo \033[34m
    if $SHOWCPUREGISTERS == 1
        printf "----------------------------------------"
        printf "----------------------------------"
        if ($64BITS == 1)
         printf "---------------------------------------------"
        end
        echo \033[34m\033[1m
        printf "[regs]\n"
        echo \033[0m
        reg
        echo \033[36m
    end
    if $SHOWSTACK == 1
    echo \033[34m
        if ($64BITS == 1)
         printf "[0x%04X:0x%016lX]", $ss, $rsp
        else
         printf "[0x%04X:0x%08X]", $ss, $esp
        end
        echo \033[34m
        printf "-------------------------"
        printf "-----------------------------"
        if ($64BITS == 1)
         printf "-------------------------------------"
        end
    echo \033[34m\033[1m
    printf "[stack]\n"
        echo \033[0m
        set $context_i = $CONTEXTSIZE_STACK
        while ($context_i > 0)
         set $context_t = $sp + 0x10 * ($context_i - 1)
         hexdump $context_t
         set $context_i--
        end
    end
# show the objective C message being passed to msgSend
   if $SHOWOBJECTIVEC == 1
#FIXME64
# What a piece of crap that's going on here :)
# detect if it's the correct opcode we are searching for
        set $__byte1 = *(unsigned char *)$pc
        set $__byte = *(int *)$pc
#
        if ($__byte == 0x4244489)
            set $objectivec = $eax
            set $displayobjectivec = 1
        end
#
        if ($__byte == 0x4245489)
            set $objectivec = $edx
            set $displayobjectivec = 1
        end
#
        if ($__byte == 0x4244c89)
            set $objectivec = $edx
            set $displayobjectivec = 1
        end
# and now display it or not (we have no interest in having the info displayed after the call)
        if $__byte1 == 0xE8
            if $displayobjectivec == 1
                echo \033[34m
                printf "--------------------------------------------------------------------"
                if ($64BITS == 1)
                 printf "---------------------------------------------"
                end
            echo \033[34m\033[1m
            printf "[ObjectiveC]\n"
                echo \033[0m\033[30m
                x/s $objectivec
            end
            set $displayobjectivec = 0
        end
        if $displayobjectivec == 1
            echo \033[34m
            printf "--------------------------------------------------------------------"
            if ($64BITS == 1)
             printf "---------------------------------------------"
            end
        echo \033[34m\033[1m
        printf "[ObjectiveC]\n"
            echo \033[0m\033[30m
            x/s $objectivec
        end
   end
    echo \033[0m
# and this is the end of this little crap

    if $SHOWDATAWIN == 1
     datawin
    end

    echo \033[34m
    printf "--------------------------------------------------------------------------"
    if ($64BITS == 1)
     printf "---------------------------------------------"
    end
    echo \033[34m\033[1m
    printf "[code]\n"
    echo \033[0m
    set $context_i = $CONTEXTSIZE_CODE
    if($context_i > 0)
        x /i $pc
        set $context_i--
    end
    while ($context_i > 0)
        x /i
        set $context_i--
    end
    echo \033[34m
    printf "----------------------------------------"
    printf "----------------------------------------"
    if ($64BITS == 1)
     printf "---------------------------------------------\n"
    else
     printf "\n"
    end

    echo \033[0m
end
document context
Print context window, i.e. regs, stack, ds:esi and disassemble cs:eip.
end


define context-on
    set $SHOW_CONTEXT = 1
    printf "Displaying of context is now ON\n"
end
document context-on
Enable display of context on every program break.
end


define context-off
    set $SHOW_CONTEXT = 0
    printf "Displaying of context is now OFF\n"
end
document context-off
Disable display of context on every program break.
end


# _______________process control______________
define n
    if $argc == 0
        nexti
    end
    if $argc == 1
        nexti $arg0
    end
    if $argc > 1
        help n
    end
end
document n
Step one instruction, but proceed through subroutine calls.
If NUM is given, then repeat it NUM times or till program stops.
This is alias for nexti.
Usage: n <NUM>
end


define go
    if $argc == 0
        stepi
    end
    if $argc == 1
        stepi $arg0
    end
    if $argc > 1
        help go
    end
end
document go
Step one instruction exactly.
If NUM is given, then repeat it NUM times or till program stops.
This is alias for stepi.
Usage: go <NUM>
end


define pret
    finish
end
document pret
Execute until selected stack frame returns (step out of current call).
Upon return, the value returned is printed and put in the value history.
end


define init
    set $SHOW_NEST_INSN = 0
    tbreak _init
    r
end
document init
Run program and break on _init().
end


define start
    set $SHOW_NEST_INSN = 0
    tbreak _start
    r
end
document start
Run program and break on _start().
end


define sstart
    set $SHOW_NEST_INSN = 0
    tbreak __libc_start_main
    r
end
document sstart
Run program and break on __libc_start_main().
Useful for stripped executables.
end


define main
    set $SHOW_NEST_INSN = 0
    tbreak main
    r
end
document main
Run program and break on main().
end

define null
    if ( $argc >2 || $argc == 0)
        help null
    end

    if ($argc == 1)
    set *(unsigned char *)$arg0 = 0
    else
    set $addr = $arg0
    while ($addr < $arg1)
            set *(unsigned char *)$addr = 0
        set $addr = $addr +1
    end
    end
end
document null
Usage: null ADDR1 [ADDR2]
Patch a single byte at address ADDR1 to NULL (0x00), or a series of bytes between ADDR1 and ADDR2.

end


define int3
    if $argc != 1
        help int3
    else
        set *(unsigned char *)$arg0 = 0xCC
    end
end
document int3
Patch byte at address ADDR to an INT3 (0xCC) instruction.
Usage: int3 ADDR
end

# ____________________cflow___________________
define print_insn_type
    if $argc != 1
        help print_insn_type
    else
        if ($arg0 < 0 || $arg0 > 5)
            printf "UNDEFINED/WRONG VALUE"
        end
        if ($arg0 == 0)
            printf "UNKNOWN"
        end
        if ($arg0 == 1)
            printf "JMP"
        end
        if ($arg0 == 2)
            printf "JCC"
        end
        if ($arg0 == 3)
            printf "CALL"
        end
        if ($arg0 == 4)
            printf "RET"
        end
        if ($arg0 == 5)
            printf "INT"
        end
    end
end
document print_insn_type
Print human-readable mnemonic for the instruction type (usually $INSN_TYPE).
Usage: print_insn_type INSN_TYPE_NUMBER
end


define get_insn_type
    if $argc != 1
        help get_insn_type
    else
        set $INSN_TYPE = 0
        set $_byte1 = *(unsigned char *)$arg0
        if ($_byte1 == 0x9A || $_byte1 == 0xE8)
            # "call"
            set $INSN_TYPE = 3
        end
        if ($_byte1 >= 0xE9 && $_byte1 <= 0xEB)
            # "jmp"
            set $INSN_TYPE = 1
        end
        if ($_byte1 >= 0x70 && $_byte1 <= 0x7F)
            # "jcc"
            set $INSN_TYPE = 2
        end
        if ($_byte1 >= 0xE0 && $_byte1 <= 0xE3 )
            # "jcc"
            set $INSN_TYPE = 2
        end
        if ($_byte1 == 0xC2 || $_byte1 == 0xC3 || $_byte1 == 0xCA || \
            $_byte1 == 0xCB || $_byte1 == 0xCF)
            # "ret"
            set $INSN_TYPE = 4
        end
        if ($_byte1 >= 0xCC && $_byte1 <= 0xCE)
            # "int"
            set $INSN_TYPE = 5
        end
        if ($_byte1 == 0x0F )
            # two-byte opcode
            set $_byte2 = *(unsigned char *)($arg0 + 1)
            if ($_byte2 >= 0x80 && $_byte2 <= 0x8F)
                # "jcc"
                set $INSN_TYPE = 2
            end
        end
        if ($_byte1 == 0xFF)
            # opcode extension
            set $_byte2 = *(unsigned char *)($arg0 + 1)
            set $_opext = ($_byte2 & 0x38)
            if ($_opext == 0x10 || $_opext == 0x18)
                # "call"
                set $INSN_TYPE = 3
            end
            if ($_opext == 0x20 || $_opext == 0x28)
                # "jmp"
                set $INSN_TYPE = 1
            end
        end
    end
end
document get_insn_type
Recognize instruction type at address ADDR.
Take address ADDR and set the global $INSN_TYPE variable to
0, 1, 2, 3, 4, 5 if the instruction at that address is
unknown, a jump, a conditional jump, a call, a return, or an interrupt.
Usage: get_insn_type ADDR
end


define step_to_call
    set $_saved_ctx = $SHOW_CONTEXT
    set $SHOW_CONTEXT = 0
    set $SHOW_NEST_INSN = 0

    set logging file /dev/null
    set logging redirect on
    set logging on

    set $_cont = 1
    while ($_cont > 0)
        stepi
        get_insn_type $pc
        if ($INSN_TYPE == 3)
            set $_cont = 0
        end
    end

    set logging off

    if ($_saved_ctx > 0)
        context
    end

    set $SHOW_CONTEXT = $_saved_ctx
    set $SHOW_NEST_INSN = 0

    set logging file ~/gdb.txt
    set logging redirect off
    set logging on

    printf "step_to_call command stopped at:\n  "
    x/i $pc
    printf "\n"
    set logging off

end
document step_to_call
Single step until a call instruction is found.
Stop before the call is taken.
Log is written into the file ~/gdb.txt.
end


define trace_calls

    printf "Tracing...please wait...\n"

    set $_saved_ctx = $SHOW_CONTEXT
    set $SHOW_CONTEXT = 0
    set $SHOW_NEST_INSN = 0
    set $_nest = 1
    set listsize 0

    set logging overwrite on
    set logging file ~/gdb_trace_calls.txt
    set logging on
    set logging off
    set logging overwrite off

    while ($_nest > 0)
        get_insn_type $pc
        # handle nesting
        if ($INSN_TYPE == 3)
            set $_nest = $_nest + 1
        else
            if ($INSN_TYPE == 4)
                set $_nest = $_nest - 1
            end
        end
        # if a call, print it
        if ($INSN_TYPE == 3)
            set logging file ~/gdb_trace_calls.txt
            set logging redirect off
            set logging on

            set $x = $_nest - 2
            while ($x > 0)
                printf "\t"
                set $x = $x - 1
            end
            x/i $pc
        end

        set logging off
        set logging file /dev/null
        set logging redirect on
        set logging on
        stepi
        set logging redirect off
        set logging off
    end

    set $SHOW_CONTEXT = $_saved_ctx
    set $SHOW_NEST_INSN = 0

    printf "Done, check ~/gdb_trace_calls.txt\n"
end
document trace_calls
Create a runtime trace of the calls made by target.
Log overwrites(!) the file ~/gdb_trace_calls.txt.
end


define trace_run

    printf "Tracing...please wait...\n"

    set $_saved_ctx = $SHOW_CONTEXT
    set $SHOW_CONTEXT = 0
    set $SHOW_NEST_INSN = 1
    set logging overwrite on
    set logging file ~/gdb_trace_run.txt
    set logging redirect on
    set logging on
    set $_nest = 1

    while ( $_nest > 0 )

        get_insn_type $pc
        # jmp, jcc, or cll
        if ($INSN_TYPE == 3)
            set $_nest = $_nest + 1
        else
            # ret
            if ($INSN_TYPE == 4)
                set $_nest = $_nest - 1
            end
        end
        stepi
    end

    printf "\n"

    set $SHOW_CONTEXT = $_saved_ctx
    set $SHOW_NEST_INSN = 0
    set logging redirect off
    set logging off

    # clean up trace file
    shell  grep -v ' at ' ~/gdb_trace_run.txt > ~/gdb_trace_run.1
    shell  grep -v ' in ' ~/gdb_trace_run.1 > ~/gdb_trace_run.txt
    shell  rm -f ~/gdb_trace_run.1
    printf "Done, check ~/gdb_trace_run.txt\n"
end
document trace_run
Create a runtime trace of target.
Log overwrites(!) the file ~/gdb_trace_run.txt.
end

# bunch of semi-useless commands
#
#   STL GDB evaluators/views/utilities - 1.03
#
#   The following STL containers are currently supported:
#
#       std::vector<T> -- via pvector command
#       std::list<T> -- via plist or plist_member command
#       std::map<T,T> -- via pmap or pmap_member command
#       std::multimap<T,T> -- via pmap or pmap_member command
#       std::set<T> -- via pset command
#       std::multiset<T> -- via pset command
#       std::deque<T> -- via pdequeue command
#       std::stack<T> -- via pstack command
#       std::queue<T> -- via pqueue command
#       std::priority_queue<T> -- via ppqueue command
#       std::bitset<n> -- via pbitset command
#       std::string -- via pstring command
#       std::widestring -- via pwstring command
#
#   The end of this file contains (optional) C++ beautifiers
#   Make sure your debugger supports $argc
#

#
# std::vector<>
#

define pvector
	if $argc == 0
		help pvector
	else
		set $size = $arg0._M_impl._M_finish - $arg0._M_impl._M_start
		set $capacity = $arg0._M_impl._M_end_of_storage - $arg0._M_impl._M_start
		set $size_max = $size - 1
	end
	if $argc == 1
		set $i = 0
		while $i < $size
			printf "elem[%u]: ", $i
			p *($arg0._M_impl._M_start + $i)
			set $i++
		end
	end
	if $argc == 2
		set $idx = $arg1
		if $idx < 0 || $idx > $size_max
			printf "idx1, idx2 are not in acceptable range: [0..%u].\n", $size_max
		else
			printf "elem[%u]: ", $idx
			p *($arg0._M_impl._M_start + $idx)
		end
	end
	if $argc == 3
	  set $start_idx = $arg1
	  set $stop_idx = $arg2
	  if $start_idx > $stop_idx
	    set $tmp_idx = $start_idx
	    set $start_idx = $stop_idx
	    set $stop_idx = $tmp_idx
	  end
	  if $start_idx < 0 || $stop_idx < 0 || $start_idx > $size_max || $stop_idx > $size_max
	    printf "idx1, idx2 are not in acceptable range: [0..%u].\n", $size_max
	  else
	    set $i = $start_idx
		while $i <= $stop_idx
			printf "elem[%u]: ", $i
			p *($arg0._M_impl._M_start + $i)
			set $i++
		end
	  end
	end
	if $argc > 0
		printf "Vector size = %u\n", $size
		printf "Vector capacity = %u\n", $capacity
		printf "Element "
		whatis $arg0._M_impl._M_start
	end
end

document pvector
	Prints std::vector<T> information.
	Syntax: pvector <vector> <idx1> <idx2>
	Note: idx, idx1 and idx2 must be in acceptable range [0..<vector>.size()-1].
	Examples:
	pvector v - Prints vector content, size, capacity and T typedef
	pvector v 0 - Prints element[idx] from vector
	pvector v 1 2 - Prints elements in range [idx1..idx2] from vector
end

#
# std::list<>
#

define plist
	if $argc == 0
		help plist
	else
		set $head = &$arg0._M_impl._M_node
		set $current = $arg0._M_impl._M_node._M_next
		set $size = 0
		while $current != $head
			if $argc == 2
				printf "elem[%u]: ", $size
				p *($arg1*)($current + 1)
			end
			if $argc == 3
				if $size == $arg2
					printf "elem[%u]: ", $size
					p *($arg1*)($current + 1)
				end
			end
			set $current = $current._M_next
			set $size++
		end
		printf "List size = %u \n", $size
		if $argc == 1
			printf "List "
			whatis $arg0
			printf "Use plist <variable_name> <element_type> to see the elements in the list.\n"
		end
	end
end

document plist
	Prints std::list<T> information.
	Syntax: plist <list> <T> <idx>: Prints list size, if T defined all elements or just element at idx
	Examples:
	plist l - prints list size and definition
	plist l int - prints all elements and list size
	plist l int 2 - prints the third element in the list (if exists) and list size
end

define plist_member
	if $argc == 0
		help plist_member
	else
		set $head = &$arg0._M_impl._M_node
		set $current = $arg0._M_impl._M_node._M_next
		set $size = 0
		while $current != $head
			if $argc == 3
				printf "elem[%u]: ", $size
				p (*($arg1*)($current + 1)).$arg2
			end
			if $argc == 4
				if $size == $arg3
					printf "elem[%u]: ", $size
					p (*($arg1*)($current + 1)).$arg2
				end
			end
			set $current = $current._M_next
			set $size++
		end
		printf "List size = %u \n", $size
		if $argc == 1
			printf "List "
			whatis $arg0
			printf "Use plist_member <variable_name> <element_type> <member> to see the elements in the list.\n"
		end
	end
end

document plist_member
	Prints std::list<T> information.
	Syntax: plist <list> <T> <idx>: Prints list size, if T defined all elements or just element at idx
	Examples:
	plist_member l int member - prints all elements and list size
	plist_member l int member 2 - prints the third element in the list (if exists) and list size
end


#
# std::map and std::multimap
#

define pmap
	if $argc == 0
		help pmap
	else
		set $tree = $arg0
		set $i = 0
		set $node = $tree._M_t._M_impl._M_header._M_left
		set $end = $tree._M_t._M_impl._M_header
		set $tree_size = $tree._M_t._M_impl._M_node_count
		if $argc == 1
			printf "Map "
			whatis $tree
			printf "Use pmap <variable_name> <left_element_type> <right_element_type> to see the elements in the map.\n"
		end
		if $argc == 3
			while $i < $tree_size
				set $value = (void *)($node + 1)
				printf "elem[%u].left: ", $i
				p *($arg1*)$value
				set $value = $value + sizeof($arg1)
				printf "elem[%u].right: ", $i
				p *($arg2*)$value
				if $node._M_right != 0
					set $node = $node._M_right
					while $node._M_left != 0
						set $node = $node._M_left
					end
				else
					set $tmp_node = $node._M_parent
					while $node == $tmp_node._M_right
						set $node = $tmp_node
						set $tmp_node = $tmp_node._M_parent
					end
					if $node._M_right != $tmp_node
						set $node = $tmp_node
					end
				end
				set $i++
			end
		end
		if $argc == 4
			set $idx = $arg3
			set $ElementsFound = 0
			while $i < $tree_size
				set $value = (void *)($node + 1)
				if *($arg1*)$value == $idx
					printf "elem[%u].left: ", $i
					p *($arg1*)$value
					set $value = $value + sizeof($arg1)
					printf "elem[%u].right: ", $i
					p *($arg2*)$value
					set $ElementsFound++
				end
				if $node._M_right != 0
					set $node = $node._M_right
					while $node._M_left != 0
						set $node = $node._M_left
					end
				else
					set $tmp_node = $node._M_parent
					while $node == $tmp_node._M_right
						set $node = $tmp_node
						set $tmp_node = $tmp_node._M_parent
					end
					if $node._M_right != $tmp_node
						set $node = $tmp_node
					end
				end
				set $i++
			end
			printf "Number of elements found = %u\n", $ElementsFound
		end
		if $argc == 5
			set $idx1 = $arg3
			set $idx2 = $arg4
			set $ElementsFound = 0
			while $i < $tree_size
				set $value = (void *)($node + 1)
				set $valueLeft = *($arg1*)$value
				set $valueRight = *($arg2*)($value + sizeof($arg1))
				if $valueLeft == $idx1 && $valueRight == $idx2
					printf "elem[%u].left: ", $i
					p $valueLeft
					printf "elem[%u].right: ", $i
					p $valueRight
					set $ElementsFound++
				end
				if $node._M_right != 0
					set $node = $node._M_right
					while $node._M_left != 0
						set $node = $node._M_left
					end
				else
					set $tmp_node = $node._M_parent
					while $node == $tmp_node._M_right
						set $node = $tmp_node
						set $tmp_node = $tmp_node._M_parent
					end
					if $node._M_right != $tmp_node
						set $node = $tmp_node
					end
				end
				set $i++
			end
			printf "Number of elements found = %u\n", $ElementsFound
		end
		printf "Map size = %u\n", $tree_size
	end
end

document pmap
	Prints std::map<TLeft and TRight> or std::multimap<TLeft and TRight> information. Works for std::multimap as well.
	Syntax: pmap <map> <TtypeLeft> <TypeRight> <valLeft> <valRight>: Prints map size, if T defined all elements or just element(s) with val(s)
	Examples:
	pmap m - prints map size and definition
	pmap m int int - prints all elements and map size
	pmap m int int 20 - prints the element(s) with left-value = 20 (if any) and map size
	pmap m int int 20 200 - prints the element(s) with left-value = 20 and right-value = 200 (if any) and map size
end


define pmap_member
	if $argc == 0
		help pmap_member
	else
		set $tree = $arg0
		set $i = 0
		set $node = $tree._M_t._M_impl._M_header._M_left
		set $end = $tree._M_t._M_impl._M_header
		set $tree_size = $tree._M_t._M_impl._M_node_count
		if $argc == 1
			printf "Map "
			whatis $tree
			printf "Use pmap <variable_name> <left_element_type> <right_element_type> to see the elements in the map.\n"
		end
		if $argc == 5
			while $i < $tree_size
				set $value = (void *)($node + 1)
				printf "elem[%u].left: ", $i
				p (*($arg1*)$value).$arg2
				set $value = $value + sizeof($arg1)
				printf "elem[%u].right: ", $i
				p (*($arg3*)$value).$arg4
				if $node._M_right != 0
					set $node = $node._M_right
					while $node._M_left != 0
						set $node = $node._M_left
					end
				else
					set $tmp_node = $node._M_parent
					while $node == $tmp_node._M_right
						set $node = $tmp_node
						set $tmp_node = $tmp_node._M_parent
					end
					if $node._M_right != $tmp_node
						set $node = $tmp_node
					end
				end
				set $i++
			end
		end
		if $argc == 6
			set $idx = $arg5
			set $ElementsFound = 0
			while $i < $tree_size
				set $value = (void *)($node + 1)
				if *($arg1*)$value == $idx
					printf "elem[%u].left: ", $i
					p (*($arg1*)$value).$arg2
					set $value = $value + sizeof($arg1)
					printf "elem[%u].right: ", $i
					p (*($arg3*)$value).$arg4
					set $ElementsFound++
				end
				if $node._M_right != 0
					set $node = $node._M_right
					while $node._M_left != 0
						set $node = $node._M_left
					end
				else
					set $tmp_node = $node._M_parent
					while $node == $tmp_node._M_right
						set $node = $tmp_node
						set $tmp_node = $tmp_node._M_parent
					end
					if $node._M_right != $tmp_node
						set $node = $tmp_node
					end
				end
				set $i++
			end
			printf "Number of elements found = %u\n", $ElementsFound
		end
		printf "Map size = %u\n", $tree_size
	end
end

document pmap_member
	Prints std::map<TLeft and TRight> or std::multimap<TLeft and TRight> information. Works for std::multimap as well.
	Syntax: pmap <map> <TtypeLeft> <TypeRight> <valLeft> <valRight>: Prints map size, if T defined all elements or just element(s) with val(s)
	Examples:
	pmap_member m class1 member1 class2 member2 - prints class1.member1 : class2.member2
	pmap_member m class1 member1 class2 member2 lvalue - prints class1.member1 : class2.member2 where class1 == lvalue
end


#
# std::set and std::multiset
#

define pset
	if $argc == 0
		help pset
	else
		set $tree = $arg0
		set $i = 0
		set $node = $tree._M_t._M_impl._M_header._M_left
		set $end = $tree._M_t._M_impl._M_header
		set $tree_size = $tree._M_t._M_impl._M_node_count
		if $argc == 1
			printf "Set "
			whatis $tree
			printf "Use pset <variable_name> <element_type> to see the elements in the set.\n"
		end
		if $argc == 2
			while $i < $tree_size
				set $value = (void *)($node + 1)
				printf "elem[%u]: ", $i
				p *($arg1*)$value
				if $node._M_right != 0
					set $node = $node._M_right
					while $node._M_left != 0
						set $node = $node._M_left
					end
				else
					set $tmp_node = $node._M_parent
					while $node == $tmp_node._M_right
						set $node = $tmp_node
						set $tmp_node = $tmp_node._M_parent
					end
					if $node._M_right != $tmp_node
						set $node = $tmp_node
					end
				end
				set $i++
			end
		end
		if $argc == 3
			set $idx = $arg2
			set $ElementsFound = 0
			while $i < $tree_size
				set $value = (void *)($node + 1)
				if *($arg1*)$value == $idx
					printf "elem[%u]: ", $i
					p *($arg1*)$value
					set $ElementsFound++
				end
				if $node._M_right != 0
					set $node = $node._M_right
					while $node._M_left != 0
						set $node = $node._M_left
					end
				else
					set $tmp_node = $node._M_parent
					while $node == $tmp_node._M_right
						set $node = $tmp_node
						set $tmp_node = $tmp_node._M_parent
					end
					if $node._M_right != $tmp_node
						set $node = $tmp_node
					end
				end
				set $i++
			end
			printf "Number of elements found = %u\n", $ElementsFound
		end
		printf "Set size = %u\n", $tree_size
	end
end

document pset
	Prints std::set<T> or std::multiset<T> information. Works for std::multiset as well.
	Syntax: pset <set> <T> <val>: Prints set size, if T defined all elements or just element(s) having val
	Examples:
	pset s - prints set size and definition
	pset s int - prints all elements and the size of s
	pset s int 20 - prints the element(s) with value = 20 (if any) and the size of s
end



#
# std::dequeue
#

define pdequeue
	if $argc == 0
		help pdequeue
	else
		set $size = 0
		set $start_cur = $arg0._M_impl._M_start._M_cur
		set $start_last = $arg0._M_impl._M_start._M_last
		set $start_stop = $start_last
		while $start_cur != $start_stop
			p *$start_cur
			set $start_cur++
			set $size++
		end
		set $finish_first = $arg0._M_impl._M_finish._M_first
		set $finish_cur = $arg0._M_impl._M_finish._M_cur
		set $finish_last = $arg0._M_impl._M_finish._M_last
		if $finish_cur < $finish_last
			set $finish_stop = $finish_cur
		else
			set $finish_stop = $finish_last
		end
		while $finish_first != $finish_stop
			p *$finish_first
			set $finish_first++
			set $size++
		end
		printf "Dequeue size = %u\n", $size
	end
end

document pdequeue
	Prints std::dequeue<T> information.
	Syntax: pdequeue <dequeue>: Prints dequeue size, if T defined all elements
	Deque elements are listed "left to right" (left-most stands for front and right-most stands for back)
	Example:
	pdequeue d - prints all elements and size of d
end



#
# std::stack
#

define pstack
	if $argc == 0
		help pstack
	else
		set $start_cur = $arg0.c._M_impl._M_start._M_cur
		set $finish_cur = $arg0.c._M_impl._M_finish._M_cur
		set $size = $finish_cur - $start_cur
        set $i = $size - 1
        while $i >= 0
            p *($start_cur + $i)
            set $i--
        end
		printf "Stack size = %u\n", $size
	end
end

document pstack
	Prints std::stack<T> information.
	Syntax: pstack <stack>: Prints all elements and size of the stack
	Stack elements are listed "top to buttom" (top-most element is the first to come on pop)
	Example:
	pstack s - prints all elements and the size of s
end



#
# std::queue
#

define pqueue
	if $argc == 0
		help pqueue
	else
		set $start_cur = $arg0.c._M_impl._M_start._M_cur
		set $finish_cur = $arg0.c._M_impl._M_finish._M_cur
		set $size = $finish_cur - $start_cur
        set $i = 0
        while $i < $size
            p *($start_cur + $i)
            set $i++
        end
		printf "Queue size = %u\n", $size
	end
end

document pqueue
	Prints std::queue<T> information.
	Syntax: pqueue <queue>: Prints all elements and the size of the queue
	Queue elements are listed "top to bottom" (top-most element is the first to come on pop)
	Example:
	pqueue q - prints all elements and the size of q
end



#
# std::priority_queue
#

define ppqueue
	if $argc == 0
		help ppqueue
	else
		set $size = $arg0.c._M_impl._M_finish - $arg0.c._M_impl._M_start
		set $capacity = $arg0.c._M_impl._M_end_of_storage - $arg0.c._M_impl._M_start
		set $i = $size - 1
		while $i >= 0
			p *($arg0.c._M_impl._M_start + $i)
			set $i--
		end
		printf "Priority queue size = %u\n", $size
		printf "Priority queue capacity = %u\n", $capacity
	end
end

document ppqueue
	Prints std::priority_queue<T> information.
	Syntax: ppqueue <priority_queue>: Prints all elements, size and capacity of the priority_queue
	Priority_queue elements are listed "top to buttom" (top-most element is the first to come on pop)
	Example:
	ppqueue pq - prints all elements, size and capacity of pq
end



#
# std::bitset
#

define pbitset
	if $argc == 0
		help pbitset
	else
        p /t $arg0._M_w
	end
end

document pbitset
	Prints std::bitset<n> information.
	Syntax: pbitset <bitset>: Prints all bits in bitset
	Example:
	pbitset b - prints all bits in b
end



#
# std::string
#

define pstring
	if $argc == 0
		help pstring
	else
		printf "String \t\t\t= \"%s\"\n", $arg0._M_data()
		printf "String size/length \t= %u\n", $arg0._M_rep()._M_length
		printf "String capacity \t= %u\n", $arg0._M_rep()._M_capacity
		printf "String ref-count \t= %d\n", $arg0._M_rep()._M_refcount
	end
end

document pstring
	Prints std::string information.
	Syntax: pstring <string>
	Example:
	pstring s - Prints content, size/length, capacity and ref-count of string s
end

#
# std::wstring
#

define pwstring
	if $argc == 0
		help pwstring
	else
		call printf("WString \t\t= \"%ls\"\n", $arg0._M_data())
		printf "WString size/length \t= %u\n", $arg0._M_rep()._M_length
		printf "WString capacity \t= %u\n", $arg0._M_rep()._M_capacity
		printf "WString ref-count \t= %d\n", $arg0._M_rep()._M_refcount
	end
end

document pwstring
	Prints std::wstring information.
	Syntax: pwstring <wstring>
	Example:
	pwstring s - Prints content, size/length, capacity and ref-count of wstring s
end

# enable and disable shortcuts for stop-on-solib-events fantastic trick!
define enablesolib
    set stop-on-solib-events 1
end
document enablesolib
Shortcut to enable stop-on-solib-events trick!
end

define disablesolib
    set stop-on-solib-events 0
end
document disablesolib
Shortcut to disable stop-on-solib-events trick!
end

# enable commands for different displays
define enableobjectivec
    set $SHOWOBJECTIVEC = 1
end
document enableobjectivec
Enable display of objective-c information in the context window
end

define enablecpuregisters
    set $SHOWCPUREGISTERS = 1
end
document enablecpuregisters
Enable display of cpu registers in the context window
end

define enablestack
    set $SHOWSTACK = 1
end
document enablestack
Enable display of stack in the context window
end

define enabledatawin
    set $SHOWDATAWIN = 1
end
document enabledatawin
Enable display of data window in the context window
end

# disable commands for different displays
define disableobjectivec
    set $SHOWOBJECTIVEC = 0
end
document disableobjectivec
Disable display of objective-c information in the context window
end

define disablecpuregisters
    set $SHOWCPUREGISTERS = 0
end
document disablecpuregisters
Disable display of cpu registers in the context window
end

define disablestack
    set $SHOWSTACK = 0
end
document disablestack
Disable display of stack information in the context window
end

define disabledatawin
    set $SHOWDATAWIN = 0
end
document disabledatawin
Disable display of data window in the context window
end

define 32bits
    set $64BITS = 0
end
document 32bits
Set gdb to work with 32bits binaries
end

define 64bits
    set $64BITS = 1
end
document 64bits
Set gdb to work with 64bits binaries
end

#EOF
