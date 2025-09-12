let currentChatId = null;
let availableFiles = [];

function showLoader(text = 'Загрузка...') {
    $('#loader-text').text(text);
    $('#loader').removeClass('hidden');
}

function hideLoader() {
    $('#loader').addClass('hidden');
}

function appendMessage(role, text) {
    const box = $('#chat-box');
    const bubbleClass = role === 'user'
        ? 'bg-green-100 text-gray-900 self-end'
        : 'bg-gray-100 text-gray-800 self-start';
    box.append(`<div class="max-w-[80%] px-3 py-1.5 rounded-lg ${bubbleClass} whitespace-pre-wrap text-sm">${text}</div>`);
    box.scrollTop(box[0].scrollHeight);
}

function loadChatHistory() {
    showLoader('Загрузка истории...');
    $.getJSON('/api/chats', function (data) {
        const chatList = $('#chat-list');
        chatList.empty();

        const items = data.items;
        if (items.length === 0) {
            chatList.append('<li class="text-gray-500 text-center py-1 text-xs">Нет истории чатов</li>');
        } else {
            items.forEach(chat => {
                chatList.append(`
                        <li class="group flex items-center justify-between hover:bg-gray-100 rounded">
                            <button class="flex-1 text-left px-1.5 py-0.5 truncate text-xs" onclick="viewChat('${chat._id}')">
                                ${$('<div>').text(chat.prompt.substring(0, 25) + (chat.prompt.length > 25 ? '...' : '')).html()}
                            </button>
                            <button
                                class="delete-btn p-0.5 text-gray-400 hover:text-red-500 group-hover:visible"
                                onclick="deleteChat('${chat._id}', this)"
                            >
                                <i class="fas fa-trash-alt text-[10px]"></i>
                            </button>
                        </li>
                    `);
            });
        }
        hideLoader();
    }).fail(() => {
        alert('Ошибка загрузки истории');
        hideLoader();
    });
}

function loadFiles() {
    showLoader('Загрузка файлов...');
    $.getJSON('/api/files', function (data) {
        const filesList = $('#files-list');
        filesList.empty();
        availableFiles = data.items || [];

        if (availableFiles.length === 0) {
            filesList.append('<div class="text-gray-500 text-center py-1 text-xs">Нет файлов</div>');
        } else {
            availableFiles.forEach(file => {
                filesList.append(`
                        <div class="file-item flex items-center justify-between p-1.5 bg-white rounded border text-xs">
                            <span class="truncate flex-1">
                                ${$('<div>').text(file.title.substring(0, 20) + (file.title.length > 20 ? '...' : '')).html()}
                            </span>
                            <div class="flex space-x-1">
                                <button onclick="deleteFile('${file._id}', this)" class="text-gray-500 hover:text-red-500 p-0.5">
                                    <i class="fas fa-trash-alt text-[10px]"></i>
                                </button>
                            </div>
                        </div>
                    `);
            });
        }
        hideLoader();
    }).fail(() => {
        alert('Ошибка загрузки файлов');
        hideLoader();
    });
}

function deleteFile(fileId, button) {
    if (!confirm('Удалить этот файл?')) return;

    $(button).prop('disabled', true).html('<i class="fas fa-spinner fa-spin text-[10px]"></i>');

    $.ajax({
        url: `/api/files/${fileId}`,
        type: 'DELETE',
        success: function (response) {
            if (response._success) {
                loadFiles();
            } else {
                alert('Ошибка: ' + (response.message || 'Не удалось удалить файл'));
                $(button).prop('disabled', false).html('<i class="fas fa-trash-alt text-[10px]"></i>');
            }
        },
        error: function () {
            alert('Ошибка соединения');
            $(button).prop('disabled', false).html('<i class="fas fa-trash-alt text-[10px]"></i>');
        }
    });
}

