function show_sub() {
    document.getElementById('sub_button').style.display="inline";
}
function hide_sub() {
    document.getElementById('sub_button').style.display="none";
}

function chcheck() {
    if (document.getElementById('rules').checked == true) {
	document.getElementById('sub_button').style.display="inline";
    } else {
	document.getElementById('sub_button').style.display="none";
    }
}
