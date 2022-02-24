// including all the useful header files
#include <iostream>
#include <sys/socket.h>
#include <sys/stat.h>
#include <netinet/in.h>
#include <cstring>
#include <thread>
#include <unistd.h>
#include <vector>
#include <fstream>
#include <cmath>
#include <netdb.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <set>
#include <atomic>
#include <filesystem>
using namespace std;

// setting a standard buffer size
#define bufferSize 8192

// class for calculating time
class Timer{
private:
    int64_t duration;
    std::chrono::time_point<std::chrono::high_resolution_clock> startTime,stopTime;
public:
    Timer(){
        startTime = std::chrono::high_resolution_clock::now();
    }
    int64_t getTimeDuration(){
        return duration;
    }
    void stop(){
        stopTime = std::chrono::high_resolution_clock::now();
        auto start = std::chrono::time_point_cast<std::chrono::microseconds>(startTime).time_since_epoch().count();
        auto stop = std::chrono::time_point_cast<std::chrono::microseconds>(stopTime).time_since_epoch().count();
        duration = stop-start;
        cout<<"Time taken : "<<duration<<" μs"<<endl;
    }
    ~Timer(){

    }
};

// packet class, handy while storing data of packets
class packet{
public:
    int packet_no;
    int chunk_size;
    char buffer[bufferSize];
};

// utility function for getting packet info, given the packet number, gives the packet details
pair<int,int> getPacketInfo(int packet_no,int file_size){
    int start,chunksize;
    start = (packet_no-1)*(bufferSize-1);
    chunksize = bufferSize-1;
    if(start+chunksize < file_size){
        return {start,chunksize};
    } else {
        return {start,file_size-start};
    }
}

// function which gives file size when given file name
int getFileSize(string file_name){
    std::filesystem::path file{file_name};
    return std::filesystem::file_size(file);
}

// utility function to get the memory mapping of the file and file size
pair<char*,int> getFileDetails(string file_name){
    ifstream infile(file_name,std::ios::binary);
    int file_size = getFileSize(file_name);
    char* data = new char[file_size];
    infile.read(&data[0],file_size);
    return {data,file_size};
}

// class for sending using UDP
class udpFTPsender{
    struct sockaddr_in server_address;
    int socket_fd;
    struct hostent *host; 
    int port_no;
    string file_name;
    int file_size;
    int n;
    int no_of_actual_packets;
    set<int> sent;
    char* file_contents;
    atomic<int> packets_sent;
    socklen_t server_length = sizeof(sockaddr_in);

    void initSocket(char*,int);
    void loadFileDetails();
    template<class T> void send_(T&);
    template<class T> void recv_(T&);
    void sendFileSizetoServer();
    void handleMissingPackets();
    void sendFilePacketsSimultaneously();
public:
    // constructor
    udpFTPsender(int argc,char* argv[]){
        packets_sent = 0;
	    initSocket(argv[1],stoi(argv[2]));
        file_name = argv[3];
        loadFileDetails();
    }
    // function to send the file given in arguments
    void sendFile();
};

// init socket
void udpFTPsender::initSocket(char* hostname,int port_no){
    host = gethostbyname(hostname);
    if(host == nullptr){
    	cerr<<"[Error] Server/host is not available with given IP"<<endl;
	    cout<<"[Aborting..] Terminating program"<<endl;
	    exit(EXIT_FAILURE);
    }
    socket_fd = socket(AF_INET,SOCK_DGRAM,0);
    if(socket_fd < 0){
        cerr<<"[Error] Socket creation failed"<<endl;
	    cout<<"[Aborting..] Terminating program"<<endl;
	    exit(EXIT_FAILURE);
    }
    bzero((char*)&server_address,sizeof(server_address));
    bcopy((char*)host->h_addr,(char*)&server_address.sin_addr.s_addr,host->h_length);
    server_address.sin_family = AF_INET;
    server_address.sin_port = htons(port_no);
    
    cout<<"[Log] Socket set successfully"<<endl;
    return;
}

// get the file details from the file name
void udpFTPsender::loadFileDetails(){
    pair<char*,int> file_details = getFileDetails(file_name);
    file_contents = file_details.first;
    file_size = file_details.second;

    if(file_contents == NULL or file_size == -1){
        cout<<"[Error] Unable to load the file"<<endl;
        exit(1);            
    } else {
        cout<<"[Log] Size of "<<file_name<<" : "<<file_size<<endl;
        cout<<"Successfully loaded the data of "<<file_name<<endl;            
        no_of_actual_packets = ceil((double)file_size/(bufferSize-1));
    }
    return;
}

