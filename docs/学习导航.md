# 图片降噪学习导航

本工具 2.5 已集成 Waifu2x CUNet、Real-CUGAN、AI Image Rehab 自动清理及三种 OpenCV 常规算法，界面与文件处理逻辑独立实现。

## 已集成的二次元与生成图方法

| 界面模式 | 完整开源项目 | 本工具提供的功能 |
| --- | --- | --- |
| 二次元降噪 · 推荐 | [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan) · [原始 waifu2x](https://github.com/nagadomi/waifu2x) | CUNet 低/中/高三档，1× / 2× / 4× / 8× / 16× / 32× |
| Real-CUGAN · 线条重建 | [realcugan-ncnn-vulkan](https://github.com/nihui/realcugan-ncnn-vulkan) · [原始 Real-CUGAN](https://github.com/bilibili/ailab/tree/main/Real-CUGAN) | SE 模型，1× / 2× / 3× / 4×；3×、4× 仅高档 |
| AI Image Rehab · 杂纹清理 | [ai-image-rehab](https://github.com/BlairKaiser/ai-image-rehab) | 自动杂纹清理，原尺寸；未接入可选重绘功能 |

Real-CUGAN 的 1× 使用 2× 重建后缩回原图尺寸。Waifu2x、Real-CUGAN 使用 Vulkan 显卡，AI Image Rehab 与常规算法使用 CPU。代码与模型的来源说明及许可证均随程序提供。

## 本工具使用的算法

| 界面模式 | 方法 | Python 函数 | 源码 |
| --- | --- | --- | --- |
| 精细降噪 | 非局部均值 NLM | cv2.fastNlMeansDenoisingColored | [OpenCV denoising.cpp](https://github.com/opencv/opencv/blob/4.x/modules/photo/src/denoising.cpp) |
| 快速保边 | 双边滤波 | cv2.bilateralFilter | [OpenCV bilateral_filter.dispatch.cpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/src/bilateral_filter.dispatch.cpp) |
| 去除颗粒 | 中值滤波 | cv2.medianBlur | [OpenCV median_blur.dispatch.cpp](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/src/median_blur.dispatch.cpp) |

[OpenCV 完整仓库](https://github.com/opencv/opencv) · [NLM 官方教程](https://docs.opencv.org/4.x/d5/d69/tutorial_py_non_local_means.html)

源码链接使用 4.x 分支，便于配合教程阅读；本软件打包使用的版本见 requirements.txt。

## 其他学习项目（下列模型尚未集成）

1. [Image_Denoising_and_Filtering_Techniques](https://github.com/Lucydln/Image_Denoising_and_Filtering_Techniques)
   Python/OpenCV 入门示例，包含 NLM、双边滤波、中值滤波及示例图片。建议先看 nlm.py、Bilateral Filter.py、medianblur.py。属于教学脚本集合，README 有占位安装命令，学习时以仓库实际文件为准。

2. [DnCNN](https://github.com/cszn/DnCNN)
   经典残差 CNN 降噪，适合学习从传统算法到神经网络的过渡。仓库包含 MATLAB 代码，README 提供作者推荐的 PyTorch 训练、测试实现链接。

3. [SCUNet](https://github.com/cszn/SCUNet)
   面向实用盲降噪的项目，结合 Swin Transformer、卷积与 U-Net，提供测试代码、模型和训练相关内容。适合研究真实复杂噪声的处理。

4. [NAFNet](https://github.com/megvii-research/NAFNet)
   图像恢复项目，提供训练、测试配置及预训练模型。学习降噪时选择 SIDD 对应模型和文档，避免误用去模糊模型。

5. [Restormer](https://github.com/swz30/Restormer)
   Transformer 图像恢复项目，涵盖真实噪声和高斯噪声降噪，并提供训练、测试说明及演示。适合深入学习网络结构和实验流程。

建议学习顺序：OpenCV 示例 → DnCNN → SCUNet 或 NAFNet → Restormer。

深度学习项目通常需要另行配置 PyTorch 环境并下载对应权重；这些多为研究代码，不一定附有 Windows 图形界面。代码和模型的使用条件请分别以项目许可证为准。
