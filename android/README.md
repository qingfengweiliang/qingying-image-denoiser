# 清影 Android

已发布版本：**1.0.0（CPU）**。当前源码：**1.1.0-preview（Vulkan GPU / CPU）**。下载旧 APK 不会获得新源码功能；预览包通过 Android APK 工作流生成，尚未作为正式版本发布。

清影的安卓原生界面移植。适用于 **Android 7.0 及以上、64 位 ARM 手机**；默认源码及工作流构建包含 arm64-v8a 和模拟器使用的 x86_64；已发布的 1.0.0 手机 APK 仅含 arm64-v8a。六种算法均本地运行，模型随 APK 内置，不需要联网，不申请全盘文件访问权限。

## 使用

安装 `Qingying-Android-1.0.0.apk`，首次安装可能需要允许浏览器或文件管理器“安装未知应用”。打开图片，选择算法、强度、倍率后开始降噪。当前源码增加“自动 · 优先 GPU”和“CPU · 兼容模式”，会记住你的选择；设备检测结果显示在算法下方。使用“原图 / 结果 / 分割对比”检查结果；双指缩放，拖动画面或中间分割线，双击复位。保存时可选择 PNG、JPEG、WebP 和系统文件位置。点击标题旁的 ⓘ 查看说明和第三方许可证。

| 算法 | 安卓倍率 | 当前源码说明 |
| --- | --- | --- |
| Waifu2x CUNet | 1 / 2 / 4× | Vulkan / CPU 分块推理；4× 连续两次 2× |
| Real-CUGAN | 1 / 2 / 3 / 4× | Vulkan / CPU；1× 先 2× 重建后缩回；3 / 4× 固定高强度 |
| AI Image Rehab | 1× | 沿用原项目杂纹清理算法 |
| 非局部均值 | 1× | OpenCV 照片降噪 |
| 双边滤波 | 1× | OpenCV 快速保边 |
| 中值滤波 | 1× | OpenCV 椒盐颗粒处理 |

当前版本面向单张图片，不含 Windows 批量处理和超过 4× 的放大。自动模式在设备有可用 Vulkan GPU 时加速两种 AI 算法；不支持时使用 CPU。GPU 返回可恢复错误时会重新用 CPU 处理当前轮，保留其他已完成轮次；手动 CPU 模式可用于驱动不兼容的机型。其余四种算法仍使用 CPU。手机上大图可能处理较久；请保持应用打开，系统强制终止应用会中断任务。仍不提供中途取消。输入上限 1600 万像素，实际处理上限还会按设备可用 Java 堆、算法和中间放大倍率进一步收紧。该限制降低内存风险，但无法保证任意图片在所有机型上都可完成。

图片按常规 8 位 RGB/RGBA 处理，支持 EXIF 方向校正，不支持相机 RAW。透明度保留；JPEG 输出合成白色背景。导出不保留原始 EXIF、GPS、ICC 等元数据。使用 Android 系统文件选择器导入和导出；不上传图片。

## 进度、速度与耗时

- 两种 AI 算法显示真实的“已完成 / 总图块步骤”和推理百分比。Real-CUGAN 会把多轮 SE 推理纳入总量；Waifu2x 4× 会合并两轮不同尺寸的图块数。
- 每完成一块才更新计数。GPU 以命令执行完成为准，不把刚入队的任务算成已完成。
- 显示处理设备、总耗时、当前轮平均图块步骤/秒与预计剩余时间；至少完成两步且累计两秒后才估算。不同图块和阶段耗时不同，预计时间会变化。
- 若 GPU 失败重试，当前轮从零重新统计，旧的 GPU 速度不用于 CPU 估算，总用时包含失败尝试。
- 导入、加载模型、编码、保存及四种 CPU 算法显示真实阶段和耗时。OpenCV / SciPy 的单次调用无法提供内部百分比，此时不会显示推测百分比。
- 完成后显示总时间和输入像素 MP/秒，便于同图、同算法、同倍率比较 CPU / GPU；这个数值包含准备和编码，不是 GPU 核心基准。

## 兼容性与测试包

