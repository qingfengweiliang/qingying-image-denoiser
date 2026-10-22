# 构建与验证记录

构建日期：2026-10-22。版本：清影 Android 1.0.0（versionCode 1）。源项目基准提交：`52f748b5b50259dfd837ea5bda7b5f1bf73d0244`。

## 交付内容

- `Qingying-Android-1.0.0.apk`：已签名 Release 安装包，包名 `cn.qingying.denoiser`。
- `源码/qingying-image-denoiser/`：项目源码，增加 `android/` 和 GitHub Actions 工作流；原 Windows 实现保留。
- `GitHub上传与发布说明.md`：上传源码、自动构建、发布 Release 和签名管理步骤。
- `验证记录/`：签名、对齐、Lint、核心算法等检查的原始记录。
- 签名备份另行提供，**不在这个公共交付 ZIP 内**。

## 已通过的构建和检查

- JDK 17、Gradle 8.11.1、Android Gradle Plugin 8.9.1、SDK 35 / Build Tools 35.0.0、NDK 27.2.12479018、CMake 3.22.1。
- Debug 与 Release 编译成功，Android 仪器测试 APK 编译成功。
- Android Lint：**0 个错误，3 个警告**；剩余为依赖可更新提示、中文字符串国际化及文本拼接提示。首版仅提供中文。
- `apksigner verify`：Release 签名验证通过，使用独立 RSA 3072 位首版签名密钥。
- `zipalign -c -P 16 -v 4`：APK ZIP 对齐检查通过。该检查不代表所有第三方 ELF 库都已在 16 KB 内存页设备上实测。
- Manifest 核对：最低 Android API 24，目标 API 35，手机交付 APK 原生架构 arm64-v8a，默认 Debug 测试构建另含 x86_64；Release 未申请联网或广泛存储权限。
- Python 算法与导出回归：通过。覆盖杂纹清理、非局部均值、双边滤波、中值滤波的多个强度、尺寸与透明度保留、PNG/JPEG/WebP 导出、JPEG 白底合成。
- ncnn 20250503 CPU 模型回归：**33 组通过**。覆盖 1×1、17×19、131×67 图片，Waifu2x 三档降噪与 1/2× 模型、Real-CUGAN 2× 三档及 3/4× 高强度模型。启用 AddressSanitizer 验证上层 C++ 边界访问；预编译的 ncnn 库本体未重新进行 sanitizer 插桩。

## 安卓运行验证

**Android 10 / API 29 x86_64 模拟器：通过（OK，1 项端到端测试，308 秒）。** 当前环境没有 KVM，采用软件模拟，因此该耗时不代表手机性能。覆盖真实 Activity 启动、图片导入、六种算法处理、输出尺寸和透明度、保存按钮状态、PNG/JPEG/WebP 编码、WebP 重新导入，以及 Waifu2x 2× / Real-CUGAN 3× 的 JNI 放大结果。

首次运行测试发现 Android Pillow 包缺少 WebP 编码器，已切换为系统编解码器并重新通过完整测试。运行测试使用含 x86_64 的 Debug 构建；手机交付使用同一处理实现的 ARM64 Release 构建，另外通过 Release 编译和 Lint。最终文件选择器的 JPEG MIME 类型也已校正为 image/jpeg。未进行 ARM64 真机安装测试。

## 移植处理

- 原生安卓界面和系统文件导入/导出。
- 两种 AI 引擎使用 CPU 推理，不要求手机 Vulkan GPU。
- 修复上游 CPU 路径向新版 ncnn 传递空 Vulkan 设备的问题。
- 修复极小图反射边界不足；必要时使用复制边界。
- 透明度独立缩放并处理安卓预乘 alpha，避开上游 Real-CUGAN 的 RGBA 分块复制越界。
- Real-CUGAN 使用 syncgap=1，避免上游 syncgap=3 在狭长图片上的空缓存访问。
- 安卓 Python 图像库未包含 WebP 编码器，WebP 导出改走 Android 系统编码器；无法由 Pillow 读取的系统支持格式使用安卓解码后转 PNG。
- 输入上限和按内存估算的输出限制；文件替换采用同卷重命名，减少失败时覆盖已有结果的风险。

## 使用范围与限制

面向单张图片；Waifu2x 最高 4×，Real-CUGAN 最高 4×。不含批处理和任务取消。AI 在手机 CPU 上处理大图可能较慢；处理时保持应用打开。非相机 RAW 工作流，输出不保留原始 EXIF/GPS/ICC。

未进行实体 Android 手机测试，不能据此承诺不同品牌手机的速度、内存上限或所有 Android 版本的兼容性。16 KB 内存页设备尚需真机测试。正式版本的真机验证范围仍以本记录为准。
