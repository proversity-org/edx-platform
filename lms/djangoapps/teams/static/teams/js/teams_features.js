/* Javascript for StudioView. */
(function(define) {
    'use strict';

    var xblock;

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
    };

    function loadUserTeam(options){
        var data = {"course_id": options.courseID, "username": options.userInfo.username}
        $.ajax({
            url: options.teamsUrl,
            data: data,
            success: function(data){
                if(data.count == 1){
                    removeBrowseTab();
                }
            }
        });
    };

    function removeBrowseTab(){
        $("#tab-1").remove();
        $("#tabpanel-browse").remove();
        $("#tab-0").addClass("is-active");
        $("#tabpanel-my-teams").removeClass("is-hidden");
    };

    function removeBrowseAndButtons(staff, teamsLocked, options){
        if (teamsLocked && !staff){
            // Remove browse
            removeBrowseTab();
            // remove join and leave button
            $(".join-team .action-primary").remove();
            $(".page-content-secondary .leave-team").remove();

        }else if(!staff){
            loadUserTeam(options);
        };
    };

    function buttonAddMembers(staff, url){
        var button = $("<button class='btn btn-secondary'>Add Members</button>");
        var input = $("<input type='file' name='fileUpload' style='display: none;'accept='text/csv'/>")
        if(!$(".page-header-secondary").children()[0] && staff){
            $(".page-header-secondary").append(input);
            $(".page-header-secondary").append(button);

            input.fileupload({
                url: url,
                done:function(e, data){
                    $(".page-header-secondary").empty();
                    var errors = data.result.errors;
                    var success = data.result.success;
                    var container = $("<div id='result' title='Result'></div>");
                    var list = $("<ul></ul>");

                    for (var key in errors){
                        var item = $("<li class='errors'>Error in "+key+" = "+errors[key]+"</li>");
                        list.append(item);
                    };

                    container.append(list);
                    var list = $("<ul></ul>");

                    for (var key in success){
                        var item = $("<li class='success'>"+success[key]+"</li>");
                        list.append(item);
                    };

                    container.append(list);
                    container.dialog();
                },
                fail: function(e, data){
                    $(".page-header-secondary").empty();
                    var container = $("<div title='Results'>"+data.errorThrown+"</div>");
                    container.dialog();
                }
            });

            button.click(function(){
                input.click();
            });
        }
    }

    function loadjs(url) {
        $('<script>')
            .attr('type', 'text/javascript')
            .attr('src', url)
            .appendTo("body");
    }

    define(['jquery'],

        function($) {

            loadjs('/static/js/vendor/jQuery-File-Upload/js/vendor/jquery.ui.widget.js');
            loadjs('/static/js/vendor/jQuery-File-Upload/js/jquery.fileupload.js');
            loadjs('/static/js/vendor/jquery-ui.min.js');

            return function(options){
                var urlRocketChat = "/xblock/"+options.rocketChatLocator;
                var urlApiCreateTeams = options.teamsCreateUrl;
                var staff = options.userInfo.staff;
                var teamsLocked = JSON.parse(options.teamsLocked);

                $(window).load(function() {

                    $(".discussion-module").hide();

                    createRocketChatDiscussion(urlRocketChat);
                    actionsButtons(urlRocketChat);
                    buttonAddMembers(staff, urlApiCreateTeams);
                    removeBrowseAndButtons(staff, teamsLocked, options);

                    var targetNode = $(".view-in-course")[0];

                    // Options for the observer (which mutations to observe)
                    var config = {subtree : true, attributes: true}

                    // Callback function to execute when mutations are observed
                    function fnHandler () {
                        if ($("div.discussion-module")[0] && !$(".page-content-main").find("#rocketChatXblock")[0]){
                            $(".discussion-module").hide();
                            $(".team-profile").find(".page-content-main").append(xblock);
                        }
                        actionsButtons(urlRocketChat);
                        buttonAddMembers(staff, urlApiCreateTeams);
                        removeBrowseAndButtons(staff, teamsLocked, options);
                    }
                    // Create an observer instance linked to the callback function
                    var observer = new MutationObserver(fnHandler);

                    // Start observing the target node for configured mutations
                    observer.observe(targetNode, config);

                });

            };
        });

}).call(this, define || RequireJS.define);
