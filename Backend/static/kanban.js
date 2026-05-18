(function () {
  const board = document.querySelector('.kanban');
  if (!board) return;
  const url = board.dataset.statusUrl;
  let dragged = null;

  board.querySelectorAll('.kanban-card').forEach((card) => {
    card.addEventListener('dragstart', () => {
      dragged = card;
      card.classList.add('dragging');
    });
    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      dragged = null;
    });
  });

  board.querySelectorAll('.kanban-drop').forEach((zone) => {
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', async (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      if (!dragged) return;
      const col = zone.closest('.kanban-col');
      const status = col.dataset.status;
      zone.appendChild(dragged);
      const taskId = dragged.dataset.id;
      await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': typeof csrfToken === 'function' ? csrfToken() : '',
        },
        body: JSON.stringify({ task_id: parseInt(taskId, 10), status }),
      });
    });
  });
})();