// custom functions for sending/receiving packets 
// takes in any variable and send/receive it as a packet
template<class T> void udpFTPsender::send_(T &pkt){
    n = sendto(socket_fd,&pkt,sizeof(pkt),0,(sockaddr*)&server_address,sizeof(server_address));
    usleep(600);
    if(n < 0){
        cerr<<"[Error] sending packet failed in [sendto]"<<endl;
    }
    return;
}
template<class T> void udpFTPsender::recv_(T &pkt){
    n = recvfrom(socket_fd,&pkt,sizeof(pkt),0,(sockaddr*)&server_address,&server_length);
    if(n < 0){
        cerr<<"[Error] receiving packet failed in [recvfrom]"<<endl;
    }
    return;
}

// function which sends the file size to receiver
void udpFTPsender::sendFileSizetoServer(){
    send_(file_size);
    return;
}

// function which handles the missing packets
void udpFTPsender::handleMissingPackets(){
    socklen_t server_length = sizeof(sockaddr_in);
    int start;
    int chunksize;

    // run until we get all packets acknowledged
    while(true){
        // init acks of a packet
        pair<int,int> acks;
        int missedpacketno;
        bool acknowledged;

        // receive the acknowledgements sent from the receiver
        recv_(acks);
        // n = recvfrom(socket_fd,&acks,sizeof(acks),0,(sockaddr*)&server_address,&server_length);
        missedpacketno = acks.first;
        acknowledged = acks.second;

        // -1 is set to the number which suggests that all the file packets were recieved at the other end
        if(missedpacketno == -1){
            break;
        }
        
        // if a packet is acknowledged, keep track of it
        if(acknowledged){
            if(sent.find(missedpacketno) == sent.end()){
                sent.insert(missedpacketno);
               // cout<<"Sent packet - "<<missedpacketno<<endl;
            }
        // else get the packet details and send it to receiver
        } else {
            // get packet details with packet number
            pair<int,int> packetInfo = getPacketInfo(missedpacketno,file_size);
            start = packetInfo.first;
            chunksize = packetInfo.second;

            // init packet and fill corresponding attributes
            packet pkt;
            memset((void*)&pkt,0,sizeof(pkt));
            pkt.packet_no = missedpacketno;
            pkt.chunk_size = chunksize;
            memcpy(pkt.buffer,&file_contents[start],chunksize);
            pkt.buffer[chunksize+1] = '\0';

            // send the packet
            send_(pkt);
            // update the number of packets sent
            packets_sent++;
        }
    }       
}

// function which sends the file once
void udpFTPsender::sendFilePacketsSimultaneously(){
    // initializing attributes
    int chunksize = 0;
    int packet_no = 1;
    int start = 0;

    // run the loop until once the file is sent
    while(packet_no <= no_of_actual_packets){
        // get the packet details with the packet number
        pair<int,int> packetInfo = getPacketInfo(packet_no,file_size);
        start = packetInfo.first;
        chunksize = packetInfo.second;

        // init a packet and reset any memory left in it.
        packet pkt;
        memset((void*)&pkt,0,sizeof(pkt));
        // fill it with the corresponding attributes
        pkt.packet_no = packet_no++;
        pkt.chunk_size = chunksize;
        memcpy(pkt.buffer,&file_contents[start],chunksize);
        pkt.buffer[chunksize+1] = '\0';

    // if(packet_no%10 == 0) usleep(100);
    // if(packet_no%5 == 0) usleep(50);
    // if(packet_no%15 == 0) usleep(80);
	// if(packet_no%25 == 0){
            // send the packet using send_ function
            send_(pkt);

            // increment the packet count which are sent
            packets_sent++;
	// }
    }
   // cout<<"Sent file once!"<<endl;
    return;
}

// function which sends the file
void udpFTPsender::sendFile(){
    // send filesize to receiver once
    sendFileSizetoServer();
    // create a thread which handles the missing packets simultaneously
    thread handler = std::thread(&udpFTPsender::handleMissingPackets,this);
    // simultaneously send the file once
    sendFilePacketsSimultaneously();
    // join when the child thread executes its part(sending all the missed packets)
    handler.join();
    // demap the mapped contents
    munmap(file_contents, file_size);

    // Observed practical values
    cout<<"Sent the entire file"<<endl;
    // cout<<"Packets sent in total - "<<packets_sent<<endl;
    cout<<"No of packets expected to be sent - "<<no_of_actual_packets<<endl;
    // cout<<"packet loss rate : "<<(double)100*(packets_sent-no_of_actual_packets)/packets_sent<<"%"<<endl;
    return;
}

// main function
int main(int argc,char* argv[]){
    // create a sender object of udpFTP type and send the arguments
    // so that it creates and sets socket up and running
    udpFTPsender* sender = new udpFTPsender(argc,argv);
    // send the file given in arguments
    sender->sendFile();
    // end of the program
    return 0;
}
