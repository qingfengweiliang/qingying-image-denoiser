# 清影 Android 1.0.0

清影的安卓原生界面移植。适用于 **Android 7.0 及以上、64 位 ARM 手机**；默认源码构建另含 x86_64 供模拟器使用；本次手机交付 APK 仅含 arm64-v8a 以缩小体积。六种算法均本地运行，模型随 APK 内置，不需要联网，不申请全盘文件访问权限。

## 使用

安装 `Qingying-Android-1.0.0.apk`，首次安装可能需要允许浏览器或文件管理器“安装未知应用”。打开图片，选择算法、强度、倍率后开始降噪。使用“原图 / 结果 / 分割对比”检查结果；双指缩放，拖动画面或中间分割线，双击复位。保存时可选择 PNG、JPEG、WebP 和系统文件位置。点击标题旁的 ⓘ 查看说明和第三方许可证。

| 算法 | 安卓首版倍率 | 说明 |
| --- | --- | --- |
| Waifu2x CUNet | 1 / 2 / 4× | CPU 分块推理；4× 连续两次 2× |
| Real-CUGAN | 1 / 2 / 3 / 4× | 1× 先 2× 重建后缩回；3 / 4× 固定高强度 |
| AI Image Rehab | 1× | 沿用原项目杂纹清理算法 |
| 非局部均值 | 1× | OpenCV 照片降噪 |
| 双边滤波 | 1× | OpenCV 快速保边 |
| 中值滤波 | 1× | OpenCV 椒盐颗粒处理 |

当前版本面向单张图片，不含 Windows 批量处理和超过 4× 的放大。AI 使用 CPU，手机上大图可能处理较久；请保持应用打开，系统强制终止应用会中断任务。没有进度百分比和中途取消。输入上限 1600 万像素，实际处理上限还会按设备可用 Java 堆、算法和中间放大倍率进一步收紧。该限制降低内存风险，但无法保证任意图片在所有机型上都可完成。

图片按常规 8 位 RGB/RGBA 处理，支持 EXIF 方向校正，不支持相机 RAW。透明度保留；JPEG 输出合成白色背景。导出不保留原始 EXIF、GPS、ICC 等元数据。使用 Android 系统文件选择器导入和导出；不上传图片。

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

`./gradlew :app:lintDebug` 执行安卓静态检查。启动 x86_64 或 arm64 安卓设备后，`./gradlew :app:connectedDebugAndroidTest` 运行导入、六种算法、透明度、AI 放大与三种导出格式测试。

`python tests/test_processing.py` 在有 NumPy / SciPy / Pillow / OpenCV 的主机上验证四种 Python 算法与导出。`tests/native/` 包含供桌面 ncnn 库运行的 C++ 核心回归测试，可启用 AddressSanitizer 检查极小图片及分块边界；它不能替代安卓真机测试。

第三方许可证位于 `app/src/main/assets/licenses/` 和各 Python 包元数据中。模型、源码来源和移植修补说明见 `licenses/NOTICE.txt`。原项目 Windows 代码保持原状。正式版本通过项目 GitHub Releases 分发，主分支保留可复现构建的源码和工作流。

Windows 下填写 storeFile 时建议使用正斜杠，例如 C:/Private/qingying-android.jks，避免 Properties 文件中的反斜杠转义。
