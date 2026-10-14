#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#define TX_NUM 4
#define TX_SIZE 2048
#define TX_TIMEOUT_MSEC 120
#define CDC2_TX_ENDPOINT 5
struct transfer_t {uint32_t status=0;};
transfer_t tx_transfer[TX_NUM];
uint8_t txbuffer[TX_NUM*TX_SIZE],tx_head=0,tx_noautoflush=0,usb_configuration=1,transmit_previous_timeout=0;
static void usb_serial2_flush_callback(void);
bool timer_armed=false,inject_read_expiry=false,inject_start_expiry=false,in_callback=false;
unsigned expiries=0;
void expire_timer(){if(!timer_armed)return;timer_armed=false;++expiries;in_callback=true;usb_serial2_flush_callback();in_callback=false;}
struct Available {
 uint16_t value=0;
 operator uint16_t()const{if(inject_read_expiry&&tx_noautoflush&&!in_callback){inject_read_expiry=false;expire_timer();}return value;}
 Available& operator=(uint16_t n){value=n;return *this;}
} tx_available;
uint32_t systick_millis_count=0;
unsigned yields=0,prints=0,status_reads=0,starts=0,stops=0,submissions=0,prepares=0,caches=0;
bool protected_access=true;
void* prepared_buffer=nullptr;uint32_t prepared_size=0;std::vector<uint8_t> submitted_bytes;
uint32_t usb_transfer_status(transfer_t* p){++status_reads;return p->status;}
void yield(){++yields;++systick_millis_count;}
int fake_printf(const char*,...){++prints;return 0;}
void timer_start_oneshot(){++starts;timer_armed=true;if(inject_start_expiry){inject_start_expiry=false;expire_timer();}}
void timer_stop(){++stops;timer_armed=false;protected_access&=tx_noautoflush==1;}
void usb_prepare_transfer(transfer_t*,void* buffer,uint32_t size,uint32_t){++prepares;prepared_buffer=buffer;prepared_size=size;protected_access&=in_callback||tx_noautoflush==1;}
void arm_dcache_flush_delete(void*,uint32_t){++caches;protected_access&=in_callback||tx_noautoflush==1;}
void usb_transmit(int,transfer_t* p){++submissions;p->status=0x80;auto* bytes=static_cast<uint8_t*>(prepared_buffer);submitted_bytes.assign(bytes,bytes+prepared_size);protected_access&=in_callback||tx_noautoflush==1;}
#define printf fake_printf
#include "usb_functions.inc"
#undef printf
void check(bool condition,const char* message){if(!condition)throw std::runtime_error(message);}
int main(int argc,char** argv){try{
 const std::string mode=argc>1?argv[1]:"busy";
 uint8_t data[148];for(unsigned n=0;n<sizeof(data);++n)data[n]=n;
 if(mode=="busy"){
 tx_transfer[0].status=0x80;
 int result=usb_serial2_write(data,sizeof(data));
 std::cerr<<"busy result="<<result<<" yields="<<yields<<" fake_elapsed_ms="<<systick_millis_count<<'\n';
 check(yields==0,"busy-head diagnostic write must not yield");check(result==0,"busy head must skip");check(usb_serial2_write_buffer_free()==0,"other free buffers must not count");check(tx_available==0&&tx_head==0,"busy skip changed state");
 tx_transfer[0].status=0;check(usb_serial2_write_buffer_free()==TX_SIZE,"ready capacity");check(usb_serial2_write(data,sizeof(data))==148,"busy-to-ready recovery");check(!std::memcmp(data,txbuffer,148),"recovery exact bytes");
 }else if(mode=="reject"){
 for(uint8_t prior=0;prior<2;++prior){
 tx_noautoflush=prior;usb_configuration=0;check(usb_serial2_write(data,148)==0&&usb_serial2_write_buffer_free()==0,"unconfigured skip");check(tx_noautoflush==prior,"unconfigured flag restore");usb_configuration=1;
 for(uint32_t status:{0x08U,0x20U,0x40U,0x80U}){tx_transfer[0].status=status;check(usb_serial2_write(data,148)==0&&usb_serial2_write_buffer_free()==0,"error/busy status skip");check(tx_available==0&&tx_noautoflush==prior,"error flag/state restore");}
 tx_transfer[0].status=0;tx_available=100;std::memset(txbuffer,0xa5,sizeof(txbuffer));check(usb_serial2_write(data,148)==0,"insufficient contiguous capacity must reject whole line");check(tx_available==100&&txbuffer[TX_SIZE-100]==0xa5&&tx_noautoflush==prior,"partial prefix or flag mutation");
 check(usb_serial2_write(nullptr,0)==0&&tx_available==100&&tx_noautoflush==prior,"empty write changed state");tx_available=0;}
 }else if(mode=="ready"){
 for(uint8_t prior=0;prior<2;++prior){tx_noautoflush=prior;check(usb_serial2_write(data,148)==148,"ready accepts exact size");check(tx_noautoflush==prior,"success flag restore");check(!std::memcmp(data,txbuffer+prior*148,148),"ready byte equality");}
 check(tx_available==TX_SIZE-296&&starts==2&&submissions==0,"partial timer semantics");check(usb_serial2_write_buffer_free()==TX_SIZE-296,"current contiguous free capacity");check(tx_noautoflush==1,"capacity prior flag restore");
 }else if(mode=="full"){
 tx_head=TX_NUM-1;tx_available=148;tx_noautoflush=1;check(usb_serial2_write(data,148)==148,"exact-full acceptance");check(tx_head==0&&tx_available==0,"full head wrap");check(submissions==1&&prepares==1&&caches==1&&stops==1&&starts==0,"full DMA/cache/timer semantics");check(!std::memcmp(data,txbuffer+sizeof(txbuffer)-148,148),"full exact bytes");check(tx_noautoflush==1,"full flag restore");
 }else if(mode=="expiry_success"||mode=="expiry_capacity"||mode=="expiry_reject"){
 if(mode=="expiry_success"){
 inject_start_expiry=true;check(usb_serial2_write(data,148)==148,"expiry successful write return");
 }else{
 tx_available=100;std::memset(txbuffer,0xa5,sizeof(txbuffer));timer_armed=true;inject_read_expiry=true;
 if(mode=="expiry_capacity")check(usb_serial2_write_buffer_free()==100,"expiry capacity return");
 else check(usb_serial2_write(data,148)==0,"expiry rejection return");
 }
 check(expiries==1,"one-shot expiry injection not executed");check(tx_noautoflush==0,"expiry protection not released");
 if(submissions==0){check(timer_armed,"suppressed expiry stranded partial buffer without timer retry");expire_timer();}
 check(submissions==1&&tx_available==0&&tx_head==1,"partial buffer did not submit without another append");
 if(mode=="expiry_success")check(submitted_bytes==std::vector<uint8_t>(data,data+148),"successful expiry submitted wrong bytes");
 else check(submitted_bytes==std::vector<uint8_t>(TX_SIZE-100,0xa5),"pending partial expiry submitted wrong bytes");
 }else throw std::runtime_error("unknown mode");
 check(yields==0&&prints==0,"adapted function waited/logged");check(protected_access,"buffer/timer operation without autoflush protection");std::cout<<"PASS "<<mode<<'\n';return 0;
 }catch(const std::exception& e){std::cerr<<"ASSERTION: "<<e.what()<<'\n';return 1;}}
