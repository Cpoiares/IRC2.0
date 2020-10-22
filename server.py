import socket
import sys
import collections
import threading
import queue
import _thread
import errno
import string
import os.path
import time
from socketserver import ThreadingMixIn


global command
command = ""
HOST = "127.0.0.1"
PORT = 9000
PORT2 = 8000
BUFFER = 1024

exit_control = False
exitLock = threading.Lock()
lock = threading.Lock() # lock de info e mensagens 
groupLock = threading.Lock() # lock de info de groupos
clientMessages = {} # Dicionario de keys = clientes online; values = message queue de mensagens a enviar para o cliente
groupchats = {} # dicionario de keys = grupos criados; values = participantes do grupo
groups = [] # Dicionario de grupos auxiliar
activeUsers=[] # User ativos auxiliar
userfdmap = [] # User fd lista com os clientes str = 'user_name' + 'fd da socket'
blocked_conns = {} # Dicionario de conexoes bloqueadas
client_threads = {} # dicionario de threads keys = socket.fd; values = id da thread
banned_names = ['-send', '-group()', '-inbox()', '-help()', '-group()', '-create', '-remove', '-add', '-block', '-report'] # Nomes de grupos banidos
     
    
    
# ---------------------Thread connectada ao send port do servidor ---------------------
class ClientSendThread(threading.Thread):
    def __init__(self, socket, name):
        threading.Thread.__init__(self)
        self.socket = socket
        self.user_name = name
        print('Sending to ' + self.user_name)

    def run(self):
        tcpsock2.listen(1)
        (conn2,addr) = tcpsock2.accept()
        print("Connected", conn2.fileno(), self.socket.fileno())
        checkinbox = self.user_name + 'inbox.txt' # Verifica se ha ficheiro inbox
        if os.path.exists(checkinbox) == True: 
            message = '-SERVER-> You have unread messages! Enter inbox() for see them.' 
            lock.acquire()
            clientMessages[self.socket.fileno()].put(message)
            lock.release()
            
        while True:
            try: 
                if not clientMessages[self.socket.fileno()].empty(): 
                    lock.acquire()
                    message = clientMessages.get(self.socket.fileno()).get(False)
                    lock.release()
                    print("Sending message to " + str(self.socket.fileno()))
                    conn2.send(message.encode())
                    write = message.partition(" ")
                    if ('-' == write[0][0]) | ('+' == write[0][0]):
                        pass
                    else:
                        if write[0] == 'SEND':
                            writeFile(message, self.user_name)
                        else:    
                            message = 'RECEIVED-> ' + message + '\0'
                            writeFile(message, self.user_name)
                    if exit_control:
                        os._exit(1)
            except queue.Empty:
                time.sleep(2)
                
            except KeyError: 
                pass

# ---------------------Thread connectada ao receive port do servidor ---------------------
class ClientReadThread(threading.Thread):
    def __init__(self, socket, ip, port, user_name):
        threading.Thread.__init__(self)
        self.socket = socket
        self.user_name = user_name
        print('Listening to ' + user_name)

        
    def run(self):
        while True:
            online = False
            e = False
            if exit_control:
                os._exit()
            try:
                command = self.socket.recv(BUFFER).decode() # Recebe comando do cliente
            except socket.error: # Controlo de erros
                print(self.user_name+ 's socket is not currently open, exiting...\0') 
                quit(self)
            command_aux = command.partition(" ")
            if command != '':
                # ---------------------MENU---------------------
                if 'send' in command:
                    send(self,command)
                elif 'group()' in command:
                    group(self, command)                 
                elif ('inbox()' in command) & (len(command) == 7):
                    inbox(self, command)
                elif ('whoon()' == command) & (len(command) == 7):
                    whoon(self, command)                
                elif ('help()' == command) &  (len(command) == 6):
                    help(self)
                elif ('block()' in command) & (len(command_aux[0]) == 7):
                    block(self, command)
                elif 'unblock()' in command: 
                    unblock(self, command)
                elif 'list()' == command:
                    printConv(self)
                elif ('quit()' == command) & (len(command)) == 6:
                    quit(self) 
                
                else:
                    # User help
                    msg = '-SERVER-> Invalid command, enter help() to list the commands'
                    clientMessages[self.socket.fileno()].put(msg)
  
        
