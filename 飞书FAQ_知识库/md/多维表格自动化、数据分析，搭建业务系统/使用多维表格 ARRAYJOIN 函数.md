# 使用多维表格 ARRAYJOIN 函数

原文链接：https://www.feishu.cn/hc/zh-CN/articles/369600104899

## 正文

一、了解 ARRAYJOIN 函数​

ARRAYJOIN 函数：通过指定的符号，将数组或列表中的元素拼接成字符串。需要结合 LIST 函数使用​

示例：ARRAYJOIN(LIST("A","B","C"),"-") = A-B-C​

  1. 函数公式：ARRAYJOIN(数组, [分隔符])​



  2. 参数介绍​



  * 数组：要拼接到一起的数组​



  * 分隔符：将数组中各元素拼接起来的符号，默认为英文逗号​



  3. 使用场景​



  * 将多选中的选项进行拼接​



  * 将查找到的信息通过换行或其他自定义符号进行分割​



二、场景实践​

拼接多选字段中的选项​

【场景】如果需要将多选字段中的多个选项按照希望呈现的方式进行拼接，可以使用 ARRAYJOIN 函数将各选项内容拼接到一起。以下图为例，可以用 ARRAYJOIN 函数将每位嘉宾的擅长领域合并到同一个单元格​

【公式】ARRAYJOIN([擅长领域]," & ")​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/7550eff9ab7449dfa8926b95e8c1df8b~tplv-jbbdkfciu3-image:0:0.image)​​

合并不同字段的内容​

【场景】：在产品问题走查表中，可以使用 ARRAYJOIN 和 LIST 将问题出现的设备系统、问题类型和修复优先级等信息合并到一起，方便快速集中信息​

【公式】：ARRAYJOIN(LIST([设备],[设备系统],[问题类型],[优先级])," - ")​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/3a53e2e52e8e44b5981d803368d8f052~tplv-jbbdkfciu3-image:0:0.image)​​

分割查找到的多条数据​

【场景】：汇总整理信息时，可以将从其他数据表中引用过来符合条件的数据整理到一起，方便查看。比如在下图中，希望从 客户关系管理 表中将每位成员所负责的客户名称同步到 销售成员信息 表中，并通过换行的方式展示。​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/6ab9a688f13a49c8b06944406575a2d3~tplv-jbbdkfciu3-image:0:0.image)​​

【公式】：ARRAYJOIN([客户关系管理].FILTER(CurrentValue.[跟进销售人员]=[姓名]).[客户名称],CHAR(10))​

​

250px|700px|reset

![](https://p1-hera.feishucdn.com/tos-cn-i-jbbdkfciu3/71d39d883d6941d38d940f6c1d00837f~tplv-jbbdkfciu3-image:0:0.image)​​

​
