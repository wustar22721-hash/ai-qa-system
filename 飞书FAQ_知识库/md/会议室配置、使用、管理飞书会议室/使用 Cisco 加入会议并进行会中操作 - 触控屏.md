# 使用 Cisco 加入会议并进行会中操作 - 触控屏

原文链接：https://www.feishu.cn/hc/zh-CN/articles/741591205455

## 正文

​

💡

此产品需另外购买。如需咨询，请联系[客服](https://applink.feishu.cn/client/web_url/open?width=640&height=480&mode=window&url=https%3A%2F%2Flinkchat.feishu.cn%2Fim-linkchat%2Fredirect.html%3Fsource%3D5%26channelId%3D44)或客户成功经理。​

​

通过阅读该文，你可了解 Cisco SIP/H.323 会议室系统（搭配触控屏）如何通过飞书 SIP/H.323 会议室连接器加入飞书视频会议并进行会中操作。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/bebfe7b95bb94d8ca9404f66f428a46f~tplv-jbbdkfciu3-image:0:0.image)​​

一、适用设备​

​

系列​| 型号​  
---|---  
SX 系列 ​| SX10/SX20/SX80 ​  
MX 系列 ​| MX200/MX300/MX700/MX800 ​  
Room Kit 系列 ​| Room Kit Mini/Room Kit/Room Kit Plus/Room Kit Pro ​  
Room 系列 ​| Room55/Room55D/Room70S/Room70D ​  
Board 系列 ​| Webex Board55/Webex Board70/Webex Board85 ​  
  
​

二、IP 地址​

建议根据 SIP/H.323 会议室系统所在地选择对应的 IP 地址。​

​

中国大陆 ​| [101.133.204.6](http://101.133.204.6)（上海） ​[47.113.78.43](http://47.113.78.43)（深圳） ​  
---|---  
欧美 ​| [3.235.69.157](http://3.235.69.157) ​[3.235.69.156](http://3.235.69.156) ​  
东南亚 ​| [18.141.149.151](http://18.141.149.151) ​[18.141.149.150](http://18.141.149.150) ​  
  
​

三、加入会议​

以下操作以 Room Kit Mini 为例：​

  1. 飞书插件快捷入会（推荐）​



飞书插件可实现在 Cisco 设备上直接呼叫飞书视频会议 ID 加入会议。​

1.1 入会步骤​

  1. 在触控屏中点击 加入飞书 ，进入飞书会议号输入界面； ​



  2. 使用数字键盘输入飞书会议号后，点击 拨打 ； ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/c2d75af4dc9749fb98c7866915cfcf26~tplv-jbbdkfciu3-image:0:0.image)​​

  3. 拨打成功后即可直接加入飞书会议。 ​



1.2 安装&卸载飞书插件​

Cisco 配有触摸板的 CE 版本设备可进行免费安装（例如：Cisco Touch 10 或 Cisco Webex Rooms Navigator）​

安装步骤：​

  * 方式一：通过命令行直接安装​



  1. 使用终端管理员身份，登录终端的网页端界面。点击界面导航栏的 Integration > Developer API。 ​



  2. 在 Developer API 命令框中输入命令即可安装 SIP 或 H.323 版本飞书插件。 ​



  1. 安装 SIP 版本（以 SIP 协议进行呼叫）： ​



  1. 中文版本：输入 “xCommand Provisioning Service Fetch Mode: Replace URL: [https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_cn.zip](https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_cn.zip)” 后，点击 Execute。 ​



  2. 英文版本：输入 “xCommand Provisioning Service Fetch Mode: Replace URL: [https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_en.zip](https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_en.zip)” 后，点击 Execute。 ​



  2. 安装 H.323 版本（以 H.323 协议进行呼叫）： ​



  1. 中文版本：输入 “xCommand Provisioning Service Fetch Mode: Replace URL: [https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_h323_cn.zip](https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_h323_cn.zip)” 后，点击 Execute。 ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/05333e96e1134aca814e9d3db7c9f0d4~tplv-jbbdkfciu3-image:0:0.image)​​

  3. 完成安装后，终端界面上新增“飞书”按钮则代表安装成功。 ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/2add4c9634464615abd26ccac9593669~tplv-jbbdkfciu3-image:0:0.image)​​

