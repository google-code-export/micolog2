1 使用方法与原Micolog相同

2 记得在app.yaml中先替换成自己的app id，然后再做测试。

3 安装新Theme的时候将静态文件放到themes_static文件夹下，这样速度快些；不愿如此的话，在app.yaml里面将
  - url: /themes
    static_dir: themes_static
  这条配置去掉。

4 把我自己用的主题放了进来：Alltuts_Rex(Eng)。之所以放进来，是不想每次更新代码后再和自己的博客程序合并了。主题里有一些关于我个人博客的绑定，例如meta数据、Google Adsense, Google Analysis，喜欢这款主题的朋友可以在base.html和sidebar.html里面找找，然后替换为自己的。

5 页面内容会自动缓存，因此如果您启用验证码的话请确保验证码的显示是使用ajax

6 bug到http://code.google.com/p/micolog2/issues/list提交，或者在我的博客相关页面(http://blog.rexzhao.com/2011/12/1/micolog2-alpha-edition-published.html)留言讨论。

7 欢迎提交patch

