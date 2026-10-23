#include "waifu2x.h"
#include "realcugan.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char** argv)
{
    const bool gpu = argc > 1 && std::string(argv[1]) == "--gpu";
    int device = -1;
    if (gpu) {
        if (ncnn::create_gpu_instance() != 0 || ncnn::get_gpu_count() == 0)
            throw std::runtime_error("GPU regression requested but no Vulkan device is available");
        device = ncnn::get_default_gpu_index();
        std::cout << "Vulkan device: " << ncnn::get_gpu_info(device).device_name() << std::endl;
    }
    for (auto dims : {std::pair<int,int>{1,1}, {17,19}, {131,67}})
        for (int engine = 0; engine < 2; engine++)
            for (int scale = 1; scale <= 4; scale++)
                for (int noise = 1; noise <= 3; noise++) {
        if (engine == 0 && scale > 2) continue;
        if (engine == 1 && (scale == 1 || (scale > 2 && noise < 3))) continue;
        int w = dims.first, h = dims.second;
        std::vector<unsigned char> input(w*h*3), output(w*h*3*scale*scale);
        for (int i = 0; i < w*h; i++) {
            input[i*3] = 96; input[i*3+1] = 144; input[i*3+2] = 192;
        }
        ncnn::Mat in(w, h, (void*)input.data(), (size_t)3, 3);
        ncnn::Mat out(w*scale, h*scale, (void*)output.data(), (size_t)3, 3);
        int completed = 0, total = 0, calls = 0;
        auto progress = [&](int done, int count) {
            if (done < completed || done > count || count <= 0)
                throw std::runtime_error("Progress moved backwards or exceeded total");
            completed = done; total = count; calls++;
        };
        int tiles = ((w+15)/16) * ((h+15)/16);
        int expected = tiles * (engine == 1 && std::max(w,h) > 16 ? 5 : 1);
        std::string root = ASSETS_DIR;
        if (engine == 0) {
            Waifu2x net(device, false, 2);
            net.noise = noise; net.scale = scale; net.tilesize = 16;
            net.prepadding = scale == 1 ? 28 : 18;
            net.progress.callback = progress;
            std::string stem = root + "models-cunet/noise" + std::to_string(noise)
                + (scale == 1 ? "_model" : "_scale2.0x_model");
            require_ncnn(net.load(stem + ".param", stem + ".bin"));
            require_ncnn(net.process(in, out));
        } else {
            RealCUGAN net(device, false, 2);
            net.noise = noise; net.scale = scale; net.tilesize = 16;
            net.prepadding = scale == 2 ? 18 : scale == 3 ? 14 : 19;
            net.syncgap = 1; net.progress.callback = progress;
            std::string stem = root + "models-se/up" + std::to_string(scale)
                + "x-denoise" + std::to_string(noise) + "x";
            require_ncnn(net.load(stem + ".param", stem + ".bin"));
            require_ncnn(net.process(in, out));
        }
        if (completed != expected || total != expected || calls != expected + 1)
            throw std::runtime_error("Incomplete inference tile callbacks");
        double sum = 0;
        for (size_t i = 0; i < output.size(); i += 3) sum += output[i];
        if (sum / (w*h*scale*scale) < 50) throw std::runtime_error("Output is empty or corrupted");
        std::cout << "PASS " << (gpu ? "GPU" : "CPU") << " engine=" << engine
            << " size=" << w << 'x' << h << " scale=" << scale << " noise=" << noise
            << " progress=" << completed << '/' << total << std::endl;
    }
    // A failed load must throw safely, including safe partially-loaded destructors.
    bool rejected = false;
    try {
        RealCUGAN broken(device, false, 2);
        broken.load("/missing/model.param", "/missing/model.bin");
    } catch (const std::exception&) { rejected = true; }
    if (!rejected) throw std::runtime_error("Invalid model was not rejected");
    std::cout << "PASS missing-model failure cleanup" << std::endl;
}
