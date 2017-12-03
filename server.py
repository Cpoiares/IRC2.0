import socket
import sys
import collections
import threading
import queue
import _thread
import time
from socketserver import ThreadingMixIn
HOST = "127.0.0.1"
PORT = 9000
PORT2 = 8000
BUFFER = 1024



class ClientReadThread(threading.Thread):
    def __init__(self, socket, ip, port, user_name):
        threading.Thread.__init__(self)
        self.socket = socket
        self.ip = "127.0.0.1"
        self.port = PORT
        self.user_name = user_name
        self.groups = {}
        print('Listening to')

        
    def run(self):
        while True:
            online = False
            command = self.socket.recv(BUFFER).decode()
            if command != '':
                
                
                if "send" in command:
                    content = command.partition(" ")
                    contentinner = content[2].partition(" ") 
                    sendmsg = self.user_name + ": " + contentinner[2] 
                    receiver = contentinner[0]
                    print(self.user_name + " is trying to send a msg to " + receiver + ".\n")
                    
                    for z in userfdmap:
                        zi = z.partition(" ")
                        if receiver == zi[0]:
                            receiverfd = int(zi[2])
                            online = True
                            lock.acquire()
                            clientMessages[receiverfd].put(sendmsg)
                            lock.release()
                        else:
                            print("not found")
                    if online == False:   
                        msg = 'SERVER: User ' + receiver + ' not online, appending to file'
                        clientMessages[self.socket.fileno()].put(msg)                        
                        localtime = time.asctime(time.localtime(time.time()))
                        sendmsg = localtime + '->' + sendmsg
                        filename = receiver + '.txt'
                        file = open(filename, "a+")
                        file.write(sendmsg)
                        file.write('\n')
                        file.close()
                
                
                
                elif 'group()' in command:
                    sub_command = command.partition(" ")
                    group_command = sub_command[2].partition(" ")
                    if group_command[0] == "create":
                        group_name = group_command[2]
                        group_users = [self.user_name]
                        sendmsg = "New group " + group_name + " created by " + self.user_name
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
                                sendmsg = "User " + group_name[2] + " has been added to " + group_name[0] + " has asked. "
                                clientMessages[self.socket.fileno()].put(sendmsg)
                                for z in userfdmap:
                                    zi = z.partition(" ")
                                    if zi[0] == group_name[2]:
                                        sendmsg = "You been added to " + group_name[0] + " by " + self.user_name
                                        clientMessages[int(zi[2])].put(sendmsg)
                        
                            else:
                                sendmsg = "You are not a member of " + group_name[0] + ", you must be a member to add users"
                                clientMessages[self.socket.fileno()].put(sendmsg)
                                
                        else: 
                            sendmsg = group_name[0] + " does not exit."
                            clientMessages[self.socket.fileno()].put(sendmsg)
                    
                    
                    elif group_command[0] == "remove":
                        group_name = group_command[2].partition(" ")
                        if group_name[0] in groups: 
                            if self.user_name == groupchats[group_name[0]][0]:
                                groupLock.acquire()
                                if group_name[2] in groupchats[group_name[0]]:
                                    groupchats[group_name[0]].remove(group_name[2])
                                    sendmsg = "Removed " + group_name[2] + " from " + group_name[0] + " sucessfully."
                                    clientMessages[self.socket.fileno()].put(sendmsg)
                                    break
                                else:
                                    sendmsg = "User " + group_name[2] + " is not in group " + group_name[0]
                                    clientMessages[self.socket.fileno()].put(sendmsg)
                            else:
                                sendmsg = "You must be the creator of the group, and guess what, you are not."
                                clientMessages[self.socket.fileno()].put(sendmsg)
                        else:
                            sendmsg = "Group " + group_name[0] + " does not exist."
                            clientMessages[self.socket.fileno()].put(sendmsg)
                            
                            
                    elif group_command[0] in groups: # se group grupo_nome msg, envia para lista de user de grupo_nome, para tal procurar fd de z de lista de users 
                        message_sent = False
                        sendmsg = group_command[0] + "- " + self.user_name + ": " + group_command[2]                          
                        for p in groupchats[group_command[0]]:
                            for z in userfdmap:
                                zi = z.partition(" ")
                                if zi[0] == p:
                                    clientMessages[int(zi[2])].put(sendmsg)
                                    message_sent = True
                            if not message_sent:                      
                                localtime = time.asctime(time.localtime(time.time()))
                                sendmsg = localtime + '->' + sendmsg
                                filename = p + '.txt'
                                file = open(filename, "a+")
                                file.write(sendmsg)
                                file.write('\n')
                                file.close()
                                
                                
                elif 'inbox()' == command:
                    sendmsg = ""
                    filename = self.user_name + '.txt'
                    file = open(filename, "r")
                    file_head = file.read(1)
                    if not file_head:
                        sendmsg = "No msg sent while offline"
                    else:
                        file.seek(0)
                        for msg in file:
                            sendmsg=sendmsg + "\n" + msg
                    clientMessages[self.socket.fileno()].put(sendmsg)
                    
                elif 'whoon()' == command:
                    print(self.user_name + ' is trying to know who is on.\n')                    
                    sendstr = ''
                    for z in userfdmap:
                        zi = z.partition(" ")
                        sendstr = sendstr + ' ' + str(zi[0])
                    lock.acquire()
                    clientMessages[self.socket.fileno()].put(sendstr)
                    print("WHOON: Mensagem na queue.\n")
                    lock.release()
                
                elif 'help()' == command:
                    sendmsg = "\n\nSEND COMMANDS:\nsend user_name msg\n\nWHOON:\nwhoon()\n\nQUIT:\nquit()\n\nGROUPCHAT COMMANDS:\ngroup() create groupname\ngroup() add groupname username\ngroup() groupname msg\n"
                    clientMessages[self.socket.fileno()].put(sendmsg)
                    
                elif 'quit()' == command:
                    print('\n Client ' + self.user_name + 'has left the chat.\n') 
                    lock.acquire()                   
                    del clientMessages[self.socket.fileno()]
                    lock.release()
                    self.socket.close()
              
                
       
