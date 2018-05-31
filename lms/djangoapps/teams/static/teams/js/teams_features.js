/* Javascript for StudioView. */
(function(define) {
    'use strict';
    define(['jquery'],

        function($) {

            var xblock = $(".xblock-student_view-rocketc");
            $(".hidden-rocket-chat").hide()

            $(window).load(function() {

                $(".discussion-module").hide();
                $(".team-profile").find(".page-content-main").append(xblock);

                var targetNode = $(".teams-content")[0];

                // Options for the observer (which mutations to observe)
                var config = {subtree : true, attributes: true}

                // Callback function to execute when mutations are observed
                function fnHandler () {
                    if($("div.discussion-module")[0] && !$(".page-content-main").find(".xblock-student_view-rocketc")[0]){
                        $(".discussion-module").hide();
                        $(".team-profile").find(".page-content-main").append(xblock);   
                    }
                }
                // Create an observer instance linked to the callback function
                var observer = new MutationObserver(fnHandler);

                // Start observing the target node for configured mutations
                observer.observe(targetNode, config);

            });

        });
}).call(this, define || RequireJS.define);
