#include "waifu2x.h"
#include "realcugan.h"
#include <vector>
#include <iostream>
#include <cmath>

int main(){
 for(auto dims : {std::pair<int,int>{1,1},{17,19},{131,67}})for(int engine=0;engine<2;engine++)for(int scale=1;scale<=4;scale++)for(int noise=1;noise<=3;noise++){
 if(engine==0&&scale>2)continue;if(engine==1&&(scale==1||(scale>2&&noise<3)))continue;
 int w=dims.first,h=dims.second;std::vector<unsigned char> in(w*h*3),out(w*h*3*scale*scale,0);
 for(int i=0;i<w*h;i++){in[i*3]=96;in[i*3+1]=144;in[i*3+2]=192;}
 ncnn::Mat a(w,h,(void*)in.data(),(size_t)3,3),b(w*scale,h*scale,(void*)out.data(),(size_t)3,3);
 std::string dir=ASSETS_DIR;int ret;
 if(!engine){Waifu2x net(-1,false,2);net.noise=noise;net.scale=scale;net.tilesize=16;net.prepadding=scale==1?28:18;std::string stem=dir+"models-cunet/noise"+std::to_string(noise)+(scale==1?"_model":"_scale2.0x_model");net.load(stem+".param",stem+".bin");ret=net.process(a,b);}
 else{RealCUGAN net(-1,false,2);net.noise=noise;net.scale=scale;net.tilesize=16;net.prepadding=scale==2?18:scale==3?14:19;net.syncgap=1;std::string stem=dir+"models-se/up"+std::to_string(scale)+"x-denoise"+std::to_string(noise)+"x";net.load(stem+".param",stem+".bin");ret=net.process(a,b);}
 int changed=0;double sum=0;for(int i=0;i<w*h*scale*scale;i++){sum+=out[i*3];if(out[i*3])changed++;}
 if(ret||!changed||sum/(w*h*scale*scale)<50){std::cerr<<"output failure";return 3;}
 std::cout<<"PASS engine="<<engine<<" size="<<w<<"x"<<h<<" scale="<<scale<<" noise="<<noise<<" mean="<<sum/(w*h*scale*scale)<<std::endl;
 }
}
