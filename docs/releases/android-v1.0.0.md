# 清影 Android 1.0.0

清影首个安卓版本，提供六种本地图片降噪算法、AI 放大与原图 / 结果分割对比。

## 下载与安装

- [APK 安装包](https://github.com/qingfengweiliang/qingying-image-denoiser/releases/download/android-v1.0.0/Qingying-Android-1.0.0.apk)：约 93 MB，Android 7.0+ 的 ARM64 手机。
- [SHA-256 校验文件](https://github.com/qingfengweiliang/qingying-image-denoiser/releases/download/android-v1.0.0/SHA256SUMS.txt)。

下载 APK 后安装，按系统提示允许当前浏览器或文件管理器安装未知应用。应用不申请联网或广泛存储权限，使用系统文件选择器导入和导出。

## 功能

- Waifu2x CUNet、Real-CUGAN、AI Image Rehab、非局部均值、双边滤波、中值滤波。
- 中文原生界面，强度和倍率选择；两种 AI 使用 CPU 分块推理。
- Waifu2x 1 / 2 / 4×；Real-CUGAN 1 / 2 / 3 / 4×，其中 3 / 4× 固定高强度。
- 原图、结果与分割对比，双指缩放、拖动画面、双击复位。
- PNG、JPEG、WebP 导出，保留透明度；JPEG 使用白色背景。
- WebP 使用安卓系统编解码器，修复 Android Pillow 发行包缺少 WebP 编码器的问题。

## 验证与限制

Release 构建、Lint、签名和 ZIP 对齐校验通过。核心模型 33 组回归通过；Android 10 x86_64 模拟器端到端测试覆盖图片导入、六种算法、透明度、三种导出、WebP 重新导入与 AI 放大，全部通过。

**尚未进行 ARM64 真机测试。** 16 KB 内存页设备及不同品牌手机仍需兼容性验证。正式版本号表示此版本已发布，不表示已经覆盖全部机型。

首版只处理单张图片，不含批量处理或中途取消，最高 4× 放大。输入上限 1600 万像素，实际处理还受设备内存约束。AI 在 CPU 上处理大图可能较慢，处理时保持应用打开。导出不保留原始 EXIF、GPS、ICC 等元数据；不支持相机 RAW。

[完整构建与验证记录](../android-validation.md) · [安卓源码构建说明](../../android/README.md)
