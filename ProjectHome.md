Micolog2是从Micolog 0.74版改的一个GAE博客应用。解决的是我自己在使用中碰到的各种可用性、易用性问题。

---


## Demo url ##
http://micolog2.rexzhao.com/

## 版本号 ##
正式版的版本号格式为 年.月.日

## 关于主题 ##
Micolog的主题和Micolog2是通用的 :)

不过如果您想拥有更好的体验，我建议做如下更改：

1 如果comments.html里面有{% entry.comments.count %}的话，替换为{% entry.commentcount %} 这可以减少很多关于留言的查询。

2 可以把文章阅读次数在主题里面去掉，因为缓存页面的关系，不会每有人读一次，就会更新页面——这样太浪费了。

## 使用时需要留意的问题 ##
缓存不要经常刷新，否则data write operation会很多。现在缓存会自动刷新需要刷新的部分，没有特殊情况不需要手动刷新。

## 如何收到及时的更新 ##

请订阅下面Feed之中的任何一个即可：

http://feeds2.feedburner.com/Micolog2

http://feeds2.feedburner.com/rexzhao

## 近日更新缓慢的说明 ##
因为临近毕业，所以最近没有时间更新代码，还请大家谅解。

## 联系与了解作者 ##
作者的个人网站为 http://blog.rexzhao.com