# ---------------------SEND FUNCTION---------------------                    
def send(self,command):
    content = command.partition(" ")
    contentinner = content[2].partition(" ") 
    sendmsg = self.user_name + ": " + contentinner[2] 
    receiver = contentinner[0]
    try:
        if self.user_name in blocked_conns[receiver]: # Verifica se esta bloqueado
            msg = '-SERVER-> Blocked by ' + receiver + '.'
            clientMessages[self.socket.fileno()].put(msg) 
        else:
            msg = ('SEND -> ' + sendmsg + '\n') # Tenta enviar
            clientMessages[self.socket.fileno()].put(msg)
            clientMessages[receiver].put(sendmsg)
    except KeyError: # Se key Error e porque nao esta receiver nao e key de blocked cons e porque e um canal livre 
        if receiver not in activeUsers: # Se receiver nao estiver no dicionario, nao esta online
            msg = "-SERVER-> User " + receiver + " not online. Sending note." + '\n'
            lock.acquire()
            clientMessages[self.socket.fileno()].put(msg)            
            msg = ('SEND -> ' + sendmsg + '\n') # Tenta enviar            
            clientMessages[self.socket.fileno()].put(msg)            
            lock.release()
            receiver = receiver + 'inbox'
            writeFile(sendmsg, receiver)
            
        else: # Se e livre e esta online mete na message queue de receiver fd
            for z in userfdmap: # Procura em user fdmap
                zi = z.partition(" ")
                if receiver == zi[0]:
                    receiverfd = int(zi[2])
                    online = True
                    lock.acquire()
                    clientMessages[receiverfd].put(sendmsg)
                    sendmsg = 'SENT -> ' + sendmsg
                    lock.release()

# ---------------------GROUP FUNCTION---------------------                    
def group(self, command):
    sub_command = command.partition(" ") # sub comando do grupo #group() subcommand(create, add, remove)
    group_command = sub_command[2].partition(" ") # command
    
    # ---------------------CREATE FUNCTION---------------------                    
    if group_command[0] == "create": # se group() _create
        group_name = group_command[2] # group name 3 entrada de group_command
        if group_name not in banned_names:
            group_users = [self.user_name] # Criador primeiro do array
            sendmsg = "-SERVER-> " + group_name + " created sucessfully."
            clientMessages[self.socket.fileno()].put(sendmsg)
            groupLock.acquire()
            groups.append(group_command[2]) # Append Group name
            groupchats[group_command[2]] = group_users #Inicializa dicionario de groupchat -> groupusers
            groupLock.release()
            
    # ---------------------ADD FUNCTION---------------------                            
    elif group_command[0] == "add": # group() add
        group_name = group_command[2].partition(" ") 
        if group_name[0] == '': # Controlo de user
            sendmsg = '-SERVER-> Enter a valid user_name to add!'
            lock.acquire()
            clientMessages[self.socket.fileno()].put(sendmsg)
            lock.release()
            return
        
        # ---------------------SEND FUNCTION---------------------                            
        if group_name[0] in groups: # Se o grupo existir ao que esta a tentar adicionar
            if self.user_name in groupchats[group_name[0]]:                            
                groupLock.acquire()
                groupchats[group_name[0]].append(group_name[2]) # Faz append ao lista do grupo do dicionario groupchats
                groupLock.release()
                sendmsg = "-SERVER-> User " + group_name[2] + " has been added to " + group_name[0] + " ."
                lock.acquire()
                clientMessages[self.socket.fileno()].put(sendmsg)
                for z in userfdmap:
                    zi = z.partition(" ")
                    if zi[0] == group_name[2]: # Notifica user adicionado
                        sendmsg = "-SERVER-> You have been added to " + group_name[0] + " by " + self.user_name
                        clientMessages[int(zi[2])].put(sendmsg)
                lock.release()
            else:
                sendmsg = "-SERVER-> You are not a member of " + group_name[0] + ", you must be a member to add users"
                lock.acquire()
                clientMessages[self.socket.fileno()].put(sendmsg)
                lock.release()
        else: 
            sendmsg = "-SERVER-> " + group_name[0] + " does not exit." # Controlo de erros
            lock.acquire()
            clientMessages[self.socket.fileno()].put(sendmsg)
            lock.release()
            
    elif group_command[0] == "remove": # Se remover
        group_name = group_command[2].partition(" ")
        if group_name[0] in groups: # Se grupo existir
            if self.user_name == groupchats[group_name[0]][0]: # E se user em questao criador
                groupLock.acquire()
                if group_name[2] in groupchats[group_name[0]]:
                    groupchats[group_name[0]].remove(group_name[2]) #Remover da lista da conversa
                    groupLock.release()
                    sendmsg = "-SERVER-> Removed " + group_name[2] + " from " + group_name[0] + " sucessfully."
                    lock.acquire()
                    clientMessages[self.socket.fileno()].put(sendmsg)
                    lock.release()
                    return
                else:
                    sendmsg = "-SERVER-> User " + group_name[2] + " is not in group " + group_name[0] # Controlo de user
                    lock.acquire()
                    clientMessages[self.socket.fileno()].put(sendmsg)
                    lock.release()
            else:
                sendmsg = "-SERVER-> You must be the creator of the group, and guess what, you are not." # Controlo de user
                lock.acquire()                
                clientMessages[self.socket.fileno()].put(sendmsg)
                lock.release()
        else:
            sendmsg = "-SERVER-> Group " + group_name[0] + " does not exist." # Controlo de user
            lock.acquire()
            clientMessages[self.socket.fileno()].put(sendmsg)
            lock.release()
            
    elif group_command[0] in groups: # se o subcomando for um dos grupos e mensagem
        if self.user_name in groupchats[group_command[0]]: # Se este user_name pertencer ao grupo
            message_sent = False
            sendmsg = group_command[0] + "- " + self.user_name + ": " + group_command[2]                          
            for p in groupchats[group_command[0]]: # Procura fd e envia para todos do grupo
                for z in userfdmap:
                    zi = z.partition(" ")
                    if zi[0] == p:
                        lock.acquire()
                        clientMessages[int(zi[2])].put(sendmsg)
                        lock.release()
                        message_sent = True
                if not message_sent: # Nao estava online
                    p = p + 'inbox'
                    sendmsg = '+' + sendmsg                    
                    writeFile(sendmsg, p)
        else:
            sendmsg = "-SERVER-> You are not part of " + group_command[0] + " . Get invited from a group user." # tentar enviar para grupo que nao pertence
            lock.acquire()
            clientMessages[self.socket.fileno()].put(sendmsg)
            lock.release()
            
