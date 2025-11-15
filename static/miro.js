function toMiroEmbedUrl(raw) {
    try {
        const u = new URL(raw);
        if (u.pathname.includes('/app/board/')) {
            u.pathname = u.pathname.replace('/app/board/', '/app/live-embed/');
            return u.href;
        }
        if (u.pathname.includes('/app/live-embed/')) {
            return u.href;
        }
        const segs = u.pathname.split('/').filter(Boolean);
        const last = segs[segs.length - 1] || '';
        u.pathname = `/app/live-embed/${last}/`;
        return u.href;
    } catch (e) {
        return raw;
    }
}

const STORAGE_KEY = 'miroBoardUrl-deskto';
const $doc = $(document);

// Кэшируем ссылки на узлы
const $overlay = $('#miro-container');
const holder = document.getElementById('miro-iframe-holder');

// Внутренние флаги состояния
// mounted: iframe уже создан (и ссылка известна)
// minimized: свернули (скрыто), но iframe и состояние сохранены
function getState() {
    return {
        mounted: $overlay.data('mounted') === true,
        minimized: $overlay.data('minimized') === true
    };
}

function setMounted(v) {
    $overlay.data('mounted', !!v);
}

function setMinimized(v) {
    $overlay.data('minimized', !!v);
}

function mountIframe(boardUrl) {
    if (!holder) return;
    holder.innerHTML = '';
    const iframe = document.createElement('iframe');
    iframe.className = 'w-full h-full';
    iframe.setAttribute('frameborder', '0');
    iframe.setAttribute('allow', 'fullscreen; clipboard-read; clipboard-write');
    iframe.src = toMiroEmbedUrl(boardUrl);
    holder.appendChild(iframe);
    setMounted(true);
}

function showOverlay() {
    $overlay.removeClass('hidden');
    setMinimized(false);
}

function hideOverlay() {
    // Полное закрытие (уходим от пользователя, но НЕ демонтируем iframe)
    $overlay.addClass('hidden');
    setMinimized(true);
}

function hardClose() {
    // Полное закрытие с размонтажем
    $overlay.addClass('hidden');
    setMinimized(false);
    setMounted(false);
    if (holder) holder.innerHTML = `
        <div class="text-center px-6 text-gray-500">
          <div class="text-3xl opacity-40 mb-3"><i class="fa-brands fa-miro"></i></div>
          <div class="text-sm text-slate-600">Вставьте ссылку на доску Miro — окно откроется здесь, во весь размер.</div>
        </div>`;
}

// Кнопка «Открыть Miro» (внизу левого сайдбара / в offcanvas — id одинаковый)
$doc.on('click', '#open-miro-desktop', function (e) {
    e.preventDefault();
    const {mounted, minimized} = getState();

    if (mounted && minimized) {
        // Уже смонтирован и свёрнут → просто показать, без перезагрузки
        showOverlay();
        return;
    }

    if (!mounted) {
        // Впервые: берём ссылку (или из localStorage)
        let boardUrl = (localStorage.getItem(STORAGE_KEY) || '').trim();
        if (!boardUrl) {
            boardUrl = prompt('Вставьте ссылку на доску Miro') || '';
            boardUrl = boardUrl.trim();
            if (!boardUrl) return; // отказ — ничего не делаем
            localStorage.setItem(STORAGE_KEY, boardUrl);
        }
        mountIframe(boardUrl);
    }

    // mounted && !minimized (уже открыто) — ничего не делаем, оно уже видно
    showOverlay();
});

// «Сменить ссылку» — не закрывая окно
$doc.on('click', '#miro-change-url', function () {
    let boardUrl = prompt('Новая ссылка на доску Miro') || '';
    boardUrl = boardUrl.trim();
    if (!boardUrl) return;
    localStorage.setItem(STORAGE_KEY, boardUrl);
    mountIframe(boardUrl);
    showOverlay();
});

// «Свернуть» — просто скрыть, оставить iframe
$doc.on('click', '#miro-minimize', function () {
    hideOverlay();
});

// «Закрыть» — полностью закрыть и очистить содержимое
$doc.on('click', '#miro-close', function () {
    hardClose();
});

// Клик по подложке — сворачиваем (мягко)
$doc.on('click', '#miro-container', function (e) {
    if (e.target && e.target.id === 'miro-container') hideOverlay();
});

// Esc — сворачиваем (мягко)
$doc.on('keydown', function (e) {
    if (e.key === 'Escape') hideOverlay();
});