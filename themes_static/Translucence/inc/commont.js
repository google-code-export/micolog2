function backcomment(author,id,domId){

    backdb=document.getElementById(domId);

    backdb.focus();

    backdb.value=backdb.value+'<a href=\"#comment-'+id+'\">@'+author+'<\/a>'+'\n';

    return false;

}
