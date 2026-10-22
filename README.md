# 清影 · 图片降噪

Windows 本地图片降噪与放大工具，提供六种算法、中文界面和可缩放的原图 / 结果对比。当前版本：**2.5**。

![清影界面](docs/preview.png)

## 下载与使用

打开 [Releases](https://github.com/qingfengweiliang/qingying-image-denoiser/releases)，下载 `Qingying-2.5-Windows-x64.zip`，完整解压后运行 `清影图片降噪.exe`。

请保留同目录的 `_internal` 文件夹。使用打包版不需要安装 Python，处理过程在本机运行，不上传图片。

1. 点击“打开图片”，或把图片拖到中央预览区。
2. 在左侧选择算法、强度和输出倍率，点击“开始降噪”。
3. 使用“原图 / 结果 / 对比”查看效果；对比模式下左侧原图、右侧处理后。
4. 滚轮缩放、拖动画面，拖动中间手柄调整分割位置；“100%”检查实际像素，“适应”回到全图。
5. 点击“保存结果”导出 PNG、JPG 或 WebP。批量处理入口在顶部。

## 算法

| 算法 | 适用场景 | 输出倍率 |
| --- | --- | --- |
| Waifu2x CUNet | 插画、生成图颗粒清理 | 1 / 2 / 4 / 8 / 16 / 32× |
| Real-CUGAN | 线条与纹理重建 | 1 / 2 / 3 / 4× |
| AI Image Rehab | 生成图杂纹清理 | 1× |
| 非局部均值 | 普通照片噪点 | 1× |
| 双边滤波 | 轻度噪点、快速处理 | 1× |
| 中值滤波 | 黑白颗粒、椒盐噪声 | 1× |

Waifu2x 和 Real-CUGAN 需要支持 Vulkan 的显卡及驱动；其他算法使用 CPU。Real-CUGAN 的 1× 会先以 2× 重建再缩回；3×、4× 内置模型仅提供高强度。高倍率和大图处理时间会增加，预计输出超过 6000 万像素会被阻止。

## 从源码运行（Windows）

本版本在 Python 3.14 x64 上构建并测试。仓库内含所需的原生引擎和模型；请完整下载或克隆项目。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## 打包

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm build.spec
```

输出位于 `dist/清影图片降噪/`。对外分享时还应一并附上项目的 `licenses/` 和 `使用说明.txt`，完整压缩该目录。

## 2.5 更新

- 常用参数直接可见，减少嵌套卡片。
- 固定分割对比、滚轮缩放、拖动平移及高分屏 100% 像素查看。
- 点击或拖放导入，清晰的按钮可用状态。
- 外观和输出目录移入设置窗口。

已在本机验证六种算法、PNG/JPG/WebP 导出、参数约束和预览交互。降噪可能损失纹理或改变细节，不能恢复已丢失的信息。图片按常规 8 位 RGB/RGBA 处理，不支持相机 RAW；导出不保留原始 EXIF、GPS、ICC 等元数据。

## 第三方组件

本项目调用 [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan)、[realcugan-ncnn-vulkan](https://github.com/nihui/realcugan-ncnn-vulkan)、[AI Image Rehab](https://github.com/BlairKaiser/ai-image-rehab)、OpenCV、NumPy、SciPy、Pillow 和 PySide6/Qt。

第三方代码、引擎与模型保留原作者的许可证和来源说明，见 `licenses/`、`native/` 和 `third_party/`。本仓库尚未为原创界面代码指定独立开源许可证；公开可见不等于授权任意再分发。详细说明见 [使用说明](使用说明.txt) 与 [学习导航](GitHub学习导航.md)。
