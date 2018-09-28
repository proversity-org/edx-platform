(function(define) {
    'use strict';

    define(['jquery', 'js/rocket_chat/rocket_chat_navigation', 'js/rocket_chat/rocket_chat_logout'],

        function($, RocketChatNavigation, RocketChatLogout) {
            function RocketChatControls (context){
                if (context.staff){
                    new RocketChatNavigation(context);
                }
                new RocketChatLogout(context);
            };

            return RocketChatControls;
        });
}).call(this, define || RequireJS.define);
