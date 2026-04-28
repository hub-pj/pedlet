document.addEventListener('DOMContentLoaded', () => {
  const inputs = document.querySelectorAll('.foto-input');
  const contador = document.getElementById('contadorFotos');

  function atualizarContador() {
    if (!contador) return;
    let total = 0;
    inputs.forEach((input) => {
      if (input.files && input.files.length > 0) total += 1;
    });
    contador.textContent = total;
  }

  inputs.forEach((input) => {
    input.addEventListener('change', () => {
      const card = input.closest('.upload-card');
      const previewImg = card.querySelector('.preview-img');
      const previewText = card.querySelector('.preview-box span');
      const file = input.files && input.files[0];

      if (!file) {
        previewImg.classList.add('d-none');
        previewImg.removeAttribute('src');
        previewText.classList.remove('d-none');
        atualizarContador();
        return;
      }

      const url = URL.createObjectURL(file);
      previewImg.src = url;
      previewImg.classList.remove('d-none');
      previewText.classList.add('d-none');
      atualizarContador();
    });
  });
});