# ---------------------INBOX FUNCTION---------------------                    
def inbox(self, command):
    sendmsg = ""
    filename = self.user_name + 'inbox' + '.txt' # Caixa de correio
    try: 
        file = open(filename, "r") # Tenta abrir e envia, ao enviar grava no ficheiro
        file.seek(0)
        for msg in file:
            sendmsg = sendmsg + "\n" + msg
        lock.acquire()
        clientMessages[self.socket.fileno()].put(sendmsg)    
        lock.release()
        file.close()
        os.remove(filename) # Apaga o ficheiro
    
    except IOError:
        sendmsg = "-SERVER-> Inbox empty." 
        clientMessages[self.socket.fileno()].put(sendmsg)

# ---------------------WHOON FUNCTION---------------------                    
def whoon(self, command):                    
    sendmsg = '-SERVER-> USERS ONLINE: ' # Ve quem esta online
    for z in activeUsers:
        if z != self.user_name:
            sendmsg = sendmsg + '|' + z
    lock.acquire() 
    clientMessages[self.socket.fileno()].put(sendmsg)
    lock.release()
    
# ---------------------BLOCK FUNCTION---------------------                    
def block(self, command):
    user = command.partition(" ")
    if user[2] == self.user_name: # Blocking yourself
        sendmsg = 'Do you really wanna do that.'
        lock.acquires()
        clientMessages[self.socket.fileno()].put(sendmsg)
        lock.release()
    sendmsg = '-SERVER-> You just blocked '+ user[2] + ' sucessfully!'
    lock.acquire()
    blocked_conns[self.user_name].append(user[2]) # Atualiza dicionario de ligacoes
    clientMessages[self.socket.fileno()].put(sendmsg)
    lock.release()
    
# ---------------------UNBLOCK FUNCTION---------------------                    
def unblock(self, command):
    user = command.partition(" ")
    if user[2] not in blocked_conns[self.user_name]: # Desbloquear nao bloqueado
        sendmsg = '-SERVER-> ' + user[2] + ' isnt even blocked.'
        lock.acquire()
        clientMessages[-self.socket.fileno()].put(sendmsg)
        lock.release()
    else:
        sendmsg = '-SERVER-> You just unblocked '+ user[2] + ' sucessfully!'        
        lock.acquire()
        blocked_conns[self.user_name].remove(user[2])
        clientMessages[self.socket.fileno()].put(sendmsg)
        lock.release()
        
