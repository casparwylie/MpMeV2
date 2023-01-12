eel.expose(jsprint);
function jsprint(message, mood='normal') {
  const messageRow = document.createElement('div');
  messageRow.className = 'informer-message ' + mood;
  messageRow.innerHTML = message;
  informer.appendChild(messageRow);
  setTimeout(function(){messageRow.remove()}, 4000);
}


for (element of document.getElementsByClassName("closer")) {
  element.addEventListener('click', () => {
    document.getElementById(element.getAttribute('close')).style = 'display: none';
  })
}