注：仅 CE 9.15.3 及以上版本支持显示飞书 logo。​

  * 方式二：通过上传安装包进行安装​



  1. 使用终端管理员身份，登录终端的网页端界面。点击界面顶端导航栏的 Maintenance > Backup and Restore。​



  2. 在页面中选择 Restore backup，并在 Upload Backup 中选择下载好的插件安装包上传即可； ​



  1. SIP 版本下载地址： ​



  1. 中文版本：[https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_cn.zip](https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_cn.zip)​



  2. 英文版本：[https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_en.zip](https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_en.zip)​



  2. H.323 版本下载地址： ​



  1. 中文版本：[https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_h323_cn.zip](https://lf3-static.bytednsdoc.com/obj/eden-cn/upipogbpu/feishu_join_h323_cn.zip) ​



  3. 完成安装后，终端界面上新增“飞书”按钮则代表安装成功。 ​



​

250px|700px|reset

![image.png](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/3ef4206f9bea497f815f381dfea5f787~tplv-jbbdkfciu3-png:0:0.png)​​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/ff1007c8832d4c67afe9d65b9f0d785f~tplv-jbbdkfciu3-image:0:0.image)​​

卸载步骤：​

  1. 使用终端管理员身份，登录终端的网页端界面。点击界面顶端导航栏的 Integration。 ​



  2. 删除 UI Extensions 和 Macro，并且删除 Setup/Personalization 里的 Brand Logo 即可完成卸载。 ​



  2. 常规方式入会​



2.1 拨打“会议 ID@IP 地址/域名”加入会议​

在主屏幕点击呼叫进入拨号页面，拨打 会议 ID@IP 地址/域名。拨打成功后，即可直接加入会议。 ​

操作步骤：​

  1. 在触控屏中点击 呼叫 ，进入呼叫界面； ​



  2. 输入 “会议 ID@IP 地址” 或 “会议 [ID@lvc.feishu.cn](mailto:ID@lvc.feishu.cn)”（例如： 123456789@[101.133.204.6](http://101.133.204.6) 或 [123456789@lvc.feishu.cn](mailto:123456789@lvc.feishu.cn)），输入完成后点击 呼叫 ； ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/8f5aa96b621849088b1c960959372e28~tplv-jbbdkfciu3-image:0:0.image)​​

  3. 呼叫成功后即可直接加入会议。​



2.2 拨打“接入IP/域名”加入会议​

在主屏幕点击呼叫进入拨号页面，拨打 IP 地址或域名 “[lvc.feishu.cn](http://lvc.feishu.cn)”。拨打成功后，进入飞书欢迎界面，输入 9 位会议 ID 后按 # 键即可加入会议。 ​

操作步骤：​

  1. 在触控屏中点击 呼叫 ，进入呼叫界面； ​



  2. 输入 IP 地址或域名 “[lvc.feishu.cn](http://lvc.feishu.cn)”后，点击 呼叫 ； ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/29df492898da4700807e57e58699863f~tplv-jbbdkfciu3-image:0:0.image)​​

  3. 呼叫成功后，你将在显示屏中看到飞书欢迎界面； ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/c5910bed20e041d8ac610bc5ed1ab4b4~tplv-jbbdkfciu3-image:0:0.image)​​

  4. 在触控屏中点击 键盘 ，输入飞书会议的会议 ID，输入完成后按 # 号键即可加入会议。 ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/a4f0f9551a674b6a876c4380aee11719~tplv-jbbdkfciu3-image:0:0.image)​​

四、会中操作​

  1. 在触控屏中点击 键盘 ，按 “1” 键即可显示菜单； ​



​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/91ae6f83a53f43ceaf361d0896cce9e7~tplv-jbbdkfciu3-image:0:0.image)​​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/0721506bdd354c929fe47b954fd3f3e1~tplv-jbbdkfciu3-image:0:0.image)​​

  2. 在菜单中可以查看会议 ID 并进行以下会议控制操作： ​



  1. 按 “1” 键，切换视频布局。视频布局共分为三种：宫格视图、缩略图视图、演讲者视图。 ​



  2. 按 “2” 键，开启或者关闭麦克风。 ​



  3. 按 “3” 键，开启或者关闭摄像头。 ​



  4. 按 “4” 键，显示或隐藏本地视图，设置是否看自己的视频画面。 ​



  5. 按 “0” 键，切换语音/图片提示的语言。目前支持简体中文、英文两种语言。 ​


