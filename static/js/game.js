var socket;


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

     // Next round
    socket.on('next-round', function() {
      console.log('next-round triggered');
      window.location.href = "/game";
    });

     // End game
    socket.on('end-game', function() {
      console.log('game ended');
      window.location.href = "/results";
    });

});


function sendChat() {
    console.log('sendChat() called');
    var message = $('#chatinput').val();
    if (message) {
      socket.emit('message', {'sender': config.playerName, 'message': message});
      // clear chat input
      $('#chatinput').val('');
    }
}


function sendVoteMessage() {
    console.log('sendVote() called');
    var vote = $('input[name="vote"]:checked').val();
    var message = config.playerName + " voted for " + vote;

    // Send the vote to the server
    socket.emit('message', {'sender': config.autoSendName, 'message': message}, function() {
        // Submit the form programmatically after the message is sent to the server
        $('#vote-form').submit();
    });

    // Return false to prevent the default form submission behavior while the message is being sent
    return false;
}

