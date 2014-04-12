/*
    Handles all the communication to the server.
    Currently only uses websockets
    Should support regular ajax requests at somepoint as well
*/

var net = function(){};

// Need to keep an eye on this. if we get disconnected, we will want to indicate
// that to the client
net.socket = null;
net.connect = function(){
    // Connect to warren's home/test server
    var host = 'localhost';
//    var host = 'deadheap.dyndns.org';
    var url = 'ws://' + host + ':10001/';
    // create the socket
    if ("WebSocket" in window) {
        net.socket = new WebSocket(url);
    }
    else {
        try{
            net.socket = new MozWebSocket(url);
        }
        catch(err){
            console.log("Error making new MozWebSocket" + err);
        }
    }
    if(!net.socket){
        alert("Could not instantiate a websocket! Please make sure you "+
              "are using a non-lame browser like Chrome of Firefox."
        );
    }

    // Receiving a message from server
    net.socket.onmessage = function(event) {
        net.route(JSON.parse(event.data));
    };
};
net.send = function(msg){
    msg = JSON.stringify(msg);
    console.log(msg, net.socket);
    net.socket.send(msg);
    console.log('Sent message');
};

// *** This is all the routing code for messages from the server. This will need
//     to be moved to a more appropriate location at some point
net.route = function(msg){
    // *** Pass me the full message from the server as an object (already parsed json)
    if(msg.type == 'message'){
        // New chat message
        yo_view_model.chat_msg_from_server(msg.name, msg.text);
    }
};
