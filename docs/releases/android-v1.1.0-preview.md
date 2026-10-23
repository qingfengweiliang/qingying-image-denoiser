# Android 1.1.0-preview

本页对应当前源码中的 GPU 与进度改进，尚未发布正式 APK。现有 `android-v1.0.0` 下载仍为原 CPU 版本。

## 变化

- Waifu2x CUNet、Real-CUGAN 自动优先使用 Vulkan GPU；无可用设备时使用 CPU。
- GPU 的模型加载、着色器创建、推理或命令提交返回可恢复错误时，释放当前推理资源并用 CPU 重做当前轮。可手动选择并保存 CPU 兼容模式。
- 显示可用 GPU 名称及处理时实际使用的设备。
- 修正内置着色器传入长度包含结尾 NUL 字符的问题，避免 Vulkan 着色器编译失败。
- 修正 Real-CUGAN GPU 对极小图与狭长图的边界采样，使用与 CPU 一致的安全策略。
- AI 百分比按实际完成的图块步骤计算，覆盖 Real-CUGAN 多轮推理及 Waifu2x 4× 两轮放大。
- 显示耗时、图块步骤/秒和动态预计剩余时间；重试后重算速度。
- 其他算法及导入、加载、编码、保存显示阶段与耗时；完成后显示整次处理的 MP/秒。
- 增加原生模型 / 进度回归、进度计算回归与 Android 仪器测试覆盖，整理双平台下载入口与说明。

## 使用与验证

默认选择“自动 · 优先 GPU”。若出现驱动兼容性问题，可切换“CPU · 兼容模式”。加速只应用于两种 ncnn AI 引擎，其他四种算法仍在 CPU 执行。

速度取决于手机 GPU、驱动、图片与算法；软件 Vulkan 测试只能证明相关代码路径可执行，不能证明手机实际提速。ARM64 真机、不同品牌 GPU 与 16 KB 内存页设备仍需验证。GPU 驱动导致的原生崩溃不能依靠普通错误回退恢复。

Debug 测试包使用独立包名 `cn.qingying.denoiser.preview`，可与旧正式版同时安装；不能作为正式包的覆盖更新。正式更新必须使用原私有签名密钥，且保持版本代码递增。当前源码设置 `versionCode 2`、`versionName 1.1.0-preview`。

[完整安卓说明](../../android/README.md) · [本次验证记录](../android-gpu-validation.md) · [Android 1.0.0 历史验证](../android-validation.md)
