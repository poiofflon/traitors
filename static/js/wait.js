var socket;


$(document).ready(function() {

    // Connect to the WebSocket server
    socket = io.connect('http://' + document.domain + ':' + location.port);

     // Game start
    socket.on('start-game', function() {
      console.log('start-game triggered');
      window.location.href = "/game";
    });


});