import socket
import sys
import collections
import threading
import queue
import _thread
import errno
import os.path
import time
from socketserver import ThreadingMixIn


global command
command = ""
HOST = "127.0.0.1"
PORT = 9000
PORT2 = 8000
BUFFER = 1024

exitLock = threading.Lock()
lock = threading.Lock()
groupLock = threading.Lock()
clientMessages = {}
groupchats = {}
groups = []
activeUsers=[]
userfdmap = []
blocked_conns = {}
client_threads = {}


class ClientSendThread(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.socket = socket

    def run(self):
        tcpsock2.listen(1)
        (conn2,addr) = tcpsock2.accept()
        print("Connected", conn2.fileno(), self.socket.fileno())
        name = ''
        for z in userfdmap:
            zi = z.partition(" ")
            if str(zi[2]) == str(self.socket.fileno()):
                name = zi[0]
        if os.path.exists(name + 'inbox.txt') == True:
            sendmsg = "You got unread messages! Type inbox() to make them pop on the screen.\n"
            conn2.send(sendmsg.encode())
            
        while True:
            try: 
                if not clientMessages[self.socket.fileno()].empty():
                    lock.acquire()
                    message = clientMessages.get(self.socket.fileno()).get(False)
                    lock.release()
                    print("Sending message to ", self.socket.fileno())
                    conn2.send(message.encode())
                    write = message.partition(" ")
                    if write[0] != 'SERVER:':
                        message = 'RECEIVED: ' + message
                        writeFile(message, name)
                    
            except queue.Empty:
                chat = "none"
                time.sleep(2)
                
            except KeyError: 
                pass

class ClientReadThread(threading.Thread):
    def __init__(self, socket, ip, port, user_name):
        threading.Thread.__init__(self)
        self.socket = socket
        self.ip = "127.0.0.1"
        self.port = PORT
        self.user_name = user_name
        print('Listening to' + user_name)

        
    def run(self):
        while True:
            online = False
            e = False
            try:
                command = self.socket.recv(BUFFER).decode()
                
            except socket.error:
                print(self.user_name+ 's socket is not currently open, exiting...')
                quit(self)
            if command != '':
                
                if "send" in command:
                    send(self,command)
                elif 'group()' in command:
                    group(self, command)                 
                elif 'inbox()' == command:
                    inbox(self, command)
                elif 'whoon()' == command:
                    whoon(self, command)                
                elif 'help()' == command:
                    help(self)
                elif 'block()' in command:
                    block(self, command)
                elif 'unblock()' in command: 
                    unblock(self, command)
                elif 'list()' == command:
                    printConv(self)
                elif 'quit()' == command:
                    quit(self) 
                    
def send(self,command):
    content = command.partition(" ")
    contentinner = content[2].partition(" ") 
    sendmsg = self.user_name + ": " + contentinner[2] 
    receiver = contentinner[0]
    try:
        if self.user_name in blocked_conns[receiver]:
            msg = 'SERVER: You are currently blocked by ' + receiver + '.'
            clientMessages[self.socket.fileno()].put(msg)
    except KeyError:
        if receiver not in activeUsers:
            msg = "SERVER: User " + receiver + " not online appending to his file."
            lock.acquire()
            clientMessages[self.socket.fileno()].put(msg)
            lock.release()
            receiver = receiver + 'inbox'
            writeFile(sendmsg, receiver)       
        else:
            for z in userfdmap:
                zi = z.partition(" ")
                if receiver == zi[0]:
                    receiverfd = int(zi[2])
                    online = True
                    lock.acquire()
                    clientMessages[receiverfd].put(sendmsg)
                    sendmsg = 'SENT: ' + sendmsg
                    writeFile(sendmsg, self.user_name)
                    lock.release()

def group(self, command):
    sub_command = command.partition(" ")
    group_command = sub_command[2].partition(" ")
    if group_command[0] == "create":
        group_name = group_command[2]
        group_users = [self.user_name]
        sendmsg = "SERVER: New group " + group_name + " created sucessfully."
        clientMessages[self.socket.fileno()].put(sendmsg)
        groupLock.acquire()
        groups.append(group_command[2])
        groupchats[group_command[2]] = group_users
        groupLock.release()
           
    elif group_command[0] == "add":
        group_name = group_command[2].partition(" ")
        if group_name[0] in groups:
            if self.user_name in groupchats[group_name[0]]:                            
                groupLock.acquire()
                groupchats[group_name[0]].append(group_name[2])                   
                groupLock.release()
                sendmsg = "SERVER: User " + group_name[2] + " has been added to " + group_name[0] + " has asked. "
                lock.acquire()
                clientMessages[self.socket.fileno()].put(sendmsg)
                for z in userfdmap:
                    zi = z.partition(" ")
                    if zi[0] == group_name[2]:
                        sendmsg = "SERVER: You been added to " + group_name[0] + " by " + self.user_name
                        clientMessages[int(zi[2])].put(sendmsg)
                lock.release()
            else:
                sendmsg = "SERVER: You are not a member of " + group_name[0] + ", you must be a member to add users"
                lock.acquire()
                clientMessages[self.socket.fileno()].put(sendmsg)
                lock.release()
        else: 
            sendmsg = "SERVER: " + group_name[0] + " does not exit."
            lock.acquire()
            clientMessages[self.socket.fileno()].put(sendmsg)
            lock.release()
            
    elif group_command[0] == "remove":
        group_name = group_command[2].partition(" ")
        if group_name[0] in groups: 
            if self.user_name == groupchats[group_name[0]][0]:
                groupLock.acquire()
                if group_name[2] in groupchats[group_name[0]]:
                    groupchats[group_name[0]].remove(group_name[2])
                    groupLock.release()
                    sendmsg = "SERVER: Removed " + group_name[2] + " from " + group_name[0] + " sucessfully."
                    lock.acquire()
                    clientMessages[self.socket.fileno()].put(sendmsg)
                    lock.release()
                    return
                else:
                    lock.acquire()
                    sendmsg = "SERVER: User " + group_name[2] + " is not in group " + group_name[0]
                    clientMessages[self.socket.fileno()].put(sendmsg)
                    lock.release()
            else:
                lock.acquire()
                sendmsg = "SERVER: You must be the creator of the group, and guess what, you are not."
                clientMessages[self.socket.fileno()].put(sendmsg)
                lock.release()
        else:
            lock.acquire()
            sendmsg = "SERVER: Group " + group_name[0] + " does not exist."
            clientMessages[self.socket.fileno()].put(sendmsg)
            lock.release()
            
    elif group_command[0] in groups: 
        if self.user_name in groupchats[group_command[0]]:
            message_sent = False
            sendmsg = group_command[0] + "- " + self.user_name + ": " + group_command[2]                          
            for p in groupchats[group_command[0]]:
                for z in userfdmap:
                    zi = z.partition(" ")
                    if zi[0] == p:
                        lock.acquire()
                        clientMessages[int(zi[2])].put(sendmsg)
                        lock.release()
                        message_sent = True
                if not message_sent:
                    p = p + 'inbox'
                    writeFile(sendmsg, p)
        else:
            sendmsg = "SERVER: You are not part of " + group_command[0] + " get invited from a group user."
            lock.acquire()
            clientMessages[self.socket.fileno()].put(sendmsg)
            lock.release()
def inbox(self, command):
    sendmsg = ""
    filename = self.user_name + 'inbox' + '.txt'
    try: 
        file = open(filename, "r")
        file.seek(0)
        for msg in file:
            sendmsg = sendmsg + "\n" + msg
        lock.acquire()
        clientMessages[self.socket.fileno()].put(sendmsg)    
        lock.release()
    
    except IOError:
        sendmsg = "SERVER: Inbox empty."
        clientMessages[self.socket.fileno()].put(sendmsg)
       
def whoon(self, command):                    
    sendmsg = 'SERVER: USERS ONLINE: '
    for z in activeUsers:
        if z != self.user_name:
            sendmsg = sendmsg + '|' + z
    lock.acquire() 
    clientMessages[self.socket.fileno()].put(sendmsg)
    lock.release()
    
def block(self, command):
    user = command.partition(" ")
    sendmsg = 'SERVER: You just blocked '+ user[2] + ' sucessfully!'
    lock.acquire()
    blocked_conns[self.user_name].append(user[2])
    clientMessages[self.socket.fileno()].put(sendmsg)
    lock.release()
    
def unblock(self, command):
    user = command.partition(" ")
    if user[2] not in blocked_conns[self.user_name]:
        sendmsg = 'SERVER: ' + user[2] + ' isnt even blocked.'
        lock.acquire()
        clientMessages[self.socket.fileno()].put(sendmsg)
    else:
        sendmsg = 'SERVER: You just unblocked '+ user[2] + ' sucessfully!'        
        lock.acquire()
        blocked_conns[self.user_name].remove(user[2])
        clientMessages[self.socket.fileno()].put(sendmsg)
        lock.release()
    
def help(self):
    sendmsg = "SERVER: \n\nSEND COMMANDS:\nsend user_name msg\n\nWHOON:\nwhoon()\n\nQUIT:\nquit()\n\nGROUPCHAT COMMANDS:\ngroup() create groupname\ngroup() add groupname username\ngroup() groupname msg\n \nLISTING MESSAGES: Unread Messages->ninbox()\nAll conversations->list()\n \nBLOCK: block() username | unblock() username\n"
    clientMessages[self.socket.fileno()].put(sendmsg)   
    
def printConv(self):
    filename = self.user_name + '.txt'
    try:
        file = open(filename, "r")

    except IOError:
        sendmsg = "SERVER: Looks like no conversations were recorded! Try to chat first."
        lock.acquire()
        clientMessages[self.socket.fileno()].put(sendmsg)
        lock.release()
    sendmsg = ""
    file.seek(0)
    for msg in file:
        sendmsg = sendmsg + "\n" + msg
    lock.acquire()
    clientMessages[self.socket.fileno()].put(sendmsg)    
    lock.release()  
    
    
def writeFile(sendmsg, name):
    localtime = time.strftime('%H:%M:%S')
    sendmsg = localtime + ' -> ' + sendmsg
    filename = name + '.txt'
    file = open(filename, "a+")
    file.write(sendmsg)
    file.write('\n')
    file.close()
    
def quit(self):
    print('Client ' + self.user_name + ' has left the chat.\n') 
    lock.acquire()                   
    clientMessages.pop(self.socket.fileno())
    activeUsers.remove(self.user_name)
    client_threads[self.socket.fileno()][0].join()
    client_threads[self.socket.fileno()][1].join()
    lock.release()
    self.socket.close()
    

tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
tcpsock.bind((HOST, PORT))
tcpsock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpsock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcpsock2.bind(('', PORT2))

while True:
    tcpsock.listen(10)
    print ("\nWELCOME TO THE CHAT SERVER\nSERVER WAITING FOR CONNECTIONS.\n")
    (conn, (ip,port)) = tcpsock.accept()
    threads = []
    login = True
    user_name = ''
    fd = conn.fileno()
    q = queue.Queue()



    print('SERVER: Welcome ',conn.fileno())      
    user_name = conn.recv(BUFFER).decode()
    if user_name != '':
        lock.acquire()
        userinfo = user_name + ' ' + str(fd)
        activeUsers.append(user_name)
        userfdmap.append(userinfo)
        blocked_conns[user_name] = []
        clientMessages[fd] = q
        msg = 'SERVER: Welcome to the server ' + user_name + ' If you need anything just type help()'
        clientMessages[fd].put(msg)   
        login = True
        lock.release()

    ReadingThread = ClientReadThread(conn, HOST, PORT, user_name)
    ReadingThread.daemon = True
    SendingThread = ClientSendThread(conn)
    SendingThread.daemon = True            
  
    SendingThread.start()
    ReadingThread.start()
    threads.append(SendingThread)
    threads.append(ReadingThread)
    client_threads[fd] = threads
  