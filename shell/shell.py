#!/usr/bin/env python3
import os,sys,re,time

def runCommand(args):
    if len(args) == 0:
        return   # Empty
    if args[0] == "exit" and len(args) == 1:
        os.write(1,str.encode("Exiting shell...\n"))
        sys.exit(0)   # Exit
    elif args[0] == "cd" and len(args) == 2:
        try:
            os.chdir(args[1])
        except:
            os.write(2,str.encode("No such file or directory.\n"))
    elif '|' in args:
        pipe(args)   # Pipe
    else:   # Fork
        background = False
        if '&' in args:
            args.remove('&')
            background = True

        rc = os.fork()

        if rc < 0:
            os.write(2, ("fork failed, returning %d\n" % rc).encode())
            sys.exit(1)
        elif rc == 0:   # Child
            execute(args)
            time.sleep(1)
            sys.exit(0)
        else:   # Parent
            if not background:
                childPidCode = os.wait()   # Wait for child to terminate

def pipe(args):
    cmd1 = args[0:args.index('|')]
    cmd2 = args[args.index('|') + 1:]
    
    pr,pw = os.pipe()   # Pair of fds for reading and writing

    print ("Before forking 1st child: Parent:", os.getpid())
    
    rc1 = os.fork()  
    
    if rc1 < 0:
        os.write(2, ("fork failed, returning %d\n" % rc).encode())
        sys.exit(1)
    elif rc1 == 0:   # First Child
        print ("First Child", os.getpid())
        os.close(1)   # Disconnect fd1 from display
        os.dup(pw)
        os.set_inheritable(1,True)

        # Disconnect extra connections to pipe
        for fd in (pr,pw):
            os.close(fd)
            

        os.write(2, (f"{cmd1}").encode())
        execute(cmd1)
        os.write(2, (f"{cmd1}: could not execute\n").encode())
        sys.exit(1)
    elif rc1 > 0:
        print ("Forking second child", os.getpid())
        rc2 = os.fork()
        if rc2 < 0:
            os.write(2, ("fork failed, returning %d\n" % rc).encode())
            sys.exit(1)
        elif rc2 == 0:   # Second Child
            print ("Second Child", os.getpid())
            os.close(0)   # Disconnect stdin
            os.dup(pr)
            os.set_inheritable(0,True)

            for fd in (pw,pr):
                os.close(fd)

            execute(cmd2)
            os.write(2, (f"{cmd1}: could not execute\n").encode())
            sys.exit(1)
        else:
            os.wait()
            sys.exit(0)
    else:
        os.wait()
        sys.exit(0)
        
def execute(args):
    os.write(2, (f"executing...\n").encode())
    if '/' in args[0]:
        program = args[0]
        try:
            os.execve(program, args, os.environ)
        except FileNotFoundError:
            pass
    else:
        # Redirection - Input/Output
        if '>' in args or '<' in args:
            args = redirection(args)

        for dir in re.split(":", os.environ['PATH']): # try each directory in the path
            program = "%s/%s" % (dir, args[0])
            os.write(2, (f"Trying {program}\n").encode())
            try:
                os.execve(program, args, os.environ) # try to exec program
            except FileNotFoundError:             # ...expected
                pass                              # ...fail quietly
        # Command does not exist
        os.write(2, (f"{' '.join(args)}: command not found\n").encode())
        sys.exit(1)

def redirection(args):
    # Input
    if '<' in args:
        loc = args.index('<')
        os.close(0)   # Shell closes std input
        os.open(args[loc + 1], os.O_RDONLY)
        os.set_inheritable(0,True)
        #wc < inputTest.txt 
        del args[loc:loc + 2]
    # Output
    else:
        loc = args.index('>')
        os.close(1)   # Shell closes std output
        os.open(args[loc + 1], os.O_CREAT | os.O_WRONLY)
        os.set_inheritable(1,True)
        #echo hello > testLog.txt
        del args[loc:loc + 2]
    return args

# Run Forever
while True:
    if "PS1" in os.environ:
        os.write(1,str.encode(os.environ["PS1"]))
    else:
        os.environ["PS1"] = "$ "
        os.write(1,str.encode(os.environ["PS1"]))

    # Get Input
    args = os.read(0,10000)
    if len(args) == 0: break   # Done if nothing read
    args = args.decode().split("\n")
    for arg in args:
        runCommand(arg.split())