Vulkan 是可选加速能力，不增加最低系统要求。运行库仍动态检测驱动，CPU 模式可在无 Vulkan 设备使用。GPU 驱动崩溃或系统杀进程不能通过普通错误回退恢复；遇到闪退时重开并手动选择 CPU。16 KB 内存页和不同品牌 ARM64 手机仍需要实机验证。

工作流的 Debug APK 由调试密钥签名，不能直接覆盖用原始私有密钥签名的正式 APK。要覆盖更新，需用原来的私有签名构建 Release；不能用临时密钥冒充正式更新。原签名密钥不应放进源码、PR 或测试包。预览版本增加到 versionCode 2，versionName 1.1.0-preview。

## 从源码构建

安装 JDK 17、Python 3.10、Android SDK Platform 35、Build Tools 35.0.0、NDK 27.2.12479018、CMake 3.22.1。在 Android Studio 的 SDK Manager 中可安装这些组件。

```sh
cd android
python scripts/prepare_ncnn.py
# 用 Android Studio 打开此目录，让 IDE 生成 local.properties；或设置 ANDROID_HOME。
./gradlew :app:assembleDebug
```

Windows 使用 `gradlew.bat :app:assembleDebug`。脚本固定 ncnn 20250503 并校验 SHA-256；模型权重已经包含在 `app/src/main/assets/`。Python 包版本固定在 `app/build.gradle`，首次构建需要联网下载 Maven/Chaquopy 依赖。包内原生库仅编译 arm64-v8a 和 x86_64。

Debug APK：`app/build/outputs/apk/debug/app-debug.apk`。Release：`./gradlew :app:assembleRelease`。默认 Release 未签名。手机单架构版本可执行 `./gradlew -PqingyingAbi=arm64-v8a :app:assembleRelease`。

若要使用交付 APK 的同一签名更新安装，请妥善保留随交付提供的**独立签名备份**；不要上传到公开仓库。将密钥复制到私有位置，在 `android/signing.properties` 填写：

```properties
storeFile=/absolute/private/path/qingying-android.jks
storePassword=你的备份密码
keyAlias=qingying
keyPassword=你的备份密码
```

该文件及 `*.jks` 均被 Git 忽略。配置后 `assembleRelease` 会自动签名。若丢失签名密钥，就无法覆盖更新已经安装的版本。

## 验证

`python tests/test_progress.py` 使用 JDK 验证百分比、速度、剩余时间、GPU 重试和 4× 轮次计算。`./gradlew :app:assembleDebug :app:assembleDebugAndroidTest :app:lintDebug` 构建应用、仪器测试和安卓静态检查。启动 x86_64 或 arm64 安卓设备后，`./gradlew :app:connectedDebugAndroidTest` 运行导入、六种算法、透明度、AI 放大与三种导出格式测试。

`python tests/test_processing.py` 在有 NumPy / SciPy / Pillow / OpenCV 的主机上验证四种 Python 算法与导出。`tests/native/` 包含供桌面 ncnn 库运行的 C++ 核心与逐块进度回归测试；运行 `smoke` 验证 CPU，运行 `smoke --gpu` 验证 Vulkan（无 GPU 时会失败，避免把未执行当作通过）。GitHub 工作流通过 Mesa 软件 Vulkan 执行 GPU 路径，并在安卓模拟器运行仪器测试；这些结果不能替代手机 GPU 性能与兼容性验证。原生回归也可使用带 AddressSanitizer 的工具链检查极小图片和分块边界。

第三方许可证位于 `app/src/main/assets/licenses/` 和各 Python 包元数据中。模型、源码来源和移植修补说明见 `licenses/NOTICE.txt`。原项目 Windows 代码保持原状。正式版本通过项目 GitHub Releases 分发，主分支保留可复现构建的源码和工作流。

Windows 下填写 storeFile 时建议使用正斜杠，例如 C:/Private/qingying-android.jks，避免 Properties 文件中的反斜杠转义。

本次功能、验证范围和真机待测项见 [GPU 验证记录](../docs/android-gpu-validation.md)；Android 1.0.0 的历史记录保留于 [原验证记录](../docs/android-validation.md)。
