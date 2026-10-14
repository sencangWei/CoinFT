#pragma once
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <deque>
#include <vector>
#include <algorithm>
using byte = uint8_t;
inline uint32_t now_ms=0, now_us=0, irq_mask=0;
inline std::vector<unsigned> delays;
inline uint32_t millis(){return now_ms;}
inline uint32_t micros(){return now_us+=250;}
inline void delay(unsigned n){delays.push_back(n);now_ms+=n;}
inline uint32_t __get_PRIMASK(){return irq_mask;}
inline void __disable_irq(){irq_mask=1;}
inline void __set_PRIMASK(uint32_t n){irq_mask=n;}
struct Port {
 bool open=true, fail_write=false; int capacity=1024; unsigned baud=0;
 size_t read_limit=1024, write_limit=1024;
 std::deque<uint8_t> input; std::vector<uint8_t> output;
 void begin(unsigned n){baud=n;}
 explicit operator bool()const{return open;}
 int available(){return static_cast<int>(input.size());}
 int availableForWrite(){return capacity;}
 int read(){if(input.empty())return -1;int n=input.front();input.pop_front();return n;}
 size_t readBytes(uint8_t* p,size_t n){n=std::min({n,input.size(),read_limit});for(size_t i=0;i<n;i++)p[i]=static_cast<uint8_t>(read());return n;}
 size_t readBytes(char* p,size_t n){return readBytes(reinterpret_cast<uint8_t*>(p),n);}
 size_t write(uint8_t n){return write(&n,1);}
 size_t write(const uint8_t* p,size_t n){if(fail_write)return size_t(-1);n=std::min(n,write_limit);output.insert(output.end(),p,p+n);return n;}
 size_t write(const char* p,size_t n){return write(reinterpret_cast<const uint8_t*>(p),n);}
};
inline Port Serial, Serial2, Serial3, SerialUSB1;
struct IntervalTimer {void(*callback)()=nullptr; unsigned interval=0,ends=0; bool begin(void(*f)(),unsigned n){callback=f;interval=n;return true;}void end(){callback=nullptr;++ends;}};
