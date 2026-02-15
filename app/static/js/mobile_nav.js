
document.addEventListener("DOMContentLoaded", function () {
    // Only run if sidebar exists
    const navSidebar = document.querySelector('ul.nav-sidebar');
    if (!navSidebar) return;

    // Check if duplicate
    if (document.getElementById('mobile-console-menu')) return;

    const links = [
        { name: "ダッシュボード", url: "/console/" },
        { name: "アカウント連携", url: "/console/accounts/" },
        { name: "権限チェック", url: "/console/permissions/" },
        { name: "投稿インポート", url: "/social/post-import/" },
        { name: "投稿同期", url: "/social/post-sync/" },
        { name: "Webhook 受信テスト", url: "/console/webhook-test/" },
        { name: "Webhook イベント一覧", url: "/console/webhook-events/" },
        { name: "Webhook 設定", url: "/console/webhook/setup/" },
        { name: "セットアップ", url: "/console/setup/" },
        { name: "テンプレ一覧", url: "/console/templates/" },
        { name: "テンプレ新規", url: "/console/templates/new/" },
        { name: "テンプレ書出し", url: "/console/templates/export/" },
        { name: "テンプレ読込", url: "/console/templates/import/" },
        { name: "バズ投稿取得", url: "/console/buzz-search/" },
        { name: "急成長ランキング", url: "/console/buzz-growth-ranking/" },
        { name: "一括巡回", url: "/console/buzz-keyword-scan/" },
        { name: "トレンド分析", url: "/console/buzz-trends/" },
        { name: "統合ガイド", url: "/console/help/" },
        { name: "ログ", url: "/console/logs/" },
        { name: "接続テスト", url: "/console/connection-test/" },
    ];

    const newMenuHtml = `
        <li class="nav-item has-treeview" id="mobile-console-menu">
            <a href="#" class="nav-link">
                <i class="nav-icon fas fa-cogs"></i>
                <p>
                    コンソールメニュー
                    <i class="right fas fa-angle-left"></i>
                </p>
            </a>
            <ul class="nav nav-treeview" style="display: none;">
                ${links.map(link => `
                    <li class="nav-item">
                        <a href="${link.url}" class="nav-link">
                            <i class="far fa-circle nav-icon"></i>
                            <p>${link.name}</p>
                        </a>
                    </li>
                `).join('')}
            </ul>
        </li>
    `;

    navSidebar.insertAdjacentHTML('beforeend', newMenuHtml);

    // Use jQuery for animation if available (Jazzmin uses AdminLTE which uses jQuery)
    if (window.jQuery) {
        const $ = window.jQuery;
        const $menu = $('#mobile-console-menu');
        const $link = $menu.find('> a');
        const $treeview = $menu.find('> .nav-treeview');
        const $icon = $link.find('.right');

        $link.on('click', function (e) {
            // Stop propagation to prevent AdminLTE's default handler from interfering
            // (This fixes the "opens then immediately closes" issue)
            e.preventDefault();
            e.stopPropagation();

            $treeview.slideToggle(300, function () {
                // Animation complete
                if ($treeview.is(':visible')) {
                    $menu.addClass('menu-open');
                    $icon.removeClass('fa-angle-left').addClass('fa-angle-down');
                } else {
                    $menu.removeClass('menu-open');
                    $icon.removeClass('fa-angle-down').addClass('fa-angle-left');
                }
            });
        });
    } else {
        // Fallback if no jQuery (unlikely in Jazzmin)
        const toggleLink = document.querySelector('#mobile-console-menu > a.nav-link');
        if (toggleLink) {
            toggleLink.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation(); // Try to stop propagation here too

                const parentLi = this.parentElement;
                const ul = parentLi.querySelector('ul');
                const icon = this.querySelector('.right');

                const isOpen = parentLi.classList.contains('menu-open');

                if (isOpen) {
                    ul.style.display = 'none';
                    parentLi.classList.remove('menu-open');
                    if (icon) {
                        icon.classList.remove('fa-angle-down');
                        icon.classList.add('fa-angle-left');
                    }
                } else {
                    ul.style.display = 'block';
                    parentLi.classList.add('menu-open');
                    if (icon) {
                        icon.classList.remove('fa-angle-left');
                        icon.classList.add('fa-angle-down');
                    }
                }
            });
        }
    }
});
