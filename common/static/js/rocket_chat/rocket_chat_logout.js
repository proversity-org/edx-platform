(function(define) {
    'use strict';

    define(['jquery'],
    function($) {
        return function(options){
            var urlLogout = options.url_logout;
            var beacon_rc = localStorage.getItem("beacon_rc");
            var beacon = options.beacon_rc;

            if (beacon_rc != null && beacon_rc != beacon) {
                    var data = {"key": beacon_rc};
                    $.ajax({
                        type: "GET",
                        url: urlLogout,
                        data: {"beacon_rc": beacon_rc},
                    });
                    localStorage.setItem("beacon_rc", beacon);
                } else {
                    localStorage.setItem("beacon_rc", beacon);
                }
        };
    });
}).call(this, define || RequireJS.define);
