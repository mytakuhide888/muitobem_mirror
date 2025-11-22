# app/console/views/accounts.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from sns_core.models import MetaUserToken
from ig.models import InstagramBusinessAccount
from ..utils import meta as metaapi
from django.contrib import messages
from django.urls import reverse, NoReverseMatch

def _login_url() -> str:
    """
    Meta/Facebook ログイン開始の URL 名が環境で違うことがあるので、段階的に探す。
    どれも無ければ最後はハードコードにフォールバック。
    """
    for name in ("console:meta_login", "console:oauth_begin", "console:meta_oauth_begin"):
        try:
            return reverse(name)
        except NoReverseMatch:
            pass
    return "/console/oauth/begin/"

@staff_member_required
def accounts_list(request):
    # OAuth済み？ページ列挙して取り込みUI
    user_id = request.session.get("meta_user_id")
    pages, igs = [], []
    token = None
    if user_id:
        tk = MetaUserToken.objects.filter(user_id=user_id).order_by("-created_at").first()
        if tk:
            token = tk.access_token
            try:
                pages = metaapi.list_pages(token)
                # それぞれに IG が紐づくかチェックして表示用にバインド
                igs = []
                for p in pages:
                    ig = metaapi.page_to_ig(p["id"], token)
                    if ig:
                        igs.append({"page": p, "ig": ig})
            except Exception as e:
                messages.warning(request, f"ページ取得に失敗: {e}")

    # ── 追加：/me/accounts の再取得（画面のボタンから POST）
    if request.method == "POST" and request.POST.get("action") == "fetch_candidates":
        if not token:
            messages.warning(request, "先に Meta ログインを実行してください。")
            return redirect("console:accounts")
        try:
            pages = metaapi.list_pages(token)
            igs = []
            for p in pages:
                ig = metaapi.page_to_ig(p["id"], token)
                if ig:
                    igs.append({"page": p, "ig": ig})
            messages.success(request, "候補を再取得しました。")
        except Exception as e:
            messages.error(request, f"候補の再取得に失敗: {e}")
        # fall through で下の render へ

    # 既存登録一覧
    existing = InstagramBusinessAccount.objects.all().order_by("username")
    return render(request, "admin/console/accounts.html", {
        "existing": existing,
        "pages_igs": igs,
        "token_present": bool(token),
        "login_url": _login_url(), 
    })

@staff_member_required
@require_POST
def meta_import(request):
    """選択された IG を登録"""
    user_id = request.session.get("meta_user_id")
    tk = MetaUserToken.objects.filter(user_id=user_id).order_by("-created_at").first()
    if not tk:
        messages.error(request, "OAuthトークンが見つかりません。先に『アカウント追加』してください。")
        return redirect("console:accounts")

    chosen = request.POST.getlist("ig_ids")  # ["1784...", ...]
    ok = 0
    for ig in chosen:
        InstagramBusinessAccount.objects.update_or_create(
            external_id=ig,
            defaults=dict(
                access_token=tk.access_token,
                token_expires_at=tk.expires_at,
                permissions={"granted": tk.granted_scopes, "declined": tk.declined_scopes},
            )
        )
        ok += 1
    messages.success(request, f"{ok} 件取り込みました。")
    return redirect("console:accounts")
