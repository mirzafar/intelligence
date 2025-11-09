/* --- GITHUB INTEGRATION START --- */
let githubToken = '';
let githubRepos = []; // массив объектов API GitHub
let githubReposFiltered = [];

function openGitHubModal() {
    githubToken = '';
    githubRepos = [];
    githubReposFiltered = [];
    $('#github-token-input').val('');
    $('#github-repo-search').val('');
    $('#github-select-all').prop('checked', false);
    $('#gh-step-repos').addClass('hidden');
    $('#gh-step-token').removeClass('hidden');
    $('#github-modal').removeClass('hidden');
    setTimeout(() => $('#github-token-input').focus(), 0);
}

function closeGitHubModal() {
    $('#github-modal').addClass('hidden');
}

function backToTokenStep() {
    $('#gh-step-repos').addClass('hidden');
    $('#gh-step-token').removeClass('hidden');
}

function ghHeaders() {
    return {
        'Accept': 'application/vnd.github+json',
        'Authorization': `token ${githubToken}`,
        'X-GitHub-Api-Version': '2022-11-28'
    };
}

// Пагинация /user/repos (до 100 на страницу)
async function fetchAllRepos() {
    const perPage = 100;
    let page = 1;
    const acc = [];
    while (true) {
        const url = `https://api.github.com/user/repos?per_page=${perPage}&page=${page}&sort=updated&affiliation=owner,collaborator,organization_member`;
        const res = await fetch(url, {headers: ghHeaders()});
        if (res.status === 401) throw new Error('UNAUTHORIZED');
        if (!res.ok) throw new Error(`GitHub API error: ${res.status}`);
        const batch = await res.json();
        acc.push(...batch);
        if (batch.length < perPage) break;
        page += 1;
        // защита от runaway
        if (page > 20) break; // 2000 репо — более чем достаточно
    }
    return acc;
}

function renderRepoList(list) {
    const $list = $('#github-repo-list');
    // сохраняем ранее выбранный path, если есть
    const prev = ($list.find('input[name="gh-repo"]:checked').data?.('full')) || '';

    $list.empty();

    if (!list || list.length === 0) {
        $list.append(`<div class="text-gray-500 text-xs py-6 text-center">Ничего не найдено</div>`);
        return;
    }

    list.forEach(repo => {
        const full = repo.full_name; // owner/name — это и есть path
        const branch = repo.default_branch || 'main';
        const cloneUrl = repo.clone_url;

        const safeFull = $('<div>').text(full).html();
        const checked = (prev && prev === full) ? 'checked' : '';

        $list.append(`
      <label class="flex items-start gap-2 p-1 rounded hover:bg-gray-100 cursor-pointer">
        <input type="radio" class="gh-repo-radio mt-1" name="gh-repo"
               data-full="${safeFull}" ${checked}>
        <div class="flex-1">
          <div class="font-medium">${safeFull}</div>
          <div class="text-[11px] text-gray-500">
            branch: ${branch} · https: ${cloneUrl}
          </div>
        </div>
      </label>
    `);
    });
}

function filterRepos() {
    const q = ($('#github-repo-search').val() || '').toLowerCase().trim();
    if (!q) {
        githubReposFiltered = githubRepos.slice();
    } else {
        githubReposFiltered = githubRepos.filter(r =>
            (r.full_name || '').toLowerCase().includes(q)
        );
    }
    renderRepoList(githubReposFiltered);
}


async function submitGitHubToken() {
    const token = ($('#github-token-input').val() || '').trim();
    if (!token) return showError('Введите токен');

    githubToken = token;

    try {
        showLoader('Проверяю токен…');
        // быстрая проверка токена
        const me = await fetch('https://api.github.com/user', {headers: ghHeaders()});
        if (me.status === 401) {
            hideLoader();
            return showError('Неверный токен GitHub');
        }
        if (!me.ok) {
            hideLoader();
            return showError('Не удалось проверить токен');
        }

        showLoader('Загружаю список репозиториев…');
        githubRepos = await fetchAllRepos();
        hideLoader();

        if (!githubRepos || githubRepos.length === 0) {
            showError('Репозитории не найдены');
            return;
        }

        $('#gh-step-token').addClass('hidden');
        $('#gh-step-repos').removeClass('hidden');

        githubReposFiltered = githubRepos.slice();
        renderRepoList(githubReposFiltered);
        setTimeout(() => $('#github-repo-search').focus(), 0);
    } catch (e) {
        hideLoader();
        if (e && e.message === 'UNAUTHORIZED') {
            showError('Неверный токен GitHub');
        } else {
            showError('Ошибка загрузки из GitHub');
            console.error(e);
        }
    }
}


async function confirmGitHubConnect() {
    if (!githubToken) return showError('Сначала введите токен');
    const pick = getSelectedRepo();
    if (!pick) return showError('Выберите репозиторий');

    try {
        showLoader('Отправляю на бэк…');
        const res = await fetch('/api/github/connect', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                token: githubToken,
                path: pick.path   // <-- одиночный path
            })
        });

        if (!res.ok) {
            const t = await res.text().catch(() => '');
            throw new Error(t || `HTTP ${res.status}`);
        }

        hideLoader();
        showSuccess();
        closeGitHubModal();
    } catch (e) {
        hideLoader();
        console.error(e);
        showError('Не удалось привязать GitHub');
    }
}

function getSelectedRepo() {
    const $sel = $('#github-repo-list .gh-repo-radio:checked');
    if ($sel.length === 0) return null;
    return {path: $sel.data('full')};
}

// Открыть модалку GitHub
$('#connect-github-btn, #connect-github-btn-mobile').click(() => openGitHubModal());

// Поиск/фильтр
$(document).on('input', '#github-repo-search', filterRepos);