function deleteChat(chatId, button) {
    if (!confirm('Удалить этот чат?')) return;

    $(button).prop('disabled', true).html('<i class="fas fa-spinner fa-spin text-[10px]"></i>');

    $.ajax({
        url: `/api/chats/${chatId}`,
        type: 'DELETE',
        success: function (response) {
            if (response._success) {
                if (currentChatId === chatId) {
                    $('#new-chat').click();
                }
                loadChatHistory();
            } else {
                alert('Ошибка: ' + (response.message || 'Не удалось удалить чат'));
                $(button).prop('disabled', false).html('<i class="fas fa-trash-alt text-[10px]"></i>');
            }
        },
        error: function () {
            alert('Ошибка соединения');
            $(button).prop('disabled', false).html('<i class="fas fa-trash-alt text-[10px]"></i>');
        }
    });
}

function viewChat(chatId) {
    showLoader('Загрузка чата...');
    $.getJSON(`/api/chats/${chatId}`, function (chat) {
        const item = chat.item;
        const box = $('#chat-box');
        box.empty();
        appendMessage('user', item.prompt);
        appendMessage('assistant', item.response);

        $('#prompt-input').prop('readonly', true);
        $('#send-btn').hide();

        currentChatId = chatId;
        hideLoader();
    }).fail(() => {
        alert('Ошибка загрузки чата');
        hideLoader();
    });
}

function uploadFiles(files) {
    if (files.length === 0) return;

    showLoader('Загрузка файлов...');
    const formData = new FormData();

    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }

    $.ajax({
        url: '/api/files',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
            if (response._success) {
                loadFiles();
            } else {
                alert('Ошибка: ' + (response.message || 'Не удалось загрузить файлы'));
            }
            hideLoader();
        },
        error: function () {
            alert('Ошибка соединения при загрузке');
            hideLoader();
        }
    });
}

$(document).ready(function () {
    loadChatHistory();
    loadFiles();

    $('#upload-file-btn').click(() => $('#file-upload-input').click());

    $('#file-upload-input').on('change', function () {
        const files = Array.from(this.files);
        if (files.length > 0) {
            uploadFiles(files);
            $(this).val('');
        }
    });

    $('#send-btn').click(async function () {
        const prompt = $('#prompt-input').val().trim();
        if (!prompt) return alert('Введите сообщение');

        appendMessage('user', prompt);
        showLoader('Думаю...');

        $('#prompt-input').val('').prop('readonly', true);
        $('#send-btn').prop('disabled', true);

        try {
            const assistantMessageId = 'assistant-' + Date.now();
            $('#chat-box').append(`
                    <div id="${assistantMessageId}" class="max-w-[80%] px-3 py-1.5 rounded-lg bg-gray-100 text-gray-800 self-start whitespace-pre-wrap text-sm"></div>
                `);
            console.log(JSON.stringify({
                prompt: prompt
            }))
            const response = await fetch('/api/response', {
                method: 'POST',
                body: JSON.stringify({
                    prompt: prompt
                })
            });

            if (!response.ok) throw new Error(`Ошибка ${response.status}`);
            if (!response.body) throw new Error('Поток не поддерживается');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = '';

            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                console.log(value)

                const chunk = decoder.decode(value, {stream: true});
                console.log(chunk)
                assistantMessage += chunk;
                $(`#${assistantMessageId}`).text(assistantMessage);
                $('#chat-box').scrollTop($('#chat-box')[0].scrollHeight);
            }

        } catch (error) {
            $('#chat-box').append(`
                    <div class="max-w-[80%] px-3 py-1.5 rounded-lg bg-red-100 text-red-800 self-start text-sm">
                        Ошибка: ${error.message}
                    </div>
                `);
        } finally {
            $('#prompt-input').prop('readonly', false);
            $('#send-btn').prop('disabled', false);
            hideLoader();
            loadChatHistory();
        }
    });

    $('#new-chat').click(function () {
        $('#prompt-input').val('').prop('readonly', false);
        $('#attached-files').empty();
        $('#chat-box').html('<div class="text-gray-400 text-sm text-center">Новый чат</div>');
        $('#send-btn').show();
        currentChatId = null;
        loadFiles();
    });
});
