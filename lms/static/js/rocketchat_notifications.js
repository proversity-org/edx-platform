(function(define) {
    'use strict';

    function connectWebSocket(data){

        var url = data["url_service"];
        var roomIds = data["room_ids"];
        var tab = $(".tab.rocketchat");
        tab.children().append($("<span class='rocketchat-indicator'></span>"));
        var indicator = $(".rocketchat-indicator")
        var rocketChatSocket = new WebSocket(url.replace("http", "ws")+"/websocket");
        var connectRequest = {
            "msg": "connect",
            "version": "1",
            "support": ["1"]
         }

         rocketChatSocket.onopen = function (event) {
            rocketChatSocket.send(JSON.stringify(connectRequest));

            var loginRequest = {
            "msg": "method",
            "method": "login",
            "id": "42",
            "params":[
                { "resume": data["auth_token"] }
            ]
            }
            rocketChatSocket.send(JSON.stringify(loginRequest));

            var notifyUserRequest = {
                "msg": "sub",
                "id": "unique-id",
                "name": "stream-notify-user",
                "params":[
                    data["user_id"]+"/subscriptions-changed",
                    false
                ]
            }

            rocketChatSocket.send(JSON.stringify(notifyUserRequest));
        };

        rocketChatSocket.onmessage = function (event) {

            var data = JSON.parse(event.data);
            if (data["msg"] == "ping"){
                var pong = {"msg": "pong"};
                rocketChatSocket.send(JSON.stringify(pong));
            }else if (data["msg"] == "changed"){
                try {
                    var args = data["fields"]["args"][1];

                    if(!roomIds.includes(args["rid"]) && args["unread"] > 0){
                        roomIds.push(args["rid"]);
                    }else if (args["unread"] == 0 ){
                        roomIds = roomIds.filter(item => item !== args["rid"]);
                    }
                } catch (error) {
                    console.log(error);
                }
            }

            if (roomIds.length == 0){
                indicator.css("display", "none");
            }else{
                indicator.css("display", "inline-block");
            }
        }
    }

    define(['jquery'],
     function($) {
        return function(options){
            var url_credentials = options["url_credentials"]
            var courseId = options["course_id"]
            $(document).ready(function() {
                $.ajax({
                    type: "GET",
                    url: url_credentials,
                    data: {courseId},
                    success: connectWebSocket,
                });
            });
        };
    });
}).call(this, define || RequireJS.define);
