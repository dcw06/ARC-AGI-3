"use strict";

(() => {
  const cards = [...document.querySelectorAll(".card")];
  const dialog = document.getElementById("board-dialog");
  const enlarged = document.getElementById("dialog-image");
  const previous = document.getElementById("previous-board");
  const next = document.getElementById("next-board");
  let selected = 0;
  let opener;

  function showCoordinates(event, image, output) {
    const rect = image.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = Math.max(0, Math.min(63, Math.floor((event.clientX - rect.left) * 64 / rect.width)));
    const y = Math.max(0, Math.min(63, Math.floor((event.clientY - rect.top) * 64 / rect.height)));
    output.textContent = `x ${x} · y ${y}`;
  }

  function renderBoard(index) {
    selected = index;
    const card = cards[selected];
    const image = card.querySelector("img");
    enlarged.src = image.getAttribute("src");
    enlarged.alt = image.alt;
    document.getElementById("dialog-title").textContent = `${card.dataset.game} / Level 1`;
    document.getElementById("dialog-case").textContent = `${card.dataset.case} · ${card.dataset.gameId}`;
    document.getElementById("dialog-position").textContent = `${selected + 1} / ${cards.length}`;
    document.getElementById("dialog-coordinates").textContent = "x — · y —";
    const download = document.getElementById("dialog-download");
    download.href = image.getAttribute("src");
    download.download = `${card.dataset.game}-level-1.png`;
    previous.disabled = selected === 0;
    next.disabled = selected === cards.length - 1;
  }

  cards.forEach((card, index) => {
    const image = card.querySelector("img");
    image.addEventListener("pointermove", event => showCoordinates(event, image, card.querySelector("output")));
    image.addEventListener("pointerleave", () => { card.querySelector("output").textContent = "x — · y —"; });
    card.querySelector(".board-button").addEventListener("click", event => {
      opener = event.currentTarget;
      renderBoard(index);
      dialog.showModal();
      document.getElementById("close-dialog").focus();
    });
  });
  enlarged.addEventListener("pointermove", event => showCoordinates(event, enlarged, document.getElementById("dialog-coordinates")));
  enlarged.addEventListener("pointerdown", event => showCoordinates(event, enlarged, document.getElementById("dialog-coordinates")));
  previous.addEventListener("click", () => { if (selected > 0) renderBoard(selected - 1); });
  next.addEventListener("click", () => { if (selected < cards.length - 1) renderBoard(selected + 1); });
  document.getElementById("close-dialog").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => opener?.focus());
  dialog.addEventListener("keydown", event => {
    if (event.key === "ArrowLeft" && selected > 0) { event.preventDefault(); renderBoard(selected - 1); }
    if (event.key === "ArrowRight" && selected < cards.length - 1) { event.preventDefault(); renderBoard(selected + 1); }
  });
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
})();