# ---------------------HELP FUNCTION---------------------                    
def help(self):
    sendmsg = "-SERVER->SEND COMMANDS:\n#send user_name msg\n\nWHOON:\n#whoon()\n\nQUIT:\n#quit()\n\nGROUPCHAT COMMANDS:\n#group() create groupname\n#group() add groupname username\n#group() groupname msg\n \nUnread Messages:\n#inbox()\n\nList chat history:\n#list()\nBLOCK:\n#block() username | #unblock() username\n"
    clientMessages[self.socket.fileno()].put(sendmsg)   # Help Command

# ---------------------LIST FUNCTION---------------------                    
def printConv(self):
    sendmsg = '-SERVER-> --------------PRINTING ' + self.user_name + ' RECORDS--------------\n'
    lock.acquire()
    clientMessages[self.socket.fileno()].put(sendmsg)
    lock.release()
    filename = self.user_name + '.txt'
    try:
        file = open(filename, "r")
        sendmsg = ""
        file.seek(0)
        for msg in file:
            msg = '-'+msg
            sendmsg = sendmsg + msg # Envia como mensagem
        lock.acquire()
        clientMessages[self.socket.fileno()].put(sendmsg)    
        lock.release()  
    except IOError: # Se nao abre nunca esteve no servidor
        sendmsg = "-SERVER-> Looks like no conversations were recorded! Try to chat first."
        lock.acquire()
        clientMessages[self.socket.fileno()].put(sendmsg)
        lock.release()        

# ---------------------WRITE FUNCTION---------------------                    
def writeFile(sendmsg, name):
    localtime = time.strftime('%H:%M:%S') # Timestamp
    sendmsg = localtime + ' -> ' + sendmsg
    filename = name + '.txt'
    file = open(filename, "a+")
    file.write(sendmsg)
    file.write('\n')
    lines = file.readlines()
    format = "%H:%M:%S" # Sempre que escreve ordena
    sort_lines = sorted(lines, key = lambda line: time.strptime(line.partition(" ")[0], format, reverse = True))
    for line in sort_lines:
        file.write(line)
    file.close()
    
# ---------------------QUIT FUNCTION---------------------                    
def quit(self):
    print('Client ' + self.user_name + ' has left the chat.\n') 
    lock.acquire() # Saida controlada e remocao antes de a thread morrer                  
    clientMessages.pop(self.socket.fileno())
    activeUsers.remove(self.user_name)
    for z in userfdmap:
        if str(self.socket.fileno()) in userfdmap:
            userfdmap.remove(z)
    client_threads[self.socket.fileno()][0].join()
    client_threads[self.socket.fileno()][1].join()
    lock.release()
    self.socket.close()
    

# ---------------------MAIN PROG---------------------                        
tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria socket de escuta
tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
tcpsock.bind(('', PORT))
tcpsock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Cria socket de envio
tcpsock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcpsock2.bind(('', PORT2))

while True:
    try:
        tcpsock.listen(10) 
        print ("\nWELCOME TO THE CHAT SERVER\nSERVER WAITING FOR CONNECTIONS.\n")
        (conn, (ip,port)) = tcpsock.accept()
        threads = []
        login = True
        user_name = ''
        fd = conn.fileno()
        q = queue.Queue()
        print('SERVER-> Welcome ',conn.fileno())      
        user_name = conn.recv(BUFFER).decode()
        if user_name != '': # Se user name valido append info para dicionarios
            lock.acquire()
            userinfo = user_name + ' ' + str(fd)
            activeUsers.append(user_name)
            userfdmap.append(userinfo)
            blocked_conns[user_name] = []
            clientMessages[fd] = q
            msg = '-SERVER-> Welcome to the server ' + user_name + ' If you need anything just type help().'
            clientMessages[fd].put(msg)            
            login = True
            lock.release()
            
        ReadingThread = ClientReadThread(conn, HOST, PORT, user_name) # Inicializa threads de escusa e envio
        ReadingThread.daemon = True
        SendingThread = ClientSendThread(conn, user_name)
        SendingThread.daemon = True            
        
        SendingThread.start()
        ReadingThread.start()
        threads.append(SendingThread)
        threads.append(ReadingThread)
        client_threads[fd] = threads
    except KeyboardInterrupt:
        print ("\nINFO: KeyboardInterrupt")
        print ("* Closing all sockets and exiting chat server... Goodbye! *")
        exitLock.acquire()
        exit_control = True
        exitLock.release()
        for thread in threads:
            thread.join()
        exit(0)
