//cookies.js

function setcookie(name,value){
var Days = 30;
var exp = new Date();
exp.setTime(exp.getTime() + Days*24*60*60*1000);
document.cookie = name + "="+ escape (value) + ";expires=" + exp.toGMTString();
}
function getcookie(name){
var arr = document.cookie.match(new RegExp("(^| )"+name+"=([^;]*)(;|$)"));
if(arr != null){return unescape(arr[2]);} else {return "";}
}
function login(){
setcookie("author",document.getElementById('author').value);
setcookie("email",document.getElementById('email').value);
setcookie("url",document.getElementById('url').value);
}
function loadcookies(){
document.getElementById("author").value = getcookie("author");
document.getElementById("email").value = getcookie("email");
document.getElementById("url").value = getcookie("url");
}

if (document.cookie != "") {loadcookies();}