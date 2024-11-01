
const URIs = ["viewfile", "configure", "system"];
const current_uri = window.location.pathname;

for (let i = 0; i < URIs.length; i++) {
    // console.log('uri: ' + URIs[i])
    let nav_link = document.getElementById(URIs[i] + "_nav");
    let nav_text = URIs[i].charAt(0).toUpperCase() + URIs[i].slice(1);
    nav_link.innerHTML = nav_text;
    if (current_uri.includes(URIs[i]) ) {
        nav_link.setAttribute("class", "nav-link active");
        nav_link.setAttribute("aria-current", "page");
    } else {
        nav_link.setAttribute("class", "nav-link");
    }
}