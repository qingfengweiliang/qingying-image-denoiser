#include <jni.h>
#include <android/bitmap.h>
#include <algorithm>
#include <cstring>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>
#include "waifu2x.h"
#include "realcugan.h"

namespace {
std::once_flag gpuInit;
int gpuIndex = -1;

int availableGpu()
{
    // ncnn loads Vulkan dynamically. Devices without a working driver stay on CPU.
    std::call_once(gpuInit, [] {
        try {
            if (ncnn::create_gpu_instance() == 0 && ncnn::get_gpu_count() > 0) {
                int index = ncnn::get_default_gpu_index();
                if (index >= 0 && ncnn::get_gpu_device(index)) gpuIndex = index;
            }
        } catch (const std::exception&) {
            gpuIndex = -1;
        }
    });
    return gpuIndex;
}

struct CallbackFailure {};

class ProgressCallback {
public:
    JNIEnv* env;
    jobject listener;
    jmethodID method = nullptr;
    ProgressCallback(JNIEnv* e, jobject l) : env(e), listener(l)
    {
        if (!l) return;
        jclass type = env->GetObjectClass(l);
        method = env->GetMethodID(type, "onProgress", "(IILjava/lang/String;)V");
        env->DeleteLocalRef(type);
        if (!method) throw CallbackFailure();
    }
    void report(int done, int total, const std::string& device)
    {
        if (!listener) return;
        jstring name = env->NewStringUTF(device.c_str());
        if (!name) throw CallbackFailure();
        env->CallVoidMethod(listener, method, done, total, name);
        env->DeleteLocalRef(name);
        if (env->ExceptionCheck()) throw CallbackFailure();
    }
};

class LockedPixels {
public:
    JNIEnv* env;
    jobject bitmap;
    void* data = nullptr;
    LockedPixels(JNIEnv* e, jobject b) : env(e), bitmap(b)
    {
        if (AndroidBitmap_lockPixels(env, bitmap, &data))
            throw std::runtime_error("无法访问图片像素");
    }
    ~LockedPixels() { AndroidBitmap_unlockPixels(env, bitmap); }
};

void infer(int device, int engine, int strength, int scale, const std::string& dir,
           const ncnn::Mat& in, ncnn::Mat& out, ProgressCallback& callback,
           const std::string& label)
{
    callback.report(0, 0, label + " · 加载模型");
    auto onProgress = [&](int done, int total) { callback.report(done, total, label); };
    if (engine == 0) {
        Waifu2x net(device, false, 2);
        net.noise = strength; net.scale = scale; net.tilesize = 128;
        net.prepadding = scale == 1 ? 28 : 18;
        net.progress.callback = onProgress;
        std::string stem = dir + "/models-cunet/noise" + std::to_string(strength)
            + (scale == 1 ? "_model" : "_scale2.0x_model");
        require_ncnn(net.load(stem + ".param", stem + ".bin"));
        require_ncnn(net.process(in, out));
    } else {
        RealCUGAN net(device, false, 2);
        net.noise = strength; net.scale = scale; net.tilesize = 128;
        net.prepadding = scale == 2 ? 18 : scale == 3 ? 14 : 19;
        net.syncgap = 1;
        net.progress.callback = onProgress;
        std::string stem = dir + "/models-se/up" + std::to_string(scale)
            + "x-denoise" + std::to_string(strength) + "x";
        require_ncnn(net.load(stem + ".param", stem + ".bin"));
        require_ncnn(net.process(in, out));
    }
}

void throwJava(JNIEnv* env, const char* message)
{
    if (env->ExceptionCheck()) return;
    jclass type = env->FindClass("java/lang/RuntimeException");
    env->ThrowNew(type, message);
    env->DeleteLocalRef(type);
}
}

extern "C" JNIEXPORT jstring JNICALL
Java_cn_qingying_denoiser_MainActivity_nativeGpuName(JNIEnv* env, jobject)
{
    try {
        int index = availableGpu();
        return env->NewStringUTF(index >= 0 ? ncnn::get_gpu_info(index).device_name() : "");
    } catch (const std::exception&) {
        return env->NewStringUTF("");
    }
}

