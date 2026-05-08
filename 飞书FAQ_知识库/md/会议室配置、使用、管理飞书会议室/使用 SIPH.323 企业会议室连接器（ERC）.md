# 使用 SIP/H.323 企业会议室连接器（ERC）

原文链接：https://www.feishu.cn/hc/zh-CN/articles/129418723576

## 正文

​

💡

此产品需另外购买。如需咨询，请联系[客服](https://applink.feishu.cn/client/web_url/open?width=640&height=480&mode=window&url=https%3A%2F%2Flinkchat.feishu.cn%2Fim-linkchat%2Fredirect.html%3Fsource%3D5%26channelId%3D44)或客户成功经理。 ​

​

通过阅读该文，你可了解如何使用 SIP/H.323 企业会议室连接器（ERC）。​

一、部署 ERC​

企业会议室连接器完整部署流程：[SIP/H.323 企业会议室连接器（ERC）部署指南](https://www.feishu.cn/hc/zh-CN/articles/286197496493)​

二、管理 ERC​

  1. 配置 ERC 域名 ​



设置企业会议室连接器（ERC）域名，用于统一管理企业内部署的企业会议室连接器，域名通常在部署企业会议室连接器时设置，详见部署指南。​

注：若不配置域名，将无法通过 ERC 域名注册飞书账号及加入飞书会议​

管理员点击[管理后台](https://feishu.cn/admin/index)界面上方的 产品设置 > 视频会议 ，选择 SIP/H.323 会议室连接器，在 企业会议室连接器 页面中配置企业会议室连接器域名。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/5cc7b47b99d8467e8419b613d8bd6581~tplv-jbbdkfciu3-image:0:0.image)​​

  2. 管理 ERC 管理节点​



2.1 查看管理节点状态​

在 企业会议室连接器 页面查看企业会议室连接器管理节点状态。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/665627fc34cd420db143269497c0884e~tplv-jbbdkfciu3-image:0:0.image)​​

2.2 添加管理节点备注信息​

点击操作列的 备注，填写管理节点备注信息，点击 保存。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/5a5b464f91924891acd3558dd7cf872f~tplv-jbbdkfciu3-image:0:0.image)​​

2.3 查看管理节点详情​

点击 查看详情，进入管理节点详情页面，可查看管理节点基础信息、关联的会议节点，节点服务器的 CPU 占用、内存占用、磁盘空间占用、业务进程、发送带宽、接收带宽等信息。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/be1e75ab8a27481eba4ad604d1e514ac~tplv-jbbdkfciu3-image:0:0.image)​​

2.4 删除管理节点​

点击 删除，在弹窗中选择 删除，即可删除该管理节点。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/d9f03f592026498c904fb98b180ca790~tplv-jbbdkfciu3-image:0:0.image)​​

  3. 管理 ERC 会议节点​



3.1 查看会议节点状态​

在 企业会议室连接器 页面查看企业会议室连接器会议节点状态。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/7e642f3195aa4d9eab00a46e3e324a07~tplv-jbbdkfciu3-image:0:0.image)​​

3.2 添加会议节点备注信息​

点击 备注，填写会议节点备注信息，点击 保存。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/a9845db0a30c4393bf310db1c323d3a4~tplv-jbbdkfciu3-image:0:0.image)​​

3.3 查看会议节点详情​

点击 查看详情，进入管理节点详情页面，可查看管理节点基础信息、关联的会议节点，节点服务器的CPU 占用、内存占用、磁盘空间占用、业务进程、发送带宽、接收带宽等信息。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/8d1c290377fa4d508ea98bf80f327ab1~tplv-jbbdkfciu3-image:0:0.image)​​

3.4 删除会议节点​

点击 删除，在弹窗中选择 删除，即可删除该会议节点。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/3a24fe939bd343dfaff47c2e7a733169~tplv-jbbdkfciu3-image:0:0.image)​​

  4. 鉴权信息​



4.1 获取鉴权信息​

企业会议室连接器部署完成后，通过该鉴权信息绑定企业客户。​

点击鉴权信息后的 复制，在企业会议室连接器管理节点和会议节点的管理页面粘贴使用。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/a72d72786e124a72aa532d227c438708~tplv-jbbdkfciu3-image:0:0.image)​​

4.2 更新鉴权信息​

点击鉴权信息后的 更新密钥，可生成并使用全新的鉴权信息。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/2ecbd3a34d664fe084803b94663d0c44~tplv-jbbdkfciu3-image:0:0.image)​​

三、SIP/H.323 终端连接 ERC 加入会议​

根据企业终端设备品牌，参考相应的[终端配置帮助文章](https://www.feishu.cn/hc/zh-CN/categories-detail?category-id=6933474571597119516)，修改 SIP/H.323 终端配置，将连接的飞书域名或飞书公网 IP 修改为 企业会议室连接器（ERC）的域名或 IP 即可。​
