
// const should_connect = document.getElementById('valid_log').textContent;
const cbo_textfile = document.getElementById('cbo_text_filename');
// const logfile_form = document.getElementById('logfile_form');

// Initial connection
let ws_log = null
let uri = '/ws/log/' + cbo_textfile.value;
reconnectws_file('ws://' + window.location.host + uri)
// let ws_log = new WebSocket("ws://" + window.location.host + "/ws/log/" + cbo_logfile.value);


cbo_textfile.addEventListener("change", function () {
    // Get the selected value
    const selected_value = this.value;
    var log_window = document.getElementById('log_window')

    // Do something with the selected value
    let uri = '/ws/log/' + selected_value;
    // Reconnect to a new endpoint
    reconnectws_file("ws://" + window.location.host + uri);
    log_window.innerHTML = "";

}
);

function reconnectws_file(newEndpoint) {
    console.log('Reconnectws_log()')
    if (newEndpoint == 'DoesNotExist') {
        console.log('[not_selected] endpoint.  Abandon')
        return
    }

    if (ws_log) {
        console.log("- readystate: " + ws_log.readyState)
        if (ws_log.readyState !== ws_log.CLOSED) {
            console.log('- Close current connection.')
            ws_log.close(3001, "- Reconnect to " + newEndpoint + " requested.");
        }
    }

    console.log('- Establish new connection: ' + newEndpoint)
    ws_log = new WebSocket(newEndpoint);

    ws_log.onopen = () => {
        console.log("ws_log connected to new endpoint: " + newEndpoint);
        // Handle reconnection logic
    };

    ws_log.onmessage = (event) => {
        console.log('ws_log onmessage ' + event.type)
        var log_window = document.getElementById('log_window')
        // Handle incoming messages
        log_window.innerHTML += event.data + "\n";
        // log_obj.scrollIntoView({ behavior: "smooth", block: "end", inline: "nearest" })
        log_window.scrollIntoView({ behavior: "smooth", block: "end" })
        log_window.scrollTop = log_window.scrollHeight;
    };

    ws_log.onerror = (error) => {
        console.error("ws_log error: " + error);
    };

    ws_log.onclose = (event) => {
        console.log("ws_log closed: " + event);
        // Implement reconnection logic if needed
    };
}
