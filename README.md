# 北京市预约挂号统一平台脚本(Python3)

![](https://img.shields.io/badge/Language-Python3-007fc0.svg)
![](https://img.shields.io/badge/License-GPLv3-000000.svg)

- This is a fork of the [bjguahao](https://github.com/iBreaker/bjguahao).

## 环境

- python3

- pip3 install requests

## 配置文件

- 在`config.json`写入如下数据：

```json
{
    "username": "130********",
    "password": "******",
    "dutyDate": "2017-10-18",
    "hospitalId": "142",
    "departmentId": "200039602",
    "dutyCode": "1",
    "medicareCardId": "",
    "autoChoose": true
}
```

- 配置项说明

| key            | 是否必选 | 描述             | 备注                              |
|----------------|:--------:|------------------|-----------------------------------|
| username       |    是    | 登录手机号       |                                   |
| password       |    是    | 密码             |                                   |
| dutyDate       |          | 挂号日期         | 为空时，自动挂最新一天            |
| hospitalId     |    是    | 医院ID           | 如142-北医三院                    |
| departmentId   |    是    | 科室ID           | 如200039602-运动医学科            |
| dutyCode       |    是    | 上午/下午        | 1-上午，2-下午                    |
| medicareCardId |          | 社保卡号         | 和身份证号一致，为空时，代表自费  |
| autoChoose     |          | 系统自动选择医生 | true-自动，false-手动，默认为true |

## 文档

- 医院ID和科室ID的获取

    ![](https://github.com/wzhvictor/bjguahao/raw/master/img/get_id.png)

## 运行

- ```python3 hospital_registration.py```

## 调试

- 运行时会在脚本目录下生成reg.log，这是一个较为详细的debug日志

## 致谢

- 感谢 [iBreaker](https://github.com/iBreaker) 作出的贡献

- 感谢 [@lily0101](https://github.com/lily0101) 提供详细的 [挂号攻略](tips.md)

- 若有什么问题可以提Issues，或者在使用过程中有其他的问题及建议，或者想贡献代码，请加入交流群

    ![](https://github.com/wzhvictor/bjguahao/raw/master/img/qrcode.png)

## 协议

- 基于 GPL-3.0 协议进行分发和使用，更多信息参见协议文件

    ![image](https://www.gnu.org/graphics/gplv3-127x51.png)

## 更新日志

- 2017-10-18 V0.1.0: 支持挂指定专家的号，并且可选择在该专家没号时是否接受由系统分配的其他号源。

- 2017-11-16 V0.2.0: 删除在配置中指定专家的功能，增加挂号时根据号源列表手动选择医生的功能。

- 2018-02-28 V0.2.1: 优化日志输出。

- 2018-11-02 V0.2.2: 用户名及密码在程序内进行base64处理，验证码的确认接口url更改