extern "C" JNIEXPORT jstring JNICALL
Java_cn_qingying_denoiser_MainActivity_nativeProcess(JNIEnv* env, jobject,
    jobject source, jobject dest, jstring root, jint engine, jint strength,
    jint scale, jint backend, jobject listener)
{
    try {
        AndroidBitmapInfo a{}, b{};
        if (AndroidBitmap_getInfo(env, source, &a) || AndroidBitmap_getInfo(env, dest, &b)
            || a.format != ANDROID_BITMAP_FORMAT_RGBA_8888 || b.format != a.format
            || !a.width || !a.height || engine < 0 || engine > 1 || strength < 1 || strength > 3
            || (engine == 0 ? (scale != 1 && scale != 2) : (scale < 2 || scale > 4))
            || (backend != 0 && backend != 1)
            || b.width != a.width * scale || b.height != a.height * scale)
            throw std::runtime_error("图片格式、尺寸或处理参数不支持");

        ProgressCallback callback(env, listener);
        const char* chars = env->GetStringUTFChars(root, nullptr);
        if (!chars) return nullptr;
        std::string dir(chars);
        env->ReleaseStringUTFChars(root, chars);
        size_t count = size_t(a.width) * a.height;
        std::vector<unsigned char> rgba(count * 4), input(count * 3),
            output(size_t(b.width) * b.height * 3);
        {
            LockedPixels pixels(env, source);
            for (unsigned y = 0; y < a.height; y++)
                memcpy(rgba.data() + size_t(y) * a.width * 4,
                       (char*)pixels.data + size_t(y) * a.stride, size_t(a.width) * 4);
        }
        for (size_t i = 0; i < count; i++) {
            unsigned alpha = rgba[i * 4 + 3];
            for (int c = 0; c < 3; c++) input[i * 3 + c] = alpha
                ? std::min(255u, (rgba[i * 4 + c] * 255u + alpha / 2) / alpha) : 0;
        }
        ncnn::Mat in(a.width, a.height, (void*)input.data(), (size_t)3, 3);
        ncnn::Mat out(b.width, b.height, (void*)output.data(), (size_t)3, 3);

        int device = backend == 1 ? -1 : availableGpu();
        std::string label = device >= 0
            ? std::string("GPU · ") + ncnn::get_gpu_info(device).device_name() : "CPU";
        if (device >= 0) {
            try {
                infer(device, engine, strength, scale, dir, in, out, callback, label);
            } catch (const std::exception&) {
                // Restart this pass from its original input; discard partial GPU output.
                std::fill(output.begin(), output.end(), 0);
                label = "CPU（GPU 执行失败，已回退）";
                infer(-1, engine, strength, scale, dir, in, out, callback, label);
            }
        } else {
            if (backend == 0) label = "CPU（无可用 Vulkan GPU）";
            infer(-1, engine, strength, scale, dir, in, out, callback, label);
        }

        // Preserve transparency separately from the upstream RGB inference paths.
        {
            LockedPixels pixels(env, dest);
            for (unsigned y = 0; y < b.height; y++) for (unsigned x = 0; x < b.width; x++) {
                float sx = std::max(0.f, std::min(float(a.width - 1), (x + .5f) * a.width / b.width - .5f));
                float sy = std::max(0.f, std::min(float(a.height - 1), (y + .5f) * a.height / b.height - .5f));
                int x0 = int(sx), y0 = int(sy), x1 = std::min(x0 + 1, int(a.width - 1)),
                    y1 = std::min(y0 + 1, int(a.height - 1));
                float dx = sx - x0, dy = sy - y0;
                unsigned alpha = (1 - dy) * ((1 - dx) * rgba[(size_t(y0) * a.width + x0) * 4 + 3]
                    + dx * rgba[(size_t(y0) * a.width + x1) * 4 + 3])
                    + dy * ((1 - dx) * rgba[(size_t(y1) * a.width + x0) * 4 + 3]
                    + dx * rgba[(size_t(y1) * a.width + x1) * 4 + 3]) + .5f;
                auto pixel = (unsigned char*)pixels.data + size_t(y) * b.stride + x * 4;
                pixel[3] = alpha;
                for (int c = 0; c < 3; c++)
                    pixel[c] = (output[(size_t(y) * b.width + x) * 3 + c] * alpha + 127) / 255;
            }
        }
        return env->NewStringUTF(label.c_str());
    } catch (const CallbackFailure&) {
        return nullptr;
    } catch (const std::exception& e) {
        throwJava(env, e.what());
        return nullptr;
    }
}
