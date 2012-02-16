jQuery(document).ready(
    function(){

loadjs=false;
adjust_captcha_area($("#check_type").val());

commentuser=$.cookie('comment_user');
if (commentuser)
{
 //[user,email,url]=commentuser.split('#@#');
 data=commentuser.split('#@#');
 $('#author').val(data[0]);
 $('#email').val(data[1]);
 $('#url').val(data[2]);
};

$('#commentform').ajaxForm({
        type:'post',
        dataType:  'json',
        beforeSubmit:function(formData,jqForm,options){
               var form = jqForm[0];
               if ($("#check_type").val() == 4){
                  cpcresp = Recaptcha.get_response();
                  cpcchlg = Recaptcha.get_challenge();
                  $("#checkret").val(cpcresp);
                  $("#challenge").val(cpcchlg);
               }
               if (form.author)
               {
                     if (!form.author.value)
                     {
                      showinfo('Please input your name');
                      form.author.focus();
                      return false;
                     }
                     if (!form.email.value)
                     {
                        showinfo('Please input your email');
                        form.email.focus();
                        return false;	
                     }
                     str=$.trim(form.email.value);
                     var reg = /^([A-Za-z0-9_\-\.])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
                     if(!reg.test(str)) {showinfo('请输入正确的邮件地址');form.email.focus();return false;}
               }
                if($('#checkarea').css('display')=='block')
                               {
                               if ($("#check_type").val() != 0){
                                 if(!form.checkret.value)
                                 {
                                   alert('Please input the CAPTCHA');
                                   form.checkret.focus();
                                   return false;
                                 }
                                }
                               }

                 if (!form.comment.value)
                 {
                    showinfo('Please input your comment');
                    form.comment.focus();
                    return false;
                 }

                 $('#s_msg').text('Posting comment...').show();
                 $("#submit").attr('disabled',true);

                 return true;

            },
        success:function(data){
            $("#submit").attr('disabled',false);
              if (data[0])
              {
                add_comment(data[1]);

                $('#s_msg').text('Comment successfully posted');
                $('#commentcount').text(parseInt($("#commentcount").text())+1);
                $('#comment').val('');
                if($('#checkarea').css('display')=='block')
                {
                    if($("#check_type").val()>0)
                    {
                        reloadCheckImage();
                    }
                }
                if($("#check_type").val()>0){
                  $('#checkret').val('');
                }
                location="#comments";
              }
              else
              {  
                 if (data[1]==-102){
                    showinfo('Wrong CAPTCHA');
                    reloadCheckImage();
                 }
                 $('#s_msg').text('Posting comment failed');
                 $('#checkret').focus();

              }
            }
        });
    }
)
function adjust_captcha_area(type)
{
    if (type==0)
    {
        $('#checkarea').html('');
        $('#checkarea').hide();
    }
    if (type==1)
    {
    }
    else if(type==2)
    {
        $('#check').html('');
    }
    else if (type==4)
    {
        $('#check').html('<script type="text/javascript" src="http://www.google.com/recaptcha/api/js/recaptcha_ajax.js"></script><div id="recaptcha_div"></div>');
    }
    $('#checkarea').show();
}

function showCheckImage()
{
    type = $("#check_type").val();
    if (type == 0)
        return;
    if (type == 1){
        $('#check').load('/checkcode/');
    }
    if (type == 2){
        if ($('#check').html() == '')
          $('#check').html('<img id="checkimg" src="/checkimg/" />');
        else
          $('#checkimg').attr('src', $('#checkimg').attr('src') + "?");
    }
    if (type == 4){
        if (Recaptcha.get_response() == null){
            $("#checkret").hide();
            Recaptcha.create("6Leox8YSAAAAAJFhGd5HSQn9sjEGkKJuqHiz99JJ","recaptcha_div",{theme:"clean",callback: Recaptcha.focus_response_field});
        }
        else
            Recaptcha.reload();
    }
}

function reloadCheckImage()
{
    type = $("#check_type").val();
    if (type == 0)
        return;
    if (type == 1){
        $('#check').load('/checkcode/');
    }
    if (type == 2){
        $('checkimg').src += "?"
    }
    if (type == 4){
        Recaptcha.reload();
    }
}

function showinfo(msg)
{
  alert(msg);
}
function add_comment(msg)
{
  comment=$(msg)
  if (!loadjs)
  {
  	//$("#thecomments").prepend(comment).show();
  	$("#thecomments").append(comment).show();
  	$.getScript("http://dev.jquery.com/view/trunk/plugins/color/jquery.color.js", function(){
  		 comment.animate( { backgroundColor: '#fbc7c7' }, "slow")
					.animate( { backgroundColor: 'white' }, "slow")
					loadjs=true;
				});
  }else
  {
  	//$("#thecomments").prepend(comment);
  	$("#thecomments").append(comment).show();
  	  comment.animate( { backgroundColor: '#fbc7c7' }, "slow")
					.animate( { backgroundColor: 'white' }, "slow")

  }
}

function quote(name,id,commid){
    var quoteMsg=document.getElementById(id).innerHTML;
    document.getElementById("comment").value='<a href=\"#comment-'+commid+'\">@'+name+'<\/a><blockquote>'+quoteMsg+'</blockquote>'+'\n';
    return true;
}

function backcomment(author,id){
    backdb=document.getElementById('comment');
    backdb.focus();
    backdb.value=backdb.value+'<a href=\"#comment-'+id+'\">@'+author+'<\/a>'+'\n';
    return false;
}