# 清影 Android 1.0.0 · 接手操作说明

更新日期：2026-10-22。本文不包含签名密钥、密码或访问令牌。

## 现在已经完成的部分

- 安卓正式版已经发布，发布页顶部的发布者是 **qingfengweiliang**，与 Windows 版一致。
- 完整交付 ZIP 已从安卓 Release 移除，主页和版本说明里的对应入口也已删除。
- 正式附件仅保留 APK 和 SHA-256 校验文件，APK 的二进制与签名没有改变。
- Windows 版 V2.5.0 保留；会自动创建安卓发布页的流程已撤掉，普通测试构建流程保留。

## 明天先下载这两个文件

- [APK 安装包](https://github.com/qingfengweiliang/qingying-image-denoiser/releases/download/android-v1.0.0/Qingying-Android-1.0.0.apk)
- [SHA256SUMS.txt 校验文件](https://github.com/qingfengweiliang/qingying-image-denoiser/releases/download/android-v1.0.0/SHA256SUMS.txt)
- [正式版本页面](https://github.com/qingfengweiliang/qingying-image-denoiser/releases/tag/android-v1.0.0)

APK 文件名：Qingying-Android-1.0.0.apk；大小：97,738,939 字节，约 93 MB。

APK 的 SHA-256：

```
a85418a7b71a51b52ca217392ce99eb5a5e040b7c6eeb56dc59605f74a0218a8
```

在 Windows PowerShell 中核对：

```powershell
Get-FileHash .\Qingying-Android-1.0.0.apk -Algorithm SHA256
```

## 如果你只想改发布页顶部的账号

这件事已经完成，不需要再操作。安卓页和 Windows 页的发布者现在都是 qingfengweiliang。

## 如果连附件的实际上传账号也要改

当前 APK 和校验文件的底层上传记录仍是 **github-actions[bot]**。现有连接可以用你的账号创建发布页，但文件上传接口无法用该账号完成上传。因此，没有把附件上传记录冒充成你的账号。GitHub 也没有直接编辑既有附件上传者的接口。

请用浏览器手动重新上传一次：

1. 先把上面的 APK 和 SHA256SUMS.txt 下载到自己电脑，确认文件都在，再修改网页。不要删除本地文件。
2. 登录 GitHub，确认当前账号是 qingfengweiliang。
3. 打开 [安卓版本编辑页](https://github.com/qingfengweiliang/qingying-image-denoiser/releases/edit/android-v1.0.0)。
4. 在附件区删除原来的 APK 和 SHA256SUMS.txt，只处理这两个附件。
5. 将刚才下载的同名 APK 和校验文件拖回附件区，等待上传完成。
6. 保持标签 android-v1.0.0、标题和正式发布状态不变，点击 Update release / 更新版本。

**不要删除整个 Release，不要删除版本标签，也不要修改 Windows 版本。** 附件重新上传期间，下载链接可能短暂不可用。

用你的账号完成这次网页上传后，新附件的 uploader 就会记录为 qingfengweiliang。可以打开 [公开版本元数据](https://api.github.com/repos/qingfengweiliang/qingying-image-denoiser/releases/tags/android-v1.0.0)，在 assets 中查看每个附件的 uploader.login；发布页顶部显示的 author 和附件的 uploader 是两个独立字段。

GitHub 自动附带的 Source code.zip / tar.gz 是平台源码归档，不是先前那个完整交付 ZIP，不需要处理。

## 另外一个可选的小整理

仓库 About 简介仍是旧的 Windows 描述，因为当前连接修改该字段返回权限不足。你可以在 [项目主页](https://github.com/qingfengweiliang/qingying-image-denoiser) 右侧 About 的齿轮里，把简介改成：

清影：Windows / Android 本地图片降噪与放大工具，六种算法、中文界面、原图分割对比与离线处理。

README、安卓截图、下载入口和版本说明已经更新。

## 安装与后续更新提醒

- 此 APK 支持 Android 7.0+ 的 ARM64 手机，不支持 32 位安卓设备。
- 六种算法、透明度、AI 放大和 PNG/JPEG/WebP 导出已通过模拟器测试；尚未进行 ARM64 真机测试。
- 首版面向单张图片，最高 4 倍放大；大图处理时保持应用打开。
- 后续覆盖更新必须使用同一签名密钥，并增加 android/app/build.gradle 中的 versionCode。
- 签名备份仍单独保存在当前工作区，尚未通过公开链接交付。后续应私密取回并自行备份；不要把 JKS、密码文件或私密签名备份 ZIP 上传到公开仓库或 Release。

[安卓构建说明](https://github.com/qingfengweiliang/qingying-image-denoiser/blob/main/android/README.md) · [构建与验证记录](https://github.com/qingfengweiliang/qingying-image-denoiser/blob/main/docs/android-validation.md)
