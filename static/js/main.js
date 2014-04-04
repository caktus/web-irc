var ws = (function($) {
    var ws =  new WebSocket('ws://' + window.location.host),
        ready = new $.Deferred(),
        authenticating = false,
        currentNick = null;
    ws.onopen = function () {
        ready.resolve(true);
    };
    ws.onclose = function () {
        ready = new $.Deferred();
    };
    ws.onmessage = function (msg) {
        var message;
        try {
            message = JSON.parse(msg.data);
            if (message.status) {
                console.log('Current IRC connection status: ' + message.status);
                if (message.status === 'joined') {
                    $('#chat').prepend($('<h2>').text('Welcome to ' + message.channel));
                    $('#login').fadeOut(500, function () {
                        $('#chat').fadeIn(500);
                    });
                }
            } else if (message.message) {
                addMessage(message.nick, message.message);
            } else if (message.member) {
                if (message.action === 'add') {
                    addMember(message.member);
                } else if (message.action === 'remove') {
                    removeMember(message.member);
                }
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

    function addMessage(nick, message) {
        $('#messages').append(
            $('<div>')
                .addClass('message')
                .append($('<span>').text(nick).addClass('nick'))
                .append($('<span>').text(message).addClass('text'))
        );
    }

    function addMember(nick) {
        $('#members').append($('<div>', {id: 'm-' + nick}).text(nick).addClass('member'));
    }

    function removeMember(nick) {
        $('#m-' + nick).remove();
    }

    $('#login').on('submit', function (e) {
        var data = {action: 'login'};
        e.preventDefault();
        if (!authenticating) {
            $('input', this).each(function (i, input) {
                var $input = $(input),
                    name = $input.attr('name');
                if (name) {
                    data[name] = $input.val() || null;
                }
            });
            currentNick = data.nick || data.username;
            send(data);
            $(this).addClass('waiting');
            $(':input', this).prop('disabled', true);
            authenticating = true;
        }
    });

    $('#chat-box').on('submit', function (e) {
        var $input = $('input[name=msg]'),
            message = $input.val();
        e.preventDefault();
        if (message) {
            send({message: message});
            addMessage(currentNick, message);
            $input.val('');
        }
    });
    return ws;
})(jQuery);