class ClientSendThread(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.socket = socket
        print('Sending to')

    def run(self):
        tcpsock2.listen(1)
        (conn2,addr) = tcpsock2.accept()
        print("Connected", conn2.fileno(), self.socket.fileno())
        
        while True:
            try: 
                if not clientMessages[self.socket.fileno()].empty():
                    lock.acquire()
                    message = clientMessages.get(self.socket.fileno()).get(False)
                    lock.release()
                    print(message)
                    print('havia mensagem\n')
                    print("Sending message to ", self.socket.fileno())
                    conn2.send(message.encode())
                    
            except queue.Empty:
                chat = "none"
                time.sleep(2)
                
            except KeyError: 
                pass


global command
command = ""
exitLock = threading.Lock()
lock = threading.Lock()
groupLock = threading.Lock()


groupchats = {}
groups = []
userfdmap = []
clientMessages = {}
BUFFER = 1024
threads=[]

tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
tcpsock.bind((HOST, PORT))
tcpsock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpsock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
tcpsock2.bind(('', PORT2))

while True:
    tcpsock.listen(10)
    print ("Server waiting 4 connections\n")
    (conn, (ip,port)) = tcpsock.accept()
    
    login = True
    user_name = ''
    fd = conn.fileno()
    q = queue.Queue()



    print('SERVER: Welcome ',conn.fileno())      
    user_name = conn.recv(BUFFER).decode()
    if user_name != '':
        lock.acquire()
        userinfo = user_name + ' ' + str(fd)
        userfdmap.append(userinfo)
        clientMessages[fd] = q
        msg = 'Welcome to the server ' + user_name
        clientMessages[fd].put(msg)   
        login = True
        lock.release()

    ReadingThread = ClientReadThread(conn, HOST, PORT, user_name)
    ReadingThread.daemon = True
    SendingThread = ClientSendThread(conn)
    SendingThread.daemon = True            
  
    SendingThread.start()
    ReadingThread.start()
    threads.append(ReadingThread)
    threads.append(SendingThread)
    
    