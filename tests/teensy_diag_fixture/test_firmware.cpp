#include "Arduino.h"
#include <string>
#include <sstream>
#include <iostream>
#include <stdexcept>
#include "../../firmware/teensy/teensy_coinft_serial_interface.cpp"
void check(bool v,const char* msg){if(!v)throw std::runtime_error(msg);}
std::vector<uint32_t> report(){std::string s(SerialUSB1.output.begin(),SerialUSB1.output.end());check(s.rfind("CFD1,",0)==0,"expected CFD1 heartbeat on diagnostic port");check(s.back()=='\n',"newline missing");std::stringstream stream(s.substr(5));std::string word;std::vector<uint32_t> values;while(std::getline(stream,word,','))values.push_back(static_cast<uint32_t>(std::stoull(word)));check(values.size()==13,"CSV field count");return values;}
void packet(){Serial2.input.push_back(2);for(int n=0;n<24;n++)Serial2.input.push_back(n+10);Serial2.input.push_back(3);}
int main(int argc,char** argv){try{
 std::string mode=argc>1?argv[1]:"heartbeat";
 if(mode=="legacy"||mode=="protocol"){
 setup();check(Serial2.baud==1000000&&Serial.baud==115200,"baud changed");
 const uint8_t expected[12][3]={{12,50,50},{12,30,72},{12,30,81},{12,30,82},{12,30,83},{12,30,85},{12,30,76},{12,30,75},{12,100,17},{12,100,26},{12,80,58},{12,80,42}};
 std::vector<uint8_t> bytes={'i'};for(int n=0;n<12;n++){bytes.push_back('t');bytes.push_back(n);bytes.insert(bytes.end(),expected[n],expected[n]+3);}check(Serial2.output==bytes,"setup tuning changed");check(delays.size()==14&&delays[0]==500&&std::all_of(delays.begin()+1,delays.end(),[](unsigned n){return n==50;}),"setup delays changed");
 Serial2.output.clear();Serial.input={'s'};loop();check(myTimer.interval==1000&&myTimer.callback==transmitData,"start timer");packet();loop();transmitData();std::vector<uint8_t> raw={0,0};for(int n=0;n<24;n++)raw.push_back(n+10);check(Serial.output==raw,"26-byte raw packet changed");check(Serial2.input.empty(),"UART packet not consumed");
 Serial.input={'t',4,12,30,81};loop();Serial.input={'i'};loop();check(Serial2.output==std::vector<uint8_t>({'s','t',4,12,30,81,'i'}),"command forwarding changed");check(myTimer.ends==1&&!newData1,"stop flags/timer");
#ifndef USB_DUAL_SERIAL
 check(SerialUSB1.output.empty(),"legacy diagnostic output");
#else
 SerialUSB1.output.clear();now_ms+=500;loop();auto v=report();check(v[3]==26&&v[4]==1&&v[5]==24&&v[6]==1&&v[7]==0&&v[8]==1&&v[9]==1&&v[10]==26&&v[11]==1&&v[12]==1,"packet/command counters");
#endif
 }else if(mode=="heartbeat"){
 now_ms=499;loop();check(SerialUSB1.output.empty(),"early heartbeat");now_ms=500;loop();auto v=report();check(v[0]==1&&v[1]==500&&v[2]==2,"initial heartbeat fields");check(Serial.output.empty(),"diagnostics leaked to raw");SerialUSB1.output.clear();now_ms=999;loop();check(SerialUSB1.output.empty(),"periodic early heartbeat");now_ms=1000;loop();check(report()[0]==2,"periodic heartbeat");
 }else if(mode=="skip"){
 SerialUSB1.open=false;now_ms=500;loop();check(SerialUSB1.output.empty(),"closed port output");SerialUSB1.open=true;SerialUSB1.capacity=1;now_ms=1000;loop();check(SerialUSB1.output.empty(),"full port output");SerialUSB1.capacity=1024;now_ms=1500;loop();check(report()[0]==3,"skipped sequence gaps");
 }else if(mode=="short"){
 packet();Serial2.read_limit=23;loop();Serial.write_limit=2;transmitData();now_ms=500;loop();auto v=report();check(v[3]==26&&v[4]==1&&v[5]==23&&v[6]==1&&v[10]==4,"actual return accounting");
 }else if(mode=="failure"){
 packet();loop();Serial.fail_write=true;transmitData();now_ms=500;loop();check(report()[10]==0,"failed SIZE_MAX USB writes counted as accepted bytes");
 }else if(mode=="timeout"){
 Serial2.input.assign(26,99);Serial2.input.front()=2;loop();now_ms=500;loop();auto v=report();check(v[3]==26&&v[5]==24&&v[6]==0&&v[7]==1,"timeout accounting");SerialUSB1.output.clear();Serial2.input.assign(26,55);loop();now_ms=1000;loop();check(report()[3]==27,"garbage header accounting");
 }else if(mode=="irq_wrap"){
  irq_mask=1;now_ms=0xffffff00U;loop();check(irq_mask==1,"masked interrupt state lost");auto v=report();check(v[1]==0xffffff00U,"absolute uptime wrap representation");SerialUSB1.output.clear();now_ms=244;loop();check(report()[0]==2&&irq_mask==1,"elapsed rollover or IRQ restore");
 }else if(mode=="counter_wrap"){
#ifdef USB_DUAL_SERIAL
 diagLoopCount=diagUartBytes=diagDataReads=diagPayloadBytes=diagEndMarkers=diagEndTimeouts=diagStarts=diagStops=UINT32_MAX;
 diagTimerTicks=diagUsbAttempts=diagUsbAccepted=UINT32_MAX;
 diagSequence=UINT32_MAX-1;diagLastReport=UINT32_MAX-500;now_ms=UINT32_MAX;
 // Make loop_count wrap to max during the real loop rather than wrap to zero.
 diagLoopCount=UINT32_MAX-1;loop();auto v=report();check(std::all_of(v.begin(),v.end(),[](uint32_t n){return n==UINT32_MAX;}),"maximum absolute counter CSV");check(SerialUSB1.output.size()==148,"maximum CSV bound");check(irq_mask==0,"unmasked interrupt state lost");
 SerialUSB1.output.clear();now_ms=499;loop();v=report();check(v[0]==0&&v[2]==0,"counter wrap representation");
#endif
 }else throw std::runtime_error("unknown scenario");
 std::cout<<"PASS "<<mode<<'\n';return 0;
 }catch(const std::exception& e){std::cerr<<"ASSERTION: "<<e.what()<<'\n';return 1;}}
