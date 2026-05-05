# 使用 MSI 文件批量部署飞书客户端

原文链接：https://www.feishu.cn/hc/zh-CN/articles/360049067543

## 正文

一、功能简介​

飞书提供 MSI 文件（以下简称本工具）以帮助团队批量部署飞书客户端至多台 Windows 设备。企业内的 IT 管理员可通过本工具进行飞书的部署，部署完成后，团队成员登录 Windows 账号即可使用飞书。​

安装须知 ​

  * 本工具适用于 32 位及 64 位版本的 Windows 7 及以上系统。 ​



  * 部署本工具需要管理员权限。 ​



  * 本工具部署完成后，飞书客户端将在目标 Windows 用户下次登录时自动安装并启动。 ​



  * 卸载本工具将不会同时卸载飞书客户端。卸载后，未安装飞书的用户登录时不再自动安装。 ​



二、操作流程​

自定义参数 ​

  * 设置飞书路径 ​



若安装命令行设置参数 DEPLOY_DIR="飞书路径" ，则会将飞书安装到该路径（需普通权限用户对该路径有读写权限），如： ​

​

Plain Text

复制

msiexec /i Feishu-xxxx.msi DEPLOY_DIR="D:\Feishu" ​

​

  * 输出安装日志 ​



若安装命令行设置参数 /l*V "日志路径" ，则可以记录详细的安装日志，用于排查异常情况（日志目录必须已经存在）。如： ​

​

Plain Text

复制

msiexec /i Feishu-xxxx.msi /l*V "C:\FeishuDeploymentTool.log" ​

​

下载地址 ​

MSI 32 位安装包：[点击下载](https://sf3-cn.feishucdn.com/obj/hera-cn/download/Feishu-win32_ia32-7.65.8-signed.msi)​

MD5 HASH：a0ffd26aab0e00a7ba8e664ff9959d11​

MSI 64 位安装包：[点击下载](https://sf3-cn.feishucdn.com/obj/hera-cn/download/Feishu-win32_x64-7.65.8-signed.msi)​

MD5 HASH：130c686dfb064a7409b2b7c2c9344299​

三、了解更多 ​

[飞书 Windows 版本安装或启动失败怎么办？](https://www.feishu.cn/hc/zh-CN/articles/360043226713)​

[使用飞书的硬件要求 ](https://www.feishu.cn/hc/zh-CN/articles/360049067467)​

[查看或升级飞书版本](https://www.feishu.cn/hc/zh-CN/articles/360043828013)​
