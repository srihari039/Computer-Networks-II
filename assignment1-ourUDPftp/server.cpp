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
#include <mutex>
#include <queue>
#include <set>
#include <filesystem>
using namespace std;

// setting a standard buffer size
#define bufferSize 8192
string file_to_recieve = "received_file";
ofstream outfile(file_to_recieve,ios::out|ios::binary);
mutex locker;

// class for calculating time
class Timer{
private:
    double duration;
    std::chrono::time_point<std::chrono::high_resolution_clock> startTime,stopTime;
    string message;
public:
    Timer(string msg_){
	message = msg_;
        startTime = std::chrono::high_resolution_clock::now();
    }
    double getTimeDuration(){
        return duration;
    }
    void stop(){
        stopTime = std::chrono::high_resolution_clock::now();
        auto start = std::chrono::time_point_cast<std::chrono::microseconds>(startTime).time_since_epoch().count();
        auto stop = std::chrono::time_point_cast<std::chrono::microseconds>(stopTime).time_since_epoch().count();
        duration = stop-start;
	duration *= 1e-6;
        cout<<"Time taken for "<<message<<" : "<<duration<<" s"<<endl;
    }
    ~Timer(){

    }
};

// packet class, handy while keeping track of packets
class packet{
public:
    int packet_no;
    int chunk_size;
    char buffer[bufferSize];
};

// function which gives file size when given file name
int getFileSize(string file_name){
    std::filesystem::path file{file_name};
    return std::filesystem::file_size(file);
}

// class for receiving using UDP
class udpFTPreceiver{
    struct sockaddr_in server_address,client_address;
    int socket_fd;
    int port_number;
    socklen_t client_length = sizeof(sockaddr_in);
    int file_size;
    int no_of_packets_expected;
    int n;
    double time_taken;
    void createSocket();
    void setSocket(int argc,char* argv[]);
    void bindSocket();
    template<class T> void send_(T&);
    template<class T> void recv_(T&);
    void receiveFileSize();
    void sendMissingPacketNos();
    void handleMissingPackets();
    void receive_packets();
    vector<packet> packets;
    vector<bool> received_packets;
    int count_rec_packets;
public:
    // constructor
    udpFTPreceiver(int argc,char* argv[]){
        bzero(&server_address,sizeof(server_address));
        bzero(&client_address,sizeof(client_address));
        createSocket();
        setSocket(argc,argv);
        bindSocket();
        count_rec_packets = 0;
    }
    // function which receives the file from sender
    void receiveFile();
    void calculateThroughput();
};

// create socket
void udpFTPreceiver::createSocket(){
    socket_fd = socket(AF_INET,SOCK_DGRAM,0);
    if(socket_fd < 0){
        cerr<<"[Error] Socket creation failed"<<endl;
        cout<<"[Aborting..] Program terminated"<<endl;
        exit(1);
    }
    return;
};

// set socket
void udpFTPreceiver::setSocket(int argc,char* argv[]){
    if(argc == 2){
        port_number = stoi(argv[1]);
        bzero(&server_address,sizeof(server_address));
        server_address.sin_family = AF_INET;
        server_address.sin_addr.s_addr = INADDR_ANY;
        server_address.sin_port = htons(port_number);
        cout<<"[Log] Socket created successfully"<<endl;
    } else {
        cerr<<"[Error] Invalid arguments"<<endl;
        cout<<"Usage : <Exec> port_no"<<endl;
        exit(1);
    }
    return;
}

// bind the socket 
void udpFTPreceiver::bindSocket(){
    bool bind_err = bind(socket_fd,(const sockaddr*)&server_address,sizeof(server_address)) < 0;
    if(bind_err){
        cerr<<"[Error] Binding failed!"<<endl;
        exit(1);
    }
    cout<<"[Log] Binded socket successfully"<<endl;
    return;    
}

// first receive the file size from sender
void udpFTPreceiver::receiveFileSize(){
    recv_(file_size);
    no_of_packets_expected = ceil((double)file_size/(bufferSize-1));
    packets.resize(no_of_packets_expected+1);
    received_packets.resize(no_of_packets_expected+1);
  //  cout<<"[Log] "<<no_of_packets_expected<<" packet/packets are expected"<<endl;
    return;
}

