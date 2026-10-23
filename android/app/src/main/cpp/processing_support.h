#pragma once

#include <functional>
#include <stdexcept>
#include "gpu.h"

inline void require_ncnn(int code)
{
    if (code != 0) throw std::runtime_error("AI 引擎执行失败，请尝试 CPU 模式或较小图片");
}

// Counts completed inference tiles, including every SE pass in Real-CUGAN.
struct ProcessingProgress
{
    std::function<void(int, int)> callback;
    mutable int completed = 0;
    mutable int total = 0;

    void begin(int count) const
    {
        completed = 0;
        total = count;
        if (callback) callback(0, total);
    }

    void advance(int count = 1) const
    {
        completed += count;
        if (callback) callback(completed, total);
    }
};

// Release the GPU allocators even if model execution or command submission fails.
struct ScopedGpuAllocators
{
    ncnn::VulkanDevice* device;
    ncnn::VkAllocator* blob;
    ncnn::VkAllocator* staging;

    explicit ScopedGpuAllocators(ncnn::VulkanDevice* gpu) : device(gpu),
        blob(gpu->acquire_blob_allocator()), staging(gpu->acquire_staging_allocator()) {}

    ~ScopedGpuAllocators()
    {
        device->reclaim_blob_allocator(blob);
        device->reclaim_staging_allocator(staging);
    }
    ScopedGpuAllocators(const ScopedGpuAllocators&) = delete;
    ScopedGpuAllocators& operator=(const ScopedGpuAllocators&) = delete;
};
