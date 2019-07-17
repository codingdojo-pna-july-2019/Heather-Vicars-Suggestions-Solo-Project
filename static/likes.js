$(document).ready(function(){

    showLikes();

    function showLikes(){
        $.ajax({
            url: '/showLikes_async',
            method: 'GET',
        }).done(function(response){
            $('#jslikeslist').html(response);
        })
    }; 

});

