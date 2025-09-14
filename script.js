const button = document.getElementById('starter')

let i = 0

button.addEventListener('click', (e) => {
    if (i == 0) {
        i = 1
        button.innerText = "Стоп"
        button.classList.add("active")
    } else {
        i = 0
        button.innerText = "Начать игру"
        button.classList.remove("active")
    }
})