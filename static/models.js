let currentModelId = localStorage.getItem('activeModelId') || null;
let modelModalMode = 'create'; // 'create' | 'edit'
let editingModelId = null;

function loadModels() {
    showLoader('Загрузка моделей...');
    $.getJSON('/api/models', function (data) {
        const list = $('#models-list');
        list.empty();

        const items = (data && data.items) ? data.items : (Array.isArray(data) ? data : []);
        if (!items.length) {
            list.append('<li class="text-gray-500 text-center py-1 text-xs">Нет моделей</li>');
            hideLoader();
            return;
        }

        items.forEach(model => {
            const id = model._id || model.id;
            const nameRaw = model.title || model.name || model.model || 'Без названия';
            const name = String(nameRaw);
            const prompt = String(model.prompt || '');

            const isActiveFromServer = !!(model.is_active || model.active);
            const isActive = currentModelId
                ? (id === currentModelId)
                : isActiveFromServer;

            if (isActive && !currentModelId) {
                currentModelId = id;
                localStorage.setItem('activeModelId', id);
            }

            const safeTitle = $('<div>')
                .text(name.substring(0, 25) + (name.length > 25 ? '…' : ''))
                .html();

            list.append(`
                <li class="chat-item group flex items-center justify-between ${isActive ? 'active' : ''}"
                    data-model-id="${id}">
                    <button class="flex-1 text-left px-1.5 py-1 truncate text-xs"
                            onclick="activateModel('${id}', this)">
                        ${safeTitle}
                    </button>
                    <div class="flex items-center gap-1">
                        <span class="model-active-label text-[10px] text-green-600 ${isActive ? '' : 'hidden'}">
                            active
                        </span>
                        <button class="delete-btn text-gray-400 hover:text-sky-600 p-0.5"
                                title="Редактировать"
                                onclick="editModel('${id}')">
                            <i class="fas fa-pen text-[10px]"></i>
                        </button>
                        <button class="delete-btn text-gray-400 hover:text-red-500 p-0.5"
                                title="Удалить"
                                onclick="deleteModel('${id}', this)">
                            <i class="fas fa-trash-alt text-[10px]"></i>
                        </button>
                    </div>
                </li>
            `);
        });

        hideLoader();
    }).fail(() => {
        hideLoader();
        showError('Ошибка загрузки моделей');
    });
}

function openModelModal(mode, data = null) {
    console.log('openModelModal', mode, data);
    modelModalMode = mode;
    editingModelId = data && data.id ? data.id : null;

    const $modal = $('#model-modal');
    const $title = $('#model-modal-title');
    const $name = $('#model-name-input');
    const $prompt = $('#model-prompt-input');
    const $useKb = $('#model-use-kb-input');
    const $toggle = $('#model-use-kb-toggle');

    if (mode === 'create') {
        $title.text('Новая модель');
        $name.val('');
        $prompt.val('');
        $useKb.prop('checked', false);
        $toggle.removeClass('is-on');
    } else {
        const nameVal = data && data.name ? data.name : '';
        const promptVal = data && data.prompt ? data.prompt : '';
        // пробуем разные имена полей на всякий случай
        const useKbVal = !!(
            data && (
                data.use_knowledge_base ||
                data.use_kb ||
                data.kb_enabled
            )
        );

        $title.text('Редактирование модели');
        $name.val(nameVal);
        $prompt.val(promptVal);
        $useKb.prop('checked', useKbVal);
        if (useKbVal) {
            $toggle.addClass('is-on');
        } else {
            $toggle.removeClass('is-on');
        }
    }

    $modal.removeClass('hidden');
    setTimeout(() => $name.trigger('focus'), 0);
}


function closeModelModal() {
    $('#model-modal').addClass('hidden');
    modelModalMode = 'create';
    editingModelId = null;
}

async function submitModelForm() {
    const name = ($('#model-name-input').val() || '').trim();
    const promptText = ($('#model-prompt-input').val() || '').trim();

    if (!name) {
        showError('Введите название модели');
        return;
    }

    const useKb = $('#model-use-kb-input').is(':checked');

    const payload = {
        title: name,
        prompt: promptText,
        use_knowledge_base: useKb    // <-- boolean поле
    };

    try {
        showLoader(modelModalMode === 'create' ? 'Создаю модель...' : 'Сохраняю модель...');

        let url = '/api/models';
        let method = 'POST';

        if (modelModalMode === 'edit' && editingModelId) {
            url = `/api/models/${editingModelId}/`;
            method = 'PUT';
        }

        const res = await fetch(url, {
            method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok || data._success === false) {
            throw new Error(data.message || 'Ошибка сохранения модели');
        }

        closeModelModal();
        $('#success-text').text(
            modelModalMode === 'create' ? 'Модель создана' : 'Модель сохранена'
        );
        showSuccess();
        loadModels();
    } catch (e) {
        showError(e.message || 'Ошибка сохранения модели');
    } finally {
        hideLoader();
    }
}

function createModel() {
    openModelModal('create');
}


async function editModel(modelId) {
    try {
        showLoader('Загружаю модель...');
        let modelData = {id: modelId};

        try {
            const res = await fetch(`/api/models/${modelId}/`);
            if (res.ok) {
                const d = await res.json();
                modelData = {
                    id: modelId,
                    name: d.item.title || '',
                    prompt: d.item.prompt || '',
                    use_knowledge_base: (
                        d.item.use_knowledge_base ?? false
                    )
                };
            }
        } catch (e) {
            console.error(e);
        }
        hideLoader();
        openModelModal('edit', modelData);
    } catch (e) {
        hideLoader();
        showError('Не удалось открыть модель');
    }
}


function activateModel(modelId, btn) {
    currentModelId = modelId;
    localStorage.setItem('activeModelId', modelId);

    $('#models-list .chat-item').removeClass('active')
        .find('.model-active-label').addClass('hidden');

    const $item = $(btn).closest('.chat-item');
    $item.addClass('active').find('.model-active-label').removeClass('hidden');
}

async function deleteModel(modelId, btn) {
    if (!confirm('Удалить эту модель?')) return;

    if (btn) {
        $(btn).prop('disabled', true)
            .html('<i class="fas fa-spinner fa-spin text-[10px]"></i>');
    }

    try {
        const res = await fetch(`/api/models/${modelId}/`, {
            method: 'DELETE'
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data._success === false) {
            throw new Error(data.message || 'Не удалось удалить модель');
        }

        if (currentModelId === modelId) {
            currentModelId = null;
            localStorage.removeItem('activeModelId');
        }

        loadModels();
    } catch (e) {
        showError(e.message || 'Ошибка удаления модели');
        if (btn) {
            $(btn).prop('disabled', false)
                .html('<i class="fas fa-trash-alt text-[10px]"></i>');
        }
    }
}


loadModels();
$('#new-model-btn, #new-model-mobile').click(createModel);

// Модал модели
$('#model-modal-close, #model-modal-cancel').on('click', closeModelModal);
$('#model-modal-save').on('click', submitModelForm);

$('#model-modal').on('click', function (e) {
    if (e.target.id === 'model-modal') {
        closeModelModal();
    }
});

// toggle "Использовать базу знаний"
$('#model-use-kb-toggle').on('click', function () {
    const $chk = $('#model-use-kb-input');
    const newVal = !$chk.is(':checked');
    $chk.prop('checked', newVal);
    $(this).toggleClass('is-on', newVal);
});
