const modal = document.getElementById("modal");
const yesButtons = [
  document.getElementById("yesBtn"),
  document.getElementById("alsoYesBtn"),
  document.getElementById("finalYes"),
];
const closeModal = document.getElementById("closeModal");

function showerHearts() {
  const hearts = ["<3", "<3", "<3", "<3", "<3"];
  for (let i = 0; i < 24; i += 1) {
    const heart = document.createElement("span");
    heart.className = "heart";
    heart.textContent = hearts[Math.floor(Math.random() * hearts.length)];
    heart.style.left = `${Math.random() * 100}vw`;
    heart.style.animationDelay = `${Math.random()}s`;
    document.body.appendChild(heart);
    setTimeout(() => heart.remove(), 4500);
  }
}

function openModal() {
  modal.classList.add("show");
  showerHearts();
}

function close() {
  modal.classList.remove("show");
}

yesButtons.forEach((btn) => btn.addEventListener("click", openModal));
closeModal.addEventListener("click", close);
modal.addEventListener("click", (event) => {
  if (event.target === modal) close();
});
