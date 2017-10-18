# 北京市预约挂号统一平台脚本(Python3)

![](https://img.shields.io/badge/Language-Python3-007fc0.svg)
![](https://img.shields.io/badge/License-GPLv3-000000.svg)

- This is a fork of the [bjguahao](https://github.com/iBreaker/bjguahao).

- 目前还在调试中，没有稳定的版本，欢迎吐槽和试用

## 环境

- python3

- pip3 install requests

## 配置文件

- 在`config.json`写入如下数据：

```json
{
    "username": "130********",    // (Required) 登录手机号
    "password": "******",         // (Required) 密码
    "dutyDate": "2017-10-10",     // (Optional) 挂号日期，为空时，自动挂最新一天
    "hospitalId": "142",          // (Required) 医院ID，如142-北医三院
    "departmentId": "200039602",  // (Required) 科室ID，如200039602-运动医学科
    "dutyCode": "1",              // (Required) 1-上午，2-下午
    "medicareCardId": "",         // (Optional) 社保卡号，和身份证号一致，为空时，代表自费
    "doctorName": "张仲景",        // (Optional) 优先选择的专家姓名，为空时，优先从最好的医生开始选择
    "SystemAllocation": true      // (Optional) 当指定的专家没号时，是否由系统自动分配其他医生，true-分配，false-不分配，默认为true，当doctorName为空时，此项配置不生效
}
```

## 文档

- 医院ID和科室ID的获取

    ![](https://github.com/wzhvictor/bjguahao/raw/master/img/get-id.png)

## 运行

- ```python3 hospital_registration.py```

## 调试

- 运行时会在脚本目录下生成reg.log，这是一个较为详细的debug日志

## 致谢

- 感谢 [iBreaker](https://github.com/iBreaker) 作出的贡献

- 若有什么问题可以提Issues，或者在使用过程中有其他的问题及建议，或者想贡献代码，请加入交流群

    ![](https://github.com/wzhvictor/bjguahao/raw/master/img/qq-qun.png)

## 协议

- 基于 GPL-3.0 协议进行分发和使用，更多信息参见协议文件

    ![image](https://www.gnu.org/graphics/gplv3-127x51.png)