// custom functions for sending/receiving packets 
// takes in any variable and send/receive it as a packet
template<class T> void udpFTPreceiver::send_(T &pkt){
    // usleep(2);
    n = sendto(socket_fd,&pkt,sizeof(pkt),0,(sockaddr*)&server_address,sizeof(server_address));
    if(n < 0){
        cerr<<"[Error] sending packet failed in [sendto]"<<endl;
    }
    return;
}
template<class T> void udpFTPreceiver::recv_(T &pkt){
    n = recvfrom(socket_fd,&pkt,sizeof(pkt),0,(sockaddr*)&server_address,&client_length);
    if(n < 0){
        cerr<<"[Error] receiving packet failed in [recvfrom]"<<endl;
    }
    return;
}

// function which acknowledges the packets
void udpFTPreceiver::sendMissingPacketNos(){
    for(int i = 1 ; i <= no_of_packets_expected ; i++){
//        if(not received_packets[i]){
	        pair<int,bool> acks;
            acks.first = i;
            acks.second = received_packets[i];
            send_(acks);
//	    }
    	usleep(10);
    }
    return;
}

// function which handles the missing packets
void udpFTPreceiver::handleMissingPackets(){
    // usleep(5);
   // Timer* recv_timer = new Timer("Receiving all packets");
    while(count_rec_packets < no_of_packets_expected){
        // usleep(100000);
        thread sendPacketNos = std::thread(&udpFTPreceiver::sendMissingPacketNos,this);
        sendPacketNos.join();
    }
   // recv_timer->stop();
   // delete recv_timer;
    //sendMissingPacketNos();
   // Timer* writer = new Timer("Writing to file");
    for(int i = 1 ; i <= no_of_packets_expected ; i++){
        outfile.write(packets[i].buffer,packets[i].chunk_size);
    }
   // writer->stop();
   // delete writer;
}

// function which receives the packets from the sender
void udpFTPreceiver::receive_packets(){
    while(count_rec_packets < no_of_packets_expected){
        packet pkt;
        memset((void*)&pkt,0,sizeof(pkt));
        if(count_rec_packets < no_of_packets_expected)
        recv_(pkt);
        if(received_packets[pkt.packet_no] == false){
            if(pkt.packet_no != 0){
        	cout<<"Received packet - "<<pkt.packet_no<<" packet-count : "<<count_rec_packets+1<<endl;
		received_packets[pkt.packet_no] = true;
                count_rec_packets++;
                packets[pkt.packet_no] = pkt;
            }
        }
    }
    return;
}

// function which receives the file
void udpFTPreceiver::receiveFile(){
    receiveFileSize();
    Timer* timer = new Timer("entire file transfer");
    thread handler = std::thread(&udpFTPreceiver::handleMissingPackets,this);
    thread receiver = std::thread(&udpFTPreceiver::receive_packets,this);
    receiver.join();
    handler.join();
    timer->stop();
    time_taken = timer->getTimeDuration();
    delete timer;
    cout<<"Entire file recieved with name 'received_file'"<<endl;
    int status = -1;
    n = sendto(socket_fd,&status,sizeof(status),0,(sockaddr*)&server_address,sizeof(server_address));
    return;
}

// function which calculates the throughput
void udpFTPreceiver::calculateThroughput(){
    cout<<"No of packets recieved - "<<count_rec_packets<<endl;
    double seconds = (double)time_taken;
    double throughput = (double)100/seconds;
    cout<<"Throughput - "<<throughput<<"MBps"<<" - "<<throughput*1024<<"kBps"<<endl;
}

// main function
int main(int argc, char* argv[]){
    udpFTPreceiver* receiver = new udpFTPreceiver(argc,argv);
    receiver->receiveFile();
    receiver->calculateThroughput();

    int size_of_file = getFileSize(file_to_recieve);
    cout<<"Size of "<<file_to_recieve<<" : "<<size_of_file<<endl;
    return 0;
}
