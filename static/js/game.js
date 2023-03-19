var socket;

function sendChat() {
    console.log('sendChat() called');
    var message = $('#chatinput').val();
    if (message) {
      socket.emit('message', {'sender': config.playerName, 'message': message});
      $('#chatinput').val('');
    }
}

$(document).ready(function() {
    // Display chat messages
    var chat_messages = config.chatMessages;
    for (var i = 0; i < chat_messages.length; i++) {
      var message = chat_messages[i];
      var sender = message['sender'];
      var text = message['message'];
      var html = '<p><strong>' + sender + ':</strong> ' + text + '</p>';
      $('#chatbox').append(html);
    }

    // Scroll to latest chat message
    $('#chatbox').scrollTop($('#chatbox').prop('scrollHeight'));

    // Connect to the WebSocket server
    socket = io.connect('http://' + document.domain + ':' + location.port);

    // Receive messages from the server
    socket.on('message', function(data) {
      console.log('Received message:', data);
      chat_messages.push(data);
      var sender = data['sender'];
      var text = data['message'];
      var html = '<p><strong>' + sender + ':</strong> ' + text + '</p>';
      $('#chatbox').append(html);
      // Scroll to latest chat message
      $('#chatbox').scrollTop($('#chatbox').prop('scrollHeight'));
    });
});
