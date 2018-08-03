/* Javascript for StudioView. */
(function(define) {
    'use strict';

    var xblock;

    /**
     * Remove old discussions and add an iframe with a new component using a url.
     * @function createReplacementComponent
     * @param  {String} replacementComponentUrl  Url for the new component .
     */
    function createReplacementComponent(replacementComponentUrl){

        if(!replacementComponentUrl){
            xblock = $("<strong><p id='replacementComponent'>The location id for this component has not been set correctly. Please contact support.</p></strong>");
        }else{
            var iframe = $('<iframe>', {
                src: replacementComponentUrl,
                id:  "replacementComponent",
                style: "width: 100%; border: none;",
                scrolling: 'no'
                });

            iframe.load(function() {
                $(this).height( $(this).contents().find("body").height() );
            });

            xblock = iframe;
        }

        $(".discussion-module").hide();
        if ($("div.discussion-module")[0] && !$(".page-content-main").find("#replacementComponent")[0]){
            $(".team-profile").find(".page-content-main").append(xblock);
        }else if ($(".page-content-main").find("#replacementComponent")[0]){
            $("#replacementComponent").attr("src", replacementComponentUrl)
        }
    };

    /**
     * Initialize events for some some buttons.
     * @function actionsButtons
     * @param  {String} replacementComponentUrl  Url for the new component .
     */
    function actionsButtons(replacementComponentUrl){
        $( ".join-team .action" ).unbind().click(function() {
            createReplacementComponent(replacementComponentUrl);
        });
        $( ".create-team .action" ).unbind().click(function() {
            createReplacementComponent(replacementComponentUrl);
        });
        $( ".action-primary" ).unbind().click(function() {
            createReplacementComponent(replacementComponentUrl);
        });
    };

    /**
     * Load the user team information to decide if remove the browse tab.
     * @function loadUserTeam
     * @param  {object} options User information.
     */
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

    /**
     * Remove browse tab.
     * @function removeBrowseTab
     */
    function removeBrowseTab(){
        $("#tab-1").remove();
        $("#tabpanel-browse").remove();
        $("#tab-0").addClass("is-active");
        $("#tabpanel-my-teams").removeClass("is-hidden");
    };

    /**
     * Remove browse and button if teams are locked or remove only browse tab if the user is a member team.
     * @function removeBrowseAndButtons
     * @param  {boolean} staff User is staff.
     * @param  {boolean} options teams are locked.
     * @param  {object} options User information.
     */
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

    /**
     * Add a button to join new users into different teams from a CVS file.
     * @function buttonAddMembers
     * @param  {boolean} staff User is staff.
     * @param  {string} url url to upload the CSV file.
     */
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

    /**
     * Append new javascript.
     * @function loadjs
     * @param  {string} url Url where js file is.
     */
    function loadjs(url) {
        $('<script>')
            .attr('type', 'text/javascript')
            .attr('src', url)
            .appendTo("body");
    }

    /**
     * Add a new member to the currently team.
     * @function addTeamMember
     * @param  {boolean} staff User is staff.
     * @param  {string} url Api url to add users.
     * @param  {object} userEnrolled An enrolled users list .
     */
    function addTeamMember(staff, url, usersEnrolled){

        if($(".page-content-secondary")[0] && staff && !$(".add-user")[0]){
            var button = $("<button class='btn btn-link'>Add User</button>");
            var container = $("<div class='add-user'></div>");
            var inputContainer = $("<div class='user-input'></div>");
            var input = $("<input list='users'placeholder='Username'><datalist id='users'></datalist><br>");
            var submit = $("<button class='btn btn-link'>Submit</button>");
            var cancel = $("<button class='btn btn-link' style='margin: 8px;'>Cancel</button>");

            for (var user in usersEnrolled) {
                var option = $("<option value="+usersEnrolled[user]+">");
                input.append(option);
            }


            inputContainer.append(input);
            inputContainer.append(submit);
            inputContainer.append(cancel);

            container.append(button);
            $(".page-content-secondary").append(container);
            container.after(inputContainer);

            inputContainer.hide();

            button.unbind().click(function(){
                inputContainer.show();
            });

            cancel.unbind().click(function(){
                inputContainer.hide();
                input.val("");
            });

            submit.unbind().click(function(){
                var username = input.val();
                var teamId = location.href.match(/([^\/]*)\/*$/)[1];
                var data = {"username": username, "team_id": teamId };
                $.ajax({
                    method: "POST",
                    url: url,
                    data: data,
                }).done(function() {
                   location.reload();
                }).fail(function(error) {
                    if( error.status == 404){
                        alert( error.statusText);
                    }else if (error.status == 400){
                        alert( error.responseJSON["user_message"]);
                    }
                });
             });
        }

    }

    define(['jquery'],

        function($) {

            loadjs('/static/js/vendor/jQuery-File-Upload/js/vendor/jquery.ui.widget.js');
            loadjs('/static/js/vendor/jQuery-File-Upload/js/jquery.fileupload.js');
            loadjs('/static/js/vendor/jquery-ui.min.js');

            return function(options){

                if(options.replacementComponentLocator){
                    var replacementComponentUrl = "/xblock/"+options.replacementComponentLocator;
                }else{
                    var replacementComponentUrl = null;
                }
                var urlApiCreateTeams = options.teamsCreateUrl;
                var staff = options.userInfo.staff;
                var teamsLocked = JSON.parse(options.teamsLocked);
                var usersEnrolled = JSON.parse(options.usersEnrolled);

                $(window).load(function() {

                    $(".discussion-module").hide();

                    createReplacementComponent(replacementComponentUrl);
                    actionsButtons(replacementComponentUrl);
                    buttonAddMembers(staff, urlApiCreateTeams);
                    removeBrowseAndButtons(staff, teamsLocked, options);
                    addTeamMember(staff, options.teamMembershipsUrl, usersEnrolled);

                    var targetNode = $(".view-in-course")[0];

                    // Options for the observer (which mutations to observe)
                    var config = {subtree : true, attributes: true}

                    // Callback function to execute when mutations are observed
                    function fnHandler () {
                        if ($("div.discussion-module")[0] && !$(".page-content-main").find("#replacementComponent")[0]){
                            $(".discussion-module").hide();
                            $(".team-profile").find(".page-content-main").append(xblock);
                        }
                        actionsButtons(replacementComponentUrl);
                        buttonAddMembers(staff, urlApiCreateTeams);
                        removeBrowseAndButtons(staff, teamsLocked, options);
                        addTeamMember(staff, options.teamMembershipsUrl, usersEnrolled);

                    }
                    // Create an observer instance linked to the callback function
                    var observer = new MutationObserver(fnHandler);

                    // Start observing the target node for configured mutations
                    observer.observe(targetNode, config);

                });

            };
        });

}).call(this, define || RequireJS.define);
