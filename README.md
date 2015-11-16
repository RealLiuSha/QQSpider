# QQSpider

* 这是一个用于收集QQ群消息的小程序，依赖smart qq，故此登陆采用的是二维码扫描方式，由于是用来收集QQ群消息的，所以它没有任何娱乐性，支持邮件提醒（轮询失败超过阈值，网络超时断开，掉线什么的），它的运行依赖一个配置文件。


# 配置文件(config.ini)

如果你不希望配置文件和程序放在一起，你可以通过环境变量来指定，譬如这样:
  
`export QQ_CONFIG_PATH=/tmp/config.ini`

显然，你也看出来了，这个小程序比较傻，它就要读config.ini，这个也无伤大雅..,没有环境变量的情况下，它默认读取当前目录中的`config.ini`。

配置文件多数是这样的:
```
[path]
logs=/tmp/log
data=/tmp/data
qrcode=/tmp/qrcode

[smtp]
mail_to_list=444127002@qq.com,itchenyi@gmail.com
mail_host=smtp.exmail.qq.com
mail_port=465
mail_user=zhangsan
mail_pass=password
mail_postfix=ipython.com
```

* logs 定义了logs的输出，包括pull massage、异常等
* data 存放收集的群消息
* qrcode 存放用于登陆的二维码

依赖：
  * grequests  （优雅的异步http库）
  * python 2.7

运行：
  `python qq.py --number=444127002 --action=start`

  * --number 这里需要填写QQ号
  * --action 这里需要跟运行方式，支持[start|stop|restart|debug]

  以start的方式将会运行于后台，pid将存放于`/tmp`目录下
