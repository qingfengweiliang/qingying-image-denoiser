# GPT 去鳞纹接入说明

清影 2.6 新增三个算法选项，可直接使用原有的打开图片、对比预览、保存和批量处理。

| 选项 | 处理过程 |
| --- | --- |
| GPT 去鳞纹 · ESRGAN + L0 | BOX 预缩、Real-ESRGAN x4plus anime 6B 重建、Lanczos 恢复原尺寸、L0 平滑 |
| GPT 去鳞纹 · CUGAN + L0 | BOX 预缩、Real-CUGAN 2× 高档重建、Lanczos 恢复原尺寸、L0 平滑 |
| L0 平滑 · 纯算法 | 只做 L0 平滑，无需显卡 |

| 强度 | 预缩比例 | L0 λ |
| --- | --- | --- |
| 轻柔 | 80% | 0.0006 |
| 推荐 | 60% | 0.001 |
| 强力 | 45% | 0.0018 |

先尝试 ESRGAN + L0 的推荐档。淡阴影、腮红或细字丢失时改用轻柔。L0 单独使用时忽略预缩比例。

输出始终为输入原尺寸，保留原始透明通道。三个新模式最多处理 800 万像素，避免全图双精度 FFT 耗尽内存。模型在支持 Vulkan 的显卡上运行，L0 在 CPU 上运行，大图可能需要较长时间；纯 L0 模式不需要 Vulkan。运行时不联网、不下载模型、不上传图片。

保留原先的 Waifu2x 默认选项。新增模式可用于单张、批量及 PNG/JPEG/WebP 保存。原工具的色彩/元数据和 8 位处理约定继续适用。

实现参考 [CXP-2024/gpt-anime-denoise](https://github.com/CXP-2024/gpt-anime-denoise)，作者 CXP-2024 / B站 hihihihi202。保留其 MIT 许可于 ../licenses/gpt-anime-denoise-LICENSE.txt。

为适配原便携工具，模型推理改用 Real-ESRGAN NCNN Vulkan，L0 使用上游 NumPy 双精度 CPU 实现。不同推理后端及 CUGAN 模型版本的像素输出可能不同，不能视为与上游 PyTorch 版本逐像素一致。没有引入网页界面、APISR、局部保护笔刷或连续微调控件；这次接入的是核心去鳞纹算法和三档预设。

Real-ESRGAN 官方引擎及模型来源：

- https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan
- https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0

模型及引擎许可证随 native/realesrgan 和 licenses 提供。重新打包命令与原 build.spec 相同。
