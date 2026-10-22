#include <jni.h>
#include <android/bitmap.h>
#include <vector>
#include <string>
#include <stdexcept>
#include <cstring>
#include <algorithm>
#include "waifu2x.h"
#include "realcugan.h"
extern "C" JNIEXPORT void JNICALL Java_cn_qingying_denoiser_MainActivity_nativeProcess(JNIEnv* env,jobject,jobject source,jobject dest,jstring root,jint engine,jint strength,jint scale) {
 try {
  AndroidBitmapInfo a,b;
  if(AndroidBitmap_getInfo(env,source,&a)||AndroidBitmap_getInfo(env,dest,&b)||a.format!=ANDROID_BITMAP_FORMAT_RGBA_8888||b.format!=ANDROID_BITMAP_FORMAT_RGBA_8888) throw std::runtime_error("图片格式不支持");
  std::vector<unsigned char> rgba(a.width*a.height*4), input(a.width*a.height*3), output(b.width*b.height*3);
  void* ptr;
  if(AndroidBitmap_lockPixels(env,source,&ptr)) throw std::runtime_error("无法读取图片");
  for(unsigned y=0;y<a.height;y++) memcpy(rgba.data()+y*a.width*4,(char*)ptr+y*a.stride,a.width*4);
  AndroidBitmap_unlockPixels(env,source);
  for(size_t i=0;i<a.width*a.height;i++){unsigned alpha=rgba[i*4+3];for(int c=0;c<3;c++)input[i*3+c]=alpha?std::min(255u,(rgba[i*4+c]*255u+alpha/2)/alpha):0;}
  ncnn::Mat in(a.width,a.height,(void*)input.data(),(size_t)3,3);
  ncnn::Mat out(b.width,b.height,(void*)output.data(),(size_t)3,3);
  const char* chars=env->GetStringUTFChars(root,0);std::string dir(chars);env->ReleaseStringUTFChars(root,chars);
  int code;
  if(engine==0){
   Waifu2x net(-1,false,2);net.noise=strength;net.scale=scale;net.tilesize=128;net.prepadding=scale==1?28:18;
   std::string stem=dir+"/models-cunet/noise"+std::to_string(strength)+(scale==1?"_model":"_scale2.0x_model");
   if(net.load(stem+".param",stem+".bin")) throw std::runtime_error("模型加载失败");
   code=net.process(in,out);
  } else {
   RealCUGAN net(-1,false,2);net.noise=strength;net.scale=scale;net.tilesize=128;net.prepadding=scale==2?18:scale==3?14:19;net.syncgap=1;
   std::string stem=dir+"/models-se/up"+std::to_string(scale)+"x-denoise"+std::to_string(strength)+"x";
   if(net.load(stem+".param",stem+".bin")) throw std::runtime_error("模型加载失败");
   code=net.process(in,out);
  }
  if(code) throw std::runtime_error("AI 处理失败");
  
  if(AndroidBitmap_lockPixels(env,dest,&ptr)) throw std::runtime_error("无法写入图片");
  for(unsigned y=0;y<b.height;y++)for(unsigned x=0;x<b.width;x++){
   // Preserve transparency separately; the upstream CUGAN RGBA tile path copies padded alpha.
   float sx=std::max(0.f,std::min(float(a.width-1),(x+.5f)*a.width/b.width-.5f));
   float sy=std::max(0.f,std::min(float(a.height-1),(y+.5f)*a.height/b.height-.5f));
   int x0=int(sx),y0=int(sy),x1=std::min(x0+1,int(a.width-1)),y1=std::min(y0+1,int(a.height-1));
   float dx=sx-x0,dy=sy-y0;
   unsigned alpha=(1-dy)*((1-dx)*rgba[(y0*a.width+x0)*4+3]+dx*rgba[(y0*a.width+x1)*4+3])+dy*((1-dx)*rgba[(y1*a.width+x0)*4+3]+dx*rgba[(y1*a.width+x1)*4+3])+.5f;
   auto pixel=(unsigned char*)ptr+y*b.stride+x*4;pixel[3]=alpha;
   for(int c=0;c<3;c++)pixel[c]=(output[(y*b.width+x)*3+c]*alpha+127)/255;
  }
  AndroidBitmap_unlockPixels(env,dest);
 }catch(const std::exception& e){env->ThrowNew(env->FindClass("java/lang/RuntimeException"),e.what());}
}
