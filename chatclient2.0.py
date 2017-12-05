import socket
import select 
import threading
import os


exitLock = threading.Lock()
exit_control = False
threads = []
serverHost = "127.0.0.1"
serverPort = 9000
serverPort2 = 8000
BUFFER = 1024
online = False
    
class ClientSender(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.socket = socket 
        print("New Sender Thread")
    
    def run(self):
        while True:
            print("COMMAND:")
            sendcommand = input()
            self.socket.send(sendcommand.encode())
            if (sendcommand == "quit()"):
                quit()
                os._exit(1)
            
    
    
class ClientListener(threading.Thread):
    def __init__(self, socket):
        threading.Thread.__init__(self)
        self.socket = socket
        print("New Listening Thread")
     
    def run(self):
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.connect((serverHost, serverPort2))
        welcomemsg = s2.recv(BUFFER)
        print(welcomemsg)
        while not exit_control:
            try:
                message = s2.recv(BUFFER).decode()
                if message:
                    print(message)
                
            except socket.error as err:
                print ("\nCannot receive from socket\nBroken Socket\n")
        os._exit(1)

def quit():
    exitLock.acquire()
    exit_control = True
    exitLock.release()
    clientSocket.close()   


try:
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as err:
    print ("ERROR: Cannot create client side socket:")
    exit(1)
try:   
    clientSocket.connect((serverHost,serverPort))
except socket.error as err:
    print ("ERROR: Cannot connect to chat server", err)
    print ("Server not online!\n * Exiting... Goodbye!*")
    exit(1)
    
ReadingThread = ClientListener(clientSocket)
ReadingThread.daemon = True
SendingThread = ClientSender(clientSocket)
SendingThread.daemon = True
threads.append(ReadingThread)
threads.append(SendingThread)
                
try:
    if online == False:
        print('CLIENT: Enter your username:')
        user_name = input()
        clientSocket.send(user_name.encode())
        online = True
        print('CLIENT: I guess ur logged.\nLogged as ' + user_name + '.\n')
    ReadingThread.start()
    SendingThread.start()
    while True:
        if exit_control:
            exit(1)
            
except KeyboardInterrupt:
    print ("\nINFO: KeyboardInterrupt")
    print ("* Closing all sockets and exiting chat server... Goodbye! *")
    exitLock.acquire()
    exit_control = True
    exitLock.release()
    threads[0].join()
    threads[1].join()
    clientSocket.close()
    exit(0)
