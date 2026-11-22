// Jellyfin-refina Global JS

// Gerenciador do Navegador de Pastas do Servidor (Explorador Modal)
let currentInputTargetId = null;

function openDirectoryBrowser(targetInputId) {
  currentInputTargetId = targetInputId;
  const modal = document.getElementById('dirBrowserModal');
  if (modal) {
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    const existingVal = document.getElementById(targetInputId).value.trim();
    loadDirectoryPath(existingVal || '/media');
  }
}

function closeDirectoryBrowser() {
  const modal = document.getElementById('dirBrowserModal');
  if (modal) {
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  }
}

async function loadDirectoryPath(path) {
  const listEl = document.getElementById('browserFolderList');
  const currentPathEl = document.getElementById('browserCurrentPath');
  const shortcutsEl = document.getElementById('browserShortcuts');
  const parentBtn = document.getElementById('browserParentBtn');

  listEl.innerHTML = '<div class="p-6 text-center text-gray-400"><i class="fas fa-spinner fa-spin mr-2"></i>Carregando diretórios...</div>';

  try {
    const res = await fetch(`/api/fs/browse?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error('Falha ao listar diretório');
    const data = await res.json();

    currentPathEl.textContent = data.current_path;
    currentPathEl.setAttribute('data-path', data.current_path);

    // Configura botão de subir nível
    if (data.parent_path) {
      parentBtn.disabled = false;
      parentBtn.onclick = () => loadDirectoryPath(data.parent_path);
      parentBtn.classList.remove('opacity-40', 'cursor-not-allowed');
    } else {
      parentBtn.disabled = true;
      parentBtn.classList.add('opacity-40', 'cursor-not-allowed');
    }

    // Atalhos
    if (shortcutsEl && data.shortcuts) {
      shortcutsEl.innerHTML = '';
      data.shortcuts.forEach(sc => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'px-2.5 py-1 text-xs font-medium rounded bg-gray-800 hover:bg-indigo-600 text-gray-200 hover:text-white transition';
        btn.textContent = sc.name;
        btn.onclick = () => loadDirectoryPath(sc.path);
        shortcutsEl.appendChild(btn);
      });
    }

    // Pastas
    listEl.innerHTML = '';
    if (data.folders.length === 0) {
      listEl.innerHTML = '<div class="p-6 text-center text-gray-500">Nenhuma subpasta acessível encontrada neste local.</div>';
    } else {
      data.folders.forEach(folder => {
        const item = document.createElement('div');
        item.className = 'flex items-center justify-between p-3 rounded-lg hover:bg-gray-800/80 cursor-pointer border border-transparent hover:border-gray-700 transition group';
        item.innerHTML = `
          <div class="flex items-center space-x-3 truncate">
            <i class="fas fa-folder text-amber-400 text-lg group-hover:scale-110 transition-transform"></i>
            <span class="text-gray-200 text-sm font-medium truncate">${folder.name}</span>
          </div>
          <button type="button" class="text-xs px-2.5 py-1 bg-gray-700 hover:bg-indigo-600 rounded text-gray-300 hover:text-white transition">
            Abrir
          </button>
        `;
        item.onclick = () => loadDirectoryPath(folder.path);
        listEl.appendChild(item);
      });
    }
  } catch (err) {
    listEl.innerHTML = `<div class="p-6 text-center text-red-400"><i class="fas fa-exclamation-triangle mr-2"></i>Erro ao carregar pasta: ${err.message}</div>`;
  }
}

function selectCurrentFolder() {
  const currentPathEl = document.getElementById('browserCurrentPath');
  const selectedPath = currentPathEl.getAttribute('data-path');
  if (currentInputTargetId && selectedPath) {
    const input = document.getElementById(currentInputTargetId);
    if (input) {
      input.value = selectedPath;
    }
  }
  closeDirectoryBrowser();
}

// Filtro instantâneo no cliente para telas de catálogo
function setupInstantSearch(inputId, cardSelector) {
  const input = document.getElementById(inputId);
  if (!input) return;

  input.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase().trim();
    const cards = document.querySelectorAll(cardSelector);

    cards.forEach(card => {
      const title = (card.getAttribute('data-title') || '').toLowerCase();
      const meta = (card.getAttribute('data-meta') || '').toLowerCase();
      if (!term || title.includes(term) || meta.includes(term)) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });
  });
}
