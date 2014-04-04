var ws = (function($) {
    var ws =  new WebSocket('ws://' + window.location.host),
        ready = new $.Deferred();
    ws.onopen = function () {
        ready.resolve(true);
    };
    ws.onmessage = function (msg) {
        var message;
        try {
            message = JSON.parse(msg.data);
            if (message.status) {
                console.log('Current IRC connection status: ' + message.status); 
            }
        } catch (e) {
            console.log('Recieved non-JSON message');
            console.log(msg.data);
        }
    };
    function send(message) {
        ready.done(function () {
            ws.send(JSON.stringify(message));
        });
    };

    $('#login').on('submit', function (e) {
        var data = {action: 'login'};
        e.preventDefault();
        $('input', this).each(function (i, input) {
            var $input = $(input),
                name = $input.attr('name');
            if (name) {
                data[name] = $input.val() || null;
            }
        });
        send(data);
    });
    return ws;
})(jQuery);