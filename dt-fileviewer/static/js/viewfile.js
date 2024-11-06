
const view_form     = document.getElementById('viewfile_form');
const cbo_textfile  = document.getElementById('cbo_text_filename');
const cbo_start_pos = document.getElementById('cbo_start_pos');
const txt_filter    = document.getElementById('filter_text');
const btn_submit    = document.getElementById('submit_button')
const log_window = document.getElementById('log_window');

const NULL_FILE     = 'not_selected'

// Initial connection
let ws_file_vw = null
let base_uri = '/ws/view/'
let uri = base_uri + cbo_textfile.value;

// if (cbo_textfile.value == NULL_FILE) {
//     console.log('No file selected, ignore request...')
//     log_window.innerHTML = ''
// } else {
//     reconnectws_file('ws://' + window.location.host + uri)
// }
reconnectws_file('ws://' + window.location.host + uri)

submit_button.addEventListener("click", (e) => {
    e.preventDefault();

    let text_file = cbo_textfile.value;
    let uri = base_uri + text_file;
    let query_string = '?start_pos='+cbo_start_pos.value;
    if (txt_filter.value.trim().length) {
        query_string += '&filter_text='+txt_filter.value.trim()
    }
    console.log('submit button clicked.  file: ' + text_file)

    reconnectws_file("ws://" + window.location.host + uri + query_string);
    // Disable submit_button
    enable_button(btn_submit, false)
  });
  

cbo_textfile.addEventListener("change", function () {
    const selected_value = this.value;

    console.log('cbo_textfile changed to ' + selected_value)
    if (selected_value == NULL_FILE) {
        enable_button(btn_submit, false);
        uri = base_uri + cbo_textfile.value;
        // Reset connection and clear window
        reconnectws_file('ws://' + window.location.host + uri);
    } else {
        enable_button(btn_submit, true);
    }
});

cbo_start_pos.addEventListener("change", function(){
    console.log('cbo_start_pos changed')
    enable_button(btn_submit, true);
});

txt_filter.addEventListener("change", function(){
    console.log('txt_filter changed')
    enable_button(btn_submit, true);
});

function enable_button(btn, state) {
    console.log('ENABLE ' + btn.id + ' ' + state)
    let cls = btn.getAttribute('class');
    console.log('- ' + cls)
    if (state == true) {
        // Enable - remove disabled attribute
        cls = cls.replace('disabled', '');
        btn.setAttribute('class', cls);
    } else {
        // Disable, add disabled attribute (if does not exist)
        if (! cls.includes('disabled')) {
            cls += ' disabled';
            btn.setAttribute('class', cls);
        }
    }
    console.log('- ' + cls)
}

function reconnectws_file(newEndpoint) {
    console.log('Reconnectws_file()');
    log_window.innerHTML = 'Attempting to connect...'
    if (newEndpoint == NULL_FILE) {
        console.log('[' + NULL_FILE + '] endpoint.  Abandon');
        ws_file_vw = null
        return;
    }
    if (ws_file_vw) {
        console.log("- readystate: " + ws_file_vw.readyState);
        if (ws_file_vw.readyState !== ws_file_vw.CLOSED) {
            console.log('- Close current connection.');
            ws_file_vw.close(3001, "- Reconnect to " + newEndpoint + " requested.");
        }
    }
    
    console.log('- Establish new ws connection: ' + newEndpoint);
    ws_file_vw = new WebSocket(newEndpoint);
    log_window.innerHTML = ''

    // ------------------------------------------------------------------------------------
    ws_file_vw.onopen = () => {
        console.log("Connected to new ws endpoint: " + newEndpoint);
        // Handle reconnection logic
    };

    // ------------------------------------------------------------------------------------
    ws_file_vw.onclose = (event) => {
        console.log("ws_log closed: " + event);
        // Implement reconnection logic if needed
        log_window.innerHTML = ''
    };

    // ------------------------------------------------------------------------------------
    ws_file_vw.onmessage = (event) => {
        console.log('ws_log onmessage ' + event.type)
        var log_window = document.getElementById('log_window')
        // Handle incoming messages
        log_window.innerHTML += event.data + "\n";
        // log_obj.scrollIntoView({ behavior: "smooth", block: "end", inline: "nearest" })
        log_window.scrollIntoView({ behavior: "smooth", block: "end" })
        log_window.scrollTop = log_window.scrollHeight;
    };

    // ------------------------------------------------------------------------------------
    ws_file_vw.onerror = (error) => {
        console.error("ws_log error: " + error.type + '\nEvent: ' + event);
    };

}
