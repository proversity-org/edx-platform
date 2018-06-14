/* Javascript for RocketChat- discussions */
(function(define) {
    'use strict';
    define(['jquery'],

        function($) {

            var xblock = $(".xblock-student_view-rocketc");
            var style = $("style");
            $( "body" ).empty();
            $( "body" ).append(xblock);
            $( "body" ).append(style);

        });
}).call(this, define || RequireJS.define);
