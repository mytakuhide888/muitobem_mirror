document.addEventListener("DOMContentLoaded", function () {
    const navSidebar = document.querySelector("ul.nav-sidebar");
    if (!navSidebar || document.getElementById("console-sidebar-menu-root")) {
        return;
    }

    const currentPath = window.location.pathname.replace(/\/+$/, "/");
    const canonicalPath = currentPath.replace(/^\/admin(?=\/console\/)/, "");
    const normalize = (path) => (path || "/").replace(/\/+$/, "/");

    const groups = [
        {
            label: "共通設定",
            description: "連携と運用の基本設定",
            icon: "fas fa-sliders-h",
            items: [
                { label: "アカウント連携", url: "/console/accounts/" },
                { label: "権限チェック", url: "/console/permissions/" },
                { label: "投稿インポート", url: "/social/post-import/" },
                { label: "投稿同期", url: "/social/post-sync/" },
                { label: "Webhook受信テスト", url: "/console/webhook-test/" },
                { label: "Webhookイベント一覧", url: "/console/webhook-events/" },
                { label: "Webhook設定", url: "/console/webhook/setup/" },
                { label: "セットアップ", url: "/console/setup/" },
            ],
        },
        {
            label: "企画 / Threads分析",
            description: "企画設計とThreadsリサーチ",
            icon: "fas fa-lightbulb",
            items: [
                { label: "バズ・人気アカウントリサーチ", url: "/console/buzz-research-overview/" },
                { label: "コンセプト設計", url: "/console/concept-design/" },
                { label: "バズ投稿取得", url: "/console/buzz-search/" },
                { label: "急成長ランキング", url: "/console/buzz-growth-ranking/" },
                { label: "一括巡回", url: "/console/buzz-keyword-scan/" },
                { label: "トレンド分析", url: "/console/buzz-trends/" },
            ],
        },
        {
            label: "制作 / 投稿運用",
            description: "テンプレとSNS制作",
            icon: "fas fa-pen-ruler",
            items: [
                { label: "テンプレ一覧", url: "/console/templates/" },
                { label: "テンプレ新規", url: "/console/templates/new/" },
                { label: "テンプレ書き出し", url: "/console/templates/export/" },
                { label: "テンプレ読込", url: "/console/templates/import/" },
                { label: "投稿文AI生成", url: "/console/content-generator/" },
                { label: "予約投稿管理", url: "/console/scheduled-posts/" },
                { label: "IG投稿管理", url: "/console/ig-posts/" },
                { label: "パフォーマンス分析", url: "/console/post-analytics/" },
                { label: "タロットリール生成", url: "/console/tarot-reel/" },
            ],
        },
        {
            label: "顧客対応 / 鑑定",
            description: "DMと鑑定の運用",
            icon: "fas fa-comments",
            items: [
                { label: "DM受信管理", url: "/console/dm-inbox/" },
                { label: "AI鑑定文生成", url: "/console/appraisal-gen/" },
                { label: "自動返信設定", url: "/console/auto-reply-settings/" },
            ],
        },
        {
            label: "共通ツール",
            description: "ガイドと保守確認",
            icon: "fas fa-tools",
            items: [
                { label: "ダッシュボード", url: "/console/" },
                { label: "統合ガイド", url: "/console/help/" },
                { label: "ログ", url: "/console/logs/" },
                { label: "接続テスト", url: "/console/connection-test/" },
            ],
        },
    ];

    const style = document.createElement("style");
    style.textContent = `
        .nav-sidebar .console-menu-marker {
            letter-spacing: 0.08em;
            font-size: 0.72rem;
            color: rgba(255, 255, 255, 0.55);
            margin-top: 0.75rem;
        }
        .nav-sidebar .console-group > .nav-link {
            border-radius: 12px;
            margin: 0 0.35rem 0.3rem;
            padding: 0.8rem 0.9rem;
            background: rgba(255, 255, 255, 0.02);
            transition: background-color 0.2s ease;
        }
        .nav-sidebar .console-group > .nav-link:hover,
        .nav-sidebar .console-group.is-open > .nav-link,
        .nav-sidebar .console-group.is-active > .nav-link {
            background: rgba(255, 255, 255, 0.08);
        }
        .nav-sidebar .console-group-label {
            display: flex;
            flex-direction: column;
            gap: 0.15rem;
            min-width: 0;
        }
        .nav-sidebar .console-group-label strong,
        .nav-sidebar .console-group-label span {
            white-space: normal;
            line-height: 1.25;
        }
        .nav-sidebar .console-group-label span {
            font-size: 0.72rem;
            color: rgba(255, 255, 255, 0.62);
        }
        .nav-sidebar .console-subtree {
            display: none;
            margin: 0 0.35rem 0.55rem;
            padding: 0.25rem 0 0.35rem;
            border-left: 1px solid rgba(255, 255, 255, 0.12);
        }
        .nav-sidebar .console-group.is-open > .console-subtree {
            display: block;
        }
        .nav-sidebar .console-subtree .nav-link {
            margin-left: 0.65rem;
            border-radius: 10px;
            padding: 0.65rem 0.85rem;
            white-space: normal;
            line-height: 1.3;
        }
        .nav-sidebar .console-subtree .nav-link.active {
            background: rgba(96, 165, 250, 0.22);
            color: #fff;
        }
    `;
    document.head.appendChild(style);

    const parts = ['<li class="nav-header console-menu-marker" id="console-sidebar-menu-root">Console</li>'];

    groups.forEach((group, index) => {
        const itemsHtml = group.items.map((item) => {
            const itemPath = normalize(item.url);
            const adminItemPath = normalize(`/admin${item.url}`);
            const isActive = canonicalPath.startsWith(itemPath) || currentPath.startsWith(adminItemPath);
            return `
                <li class="nav-item">
                    <a href="${item.url}" class="nav-link${isActive ? " active" : ""}">
                        <i class="far fa-circle nav-icon"></i>
                        <p>${item.label}</p>
                    </a>
                </li>
            `;
        }).join("");

        parts.push(`
            <li class="nav-item console-group" data-console-group="${index}">
                <a href="#" class="nav-link">
                    <i class="nav-icon ${group.icon}"></i>
                    <p>
                        <span class="console-group-label">
                            <strong>${group.label}</strong>
                            <span>${group.description}</span>
                        </span>
                        <i class="right fas fa-angle-left"></i>
                    </p>
                </a>
                <ul class="nav nav-treeview console-subtree">
                    ${itemsHtml}
                </ul>
            </li>
        `);
    });

    navSidebar.insertAdjacentHTML("beforeend", parts.join(""));

    const allGroups = Array.from(navSidebar.querySelectorAll(".console-group"));
    const setOpen = (group, open) => {
        const icon = group.querySelector(".right");
        group.classList.toggle("is-open", open);
        if (icon) {
            icon.classList.toggle("fa-angle-left", !open);
            icon.classList.toggle("fa-angle-down", open);
        }
    };

    allGroups.forEach((group) => {
        const hasActive = !!group.querySelector(".nav-link.active");
        group.classList.toggle("is-active", hasActive);
        setOpen(group, hasActive);

        const trigger = group.querySelector(":scope > .nav-link");
        if (!trigger) {
            return;
        }

        trigger.addEventListener("click", function (event) {
            event.preventDefault();
            const willOpen = !group.classList.contains("is-open");
            allGroups.forEach((other) => setOpen(other, other === group ? willOpen : false));
        });
    });
});
