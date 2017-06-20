/* globals _ */

(function(_) {
    'use strict';

    var Recap = (function() {


    $('#download_1').click(function(event){
        event.preventDefault();
        event.stopImmediatePropagation()
        var recap_answers;  
        var noteFormUrl;
        console.log("I was clicked")
        noteFormUrl = $('#download_1').attr('action');
        recap_answers = '<p>This is a test string.</p>';
        var csrftoken = getCookie('csrftoken');
        console.log('hi')
        $.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
        }
        });
        $.ajax({
            url: noteFormUrl,
            method: 'post',
            data: {'recap_answers': recap_answers},
            beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
          xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
        }
        }).done(function(data){
            console.log('hey')
            if (data.hasOwnProperty('error')){
                console.log("There was an error.")
            } 
            else if (data.hasOwnProperty('statusCode')){
                if (data['statusCode'] == 200) {
                    alert('The download is complete.')
                    
                }
            } else if (data['statusCode'] != 200) {
                console.log(data['statusCode']);
                console.log(data);
                alert('There was a problem and the download was not successful.')
            }
        })
    });
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }


        function RecapBlock($section) {
            this.$section = $section;
            this.$section.data('wrapper', this);
        }

        RecapBlock.prototype.onClickTitle = function() {
            var block = this.$section.find('.recap');
            XBlock.initializeBlock($(block).find('.xblock')[0]);
        };

        return RecapBlock;
    }());

    if (typeof window.setup_debug === 'undefined') {
        // eslint-disable-next-line no-unused-vars, camelcase
        window.setup_debug = function(element_id, edit_link, staff_context) {
            // stub function.
        };
    }

    _.defaults(window, {
        InstructorDashboard: {}
    });

    _.defaults(window.InstructorDashboard, {
        sections: {}
    });

    _.defaults(window.InstructorDashboard.sections, {
        Recap: Recap
    });

    this.Recap = Recap;
}).call(this, _);
