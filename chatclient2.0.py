import socket
import select 
import threading


    
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
                exitLock.acquire()
                exit_control = True
                exitLock.release()
                exit(1)
    
    
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
        while True:
            try:
                if not exit_control:
                    message = s2.recv(BUFFER).decode()
                    if message:
                        print(message)
                else:
                    threading._shutdown()
            except socket.timout as err:
                print ("\nERROR: receive timed out 3 second limit \n")



exit_control = False
exitLock = threading.Lock()
threads = []
serverHost = "127.0.0.1"
serverPort = 9000
serverPort2 = 8000
BUFFER = 1024

online = False


try:
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as err:
    print ("ERROR: Cannot create client side socket:")
    exit(1)
    
clientSocket.connect((serverHost,serverPort))
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
        print('CLIENT: I guess ur logged.\nLogged as ' +user_name + '.\n')
    ReadingThread.start()
    SendingThread.start()
    while True:
        for t in threads:
            t.join(2)
            if not t.isAlive():
                break
            
            
except socket.error as err:
    print ("ERROR: Cannot connect to chat server", err)
    print ("* Exiting... Goodbye! *")
    exit(1)

except KeyboardInterrupt:
    print ("\nINFO: KeyboardInterrupt")
    print ("* Closing all sockets and exiting chat server... Goodbye! *")
    clientSocket.close()
    exit()
