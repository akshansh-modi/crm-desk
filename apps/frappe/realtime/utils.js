const { get_conf } = require("../node_utils");
const conf = get_conf();

function get_url(socket, path) {
	if (!path) {
		path = "";
	}
	// crm-desk patch, see PATCHES.md. Upstream calls back the browser's Origin, so a forged Origin
	// (plus X-Frappe-Site-Name) made socketio send its secret to, and trust, any server. Always ask
	// our own web server instead. FRAPPE_WEB_URL: for when web runs in another pod.
	let url = process.env.FRAPPE_WEB_URL || `http://127.0.0.1:${conf.webserver_port}`;
	return url + path;
}

module.exports = {
	get_url,
};
