(function(define) {
    'use strict';
    define(['jquery', 'js/rocket_chat/rocket_chat'],
        function($, RocketChatControls) {
            return function(options) {
                var rocketChatControls = new RocketChatControls(options);
            };
        });
}).call(this, define || RequireJS.define);
