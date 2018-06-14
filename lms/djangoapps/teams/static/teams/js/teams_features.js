/* Javascript for StudioView. */
(function(define) {
    'use strict';

    var xblock;
    var teams;

    function createRocketChatDiscussion(urlRocketChat){


        var iframe = $('<iframe>', {
            src: urlRocketChat,
            id:  "rocketChatXblock",
            style: "width: 100%; border: none;",
            scrolling: 'no'
            });

        iframe.load(function() {
            $(this).height( $(this).contents().find("body").height() );
        });

        $(".discussion-module").hide();
        if ($("div.discussion-module")[0] && !$(".page-content-main").find("#rocketChatXblock")[0]){
            $(".team-profile").find(".page-content-main").append(iframe);
        }else if ($(".page-content-main").find("#rocketChatXblock")[0]){
            $("#rocketChatXblock").attr("src", urlRocketChat)
        }
        xblock = iframe;
    };

    function actionsButtons(urlRocketChat){
        $( ".join-team .action" ).unbind().click(function() {
            createRocketChatDiscussion(urlRocketChat);
        });
        $( ".create-team .action" ).unbind().click(function() {
            createRocketChatDiscussion(urlRocketChat);
        });
        $( ".action-primary" ).unbind().click(function() {
            createRocketChatDiscussion(urlRocketChat);
        });
    }

    function loadUserTeam(options){
        var data = {"course_id": options.courseID, "username": options.userInfo.username}
        $.ajax({
            url: options.teamsUrl,
            data: data,
            success: function(data){
                teams = data;
            }
        });
    }

    function removeBrowseTab(teams){
        if (teams.count == 1){
            $("#tab-1").remove();
            $("#tabpanel-browse").remove();
            $("#tab-0").addClass("is-active");
            $("#tabpanel-my-teams").removeClass("is-hidden");
        }
    }

    define(['jquery'],

        function($) {

            return function(options){
                var urlRocketChat = "/xblock/"+options.rocketChatLocator;
                teams = options.userInfo.teams;

                $(window).load(function() {

                    $(".discussion-module").hide();

                    createRocketChatDiscussion(urlRocketChat);
                    actionsButtons(urlRocketChat);
                    removeBrowseTab(teams);

                    var targetNode = $(".view-in-course")[0];

                    // Options for the observer (which mutations to observe)
                    var config = {subtree : true, attributes: true}

                    // Callback function to execute when mutations are observed
                    function fnHandler () {
                        if ($("div.discussion-module")[0] && !$(".page-content-main").find("#rocketChatXblock")[0]){
                            $(".discussion-module").hide();
                            $(".team-profile").find(".page-content-main").append(xblock);
                        }
                        loadUserTeam(options);
                        actionsButtons(urlRocketChat);
                        removeBrowseTab(teams);
                    }
                    // Create an observer instance linked to the callback function
                    var observer = new MutationObserver(fnHandler);

                    // Start observing the target node for configured mutations
                    observer.observe(targetNode, config);

                });

            };
        });

}).call(this, define || RequireJS.define);
