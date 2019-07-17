$(document).ready(function(){

    showSuggestions();

    function showSuggestions(){
        $.ajax({
            url: '/showSuggestion_async/{{session["loggedin_user"]["user_id"]}}',
            method: 'GET',
        }).done(function(response){
            $('#jssuggestionfeed').html(response);
          })
    };

    $('#submit_btn').click(function(){
        $.ajax({
            method: 'POST',
            url: '/new_suggestion',
            data: $('#suggestionForm').serialize()
        })
        .done(showSuggestionss()
        );
    });  
});