import json, os, hmac, hashlib, re
import logging
from django.conf import settings
from django.db.models import Q
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection, IntegrityError, transaction
from django.apps import apps as django_apps
apps = django_apps
from django.test import Client,RequestFactory
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from functools import cmp_to_key
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.template import Template, Context
from django.views.decorators.http import require_POST
from app.console.utils.tpl_render import render_with_vars
from django.http import HttpResponse
from django.core.serializers.json import DjangoJSONEncoder

from ..models import MessageTemplate
from ..forms import MessageTemplateForm

logger = logging.getLogger(__name__)

REQUIRED_ENV = [
    "META_IG_APP_ID", "META_IG_APP_SECRET", "WEBHOOK_VERIFY_TOKEN",
]
RECOMMENDED_ENV = [
    "GRAPH_API_TOKEN", "FB_APP_ID", "FB_APP_SECRET",
    "THREADS_USERNAME", "THREADS_PASSWORD",
    "META_APP_ID", "META_APP_SECRET",
]

_VAR_RE = re.compile(r"{{\s*([\w\.]+)\s*}}")

try:
    # 既存の URL 定義と合わせる（app/app/urls.py で social_views を使っている前提）
    from social import views as social_views
except Exception:
    social_views = None

def _pick_payload_bytes(ev):
    # 候補: JSON データが dict/str で保存されている想定
    candidates = ["payload", "raw_payload", "data", "body", "json", "raw"]
    for name in candidates:
        if hasattr(ev, name):
            val = getattr(ev, name)
            # Django JSONField → dict のことが多い
            if isinstance(val, (dict, list)):
                return _sample_json(val).encode("utf-8")
            if isinstance(val, str):
                return val.encode("utf-8")
    # なければ summary に JSON が入っているケースの救済
    if hasattr(ev, "summary") and isinstance(ev.summary, str) and ev.summary.strip().startswith("{"):
        try:
            return ev.summary.encode("utf-8")
        except Exception:
            pass
    # どうしても無ければ空 JSON
    return b"{}"

def _sig_headers(service: str, body: bytes):
    """
    Facebook/Instagram 由来: X-Hub-Signature(sha1), X-Hub-Signature-256(sha256)
    Threads 側も同様に付けられるなら付ける。Secret が無ければ空で返す。
    """
    h = {}
    app_secret = None
    if service == "ig":
        app_secret = os.environ.get("META_IG_APP_SECRET") or os.environ.get("FB_APP_SECRET") or os.environ.get("META_APP_SECRET")
    elif service == "th":
        # Threads 用に決め打ち Secret があればここで読む（無ければ IG と同じ候補を流用）
        app_secret = os.environ.get("META_APP_SECRET") or os.environ.get("FB_APP_SECRET")

    if not app_secret:
        return h  # 付与できない

    try:
        sha1 = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha1).hexdigest()
        sha256 = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        h["HTTP_X_HUB_SIGNATURE"] = f"sha1={sha1}"
        h["HTTP_X_HUB_SIGNATURE_256"] = f"sha256={sha256}"
    except Exception:
        pass
    return h

# ---------- 共通ユーティリティ ----------
def _mask(s: str, keep=4):
    if not s:
        return ""
    s = str(s)
    if len(s) <= keep:
        return "*" * len(s)
    return "*" * (len(s) - keep) + s[-keep:]

def _ok(status_code, ok_set=(200, 202, 204, 400, 401, 403, 405)):
    """Webhook到達確認は 404 以外を OK 扱いにする場合もあるが、
       まずは“存在する/署名違反など”を拾える 4xx を OK 相当で扱う。
    """
    return status_code in ok_set

# ---------- 画面 ----------
def dashboard(request):
    return render(request, "admin/console/dashboard.html")

@staff_member_required
def integration(request):
    ig_accounts = []
    th_accounts = []
    ig_err = th_err = None
    try:
        InstagramBusinessAccount = apps.get_model("ig", "InstagramBusinessAccount")
        ig_accounts = list(InstagramBusinessAccount.objects.all()[:50])
    except Exception as e:
        ig_err = str(e)
    try:
        ThreadsAccount = apps.get_model("th", "ThreadsAccount")
        th_accounts = list(ThreadsAccount.objects.all()[:50])
    except Exception as e:
        th_err = str(e)
    ctx = {"ig_accounts": ig_accounts, "th_accounts": th_accounts, "ig_err": ig_err, "th_err": th_err}
    return render(request, "admin/console/integration.html", ctx)

@staff_member_required
def logs(request):
    """
    直近ログの tail 表示（既存のテンプレに合わせて動作）。
    GET ?n=1000 で行数指定。source は将来拡張用。
    """
    n = 1000
    try:
        n = int(request.GET.get("n", n))
    except Exception:
        n = 1000
    # docker logs を直接叩くのではなく、開発サーバstdoutの末尾を擬似取得
    # docker 環境に依存しない簡易 tail。必要なら後続で source 切替を実装。
    log_path_candidates = [
        "/app/logs/django.log",
        "/var/log/app/django.log",
    ]
    # settings.LOG_FILE があれば優先的に確認
    try:
        if hasattr(settings, "LOG_FILE"):
            log_path_candidates.insert(0, str(settings.LOG_FILE))
    except Exception:
        pass
    lines = []
    used_path = None
    for p in log_path_candidates:
        if os.path.exists(p):
            used_path = p
            try:
                with open(p, "rb") as f:
                    f.seek(0, os.SEEK_END)
                    size = f.tell()
                    # ざっくり後方読み
                    chunk = min(512 * 1024, size)
                    f.seek(-chunk, os.SEEK_END)
                    lines = f.read().decode("utf-8", errors="replace").splitlines()[-n:]
            except Exception:
                pass
            break
    ctx = {"lines": lines, "used_path": used_path, "n": n}
    return render(request, "admin/console/logs.html", ctx)

@staff_member_required
def webhook_test(request):
    """
    Webhook受信の疎通テスト。サンプルJSONを /webhook/instagram/ または /webhook/threads/ にPOST。
    """
    client = Client()
    target = request.POST.get("target") or "instagram"
    sample_instagram = (
        '{\n'
        '  "object": "instagram",\n'
        '  "entry": [\n'
        '    {"id": "1234567890", "changes": [{"field": "comments", "value": {"text": "hello"}}]}\n'
        '  ]\n'
        '}'
    )
    sample_threads = (
        '{\n'
        '  "object": "threads",\n'
        '  "entry": [\n'
        '    {"id": "9876543210", "changes": [{"field": "post", "value": {"text": "hi"}}]}\n'
        '  ]\n'
        '}'
    )
    payload = request.POST.get("payload") or (sample_instagram if target == "instagram" else sample_threads)
    result = None
    error = None
    if request.method == "POST":
        try:
            url = "/webhook/instagram/" if target == "instagram" else "/webhook/threads/"
            # HTTPS リダイレクトを避けるため secure=True で内部POST
            resp = client.post(url, data=payload, content_type="application/json", secure=True)
            body = resp.content.decode("utf-8", errors="replace")
            result = {"url": url, "status": resp.status_code, "body": body[:2000]}
        except Exception as e:
            error = str(e)
    ctx = {
        "target": target,
        "payload": payload,
        "result": result,
        "error": error,
        "sample_instagram": sample_instagram,
        "sample_threads": sample_threads,
    }
    return render(request, "admin/console/webhook_test.html", ctx)

@staff_member_required
def connection_test(request):
    """
    ヘルスチェック（DB・未適用マイグレーション・Webhook到達・モデル参照・環境変数）
    """
    checks = []

    # 1) DB 接続
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks.append({"name": "データベース接続", "status": "PASS", "detail": "SELECT 1 OK"})
    except Exception as e:
        checks.append({"name": "データベース接続", "status": "FAIL", "detail": str(e)})

    # 2) 未適用マイグレーション
    try:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            apps_pending = sorted({app for app, _ in [m[0] for m in plan]})
            checks.append({
                "name": "未適用マイグレーション",
                "status": "WARN",
                "detail": f"未適用あり: {', '.join(apps_pending)}"
            })
        else:
            checks.append({"name": "未適用マイグレーション", "status": "PASS", "detail": "なし"})
    except Exception as e:
        checks.append({"name": "未適用マイグレーション", "status": "FAIL", "detail": str(e)})

    # 3) Webhook ルート到達（GET/POST）
    client = Client()
    for label, path in (("Instagram Webhook", "/webhook/instagram/"),
                        ("Threads Webhook", "/webhook/threads/")):
        try:
            r_get = client.get(path, secure=True)
            r_post = client.post(path, data="{}", content_type="application/json", allow_redirects=True, timeout=10, secure=True)
            ok = _ok(r_get.status_code) or _ok(r_post.status_code)
            checks.append({
                "name": f"{label} 到達性",
                "status": "PASS" if ok else "WARN",
                "detail": f"GET {r_get.status_code} / POST {r_post.status_code}"
            })
        except Exception as e:
            checks.append({"name": f"{label} 到達性", "status": "FAIL", "detail": str(e)})

    # 4) 主要モデル参照テスト（存在すれば件数を軽く参照）
    model_specs = [
        ("ig", "InstagramBusinessAccount", "Instagram ビジネスアカウント"),
        ("ig", "IGPost", "Instagram 投稿"),
        ("social", "AutoReplyRule", "自動返信ルール"),
        ("social", "DmMessage", "DM メッセージ"),
        ("social", "DmReplyTemplate", "DM 返信テンプレート"),
        ("th", "ThreadsAccount", "Threads アカウント"),
        ("yaget", "MallAccount", "モールアカウント"),  # 存在しない場合はスキップ
    ]
    for app_label, model_name, title in model_specs:
        try:
            Model = apps.get_model(app_label, model_name)
            if Model is None:
                continue
            cnt = Model.objects.all().count()
            checks.append({"name": f"モデル参照: {title}", "status": "PASS", "detail": f"件数: {cnt}"})
        except LookupError:
            # モデルが実在しないのは FAIL ではなくスキップ扱い（表示しない）
            continue
        except Exception as e:
            checks.append({"name": f"モデル参照: {title}", "status": "FAIL", "detail": str(e)})

    # 5) 環境変数（存在のみ。値はマスク）
    env_keys = [
        # Meta/IG
        "META_IG_APP_ID", "META_IG_APP_SECRET", "GRAPH_API_TOKEN", "FB_APP_ID", "FB_APP_SECRET",
        # Threads 側（例）
        "THREADS_USERNAME", "THREADS_PASSWORD",
        # 汎用
        "WEBHOOK_VERIFY_TOKEN", "META_APP_ID", "META_APP_SECRET",
    ]
    present = []
    missing = []
    for k in env_keys:
        v = os.environ.get(k)
        if v:
            present.append(f"{k} = {_mask(v)}")
        else:
            missing.append(k)
    detail = []
    if present: detail.append("設定あり:\n- " + "\n- ".join(present))
    if missing: detail.append("未設定:\n- " + "\n- ".join(missing))
    checks.append({
        "name": "環境変数の存在",
        "status": "PASS" if not missing else "WARN",
        "detail": "\n\n".join(detail) if detail else "対象なし",
    })

    # 集計
    summary = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for c in checks:
        summary[c["status"]] = summary.get(c["status"], 0) + 1

    ctx = {"checks": checks, "summary": summary}
    return render(request, "admin/console/connection_test.html", ctx)

def _dt_of(obj):
    # created系をできるだけ拾う（無ければNone）
    for k in ("created_at", "created", "timestamp", "ts", "received_at"):
        if hasattr(obj, k) and getattr(obj, k):
            return getattr(obj, k)
    return None

def _payload_of(obj):
    # よくあるフィールド名を総当り
    for k in ("payload", "body", "raw_body", "data", "raw", "json"):
        if hasattr(obj, k) and getattr(obj, k) not in (None, ""):
            return getattr(obj, k)
    return None

def _pretty_and_text(payload):
    """payload( dict | str | None ) -> (pretty, flat_text)"""
    if payload is None:
        return ("(no payload)", "")
    # dict ならそのまま、文字列ならJSONとして読み直すのを試みる
    try:
        if isinstance(payload, str):
            try:
                obj = json.loads(payload)
            except Exception:
                # プレーン文字列
                return (payload, payload)
        else:
            obj = payload
        pretty = _sample_json(obj)
        flat   = _sample_json(obj)
        return (pretty, flat)
    except Exception:
        s = str(payload)
        return (s, s)

def webhook_events(request):
    """
    Instagram / Threads のWebhook受信イベントを横断表示。
    GET:
      - service: all|instagram|threads
      - q: ペイロード内検索（単純包含）
      - limit: 1..1000 既定200
    """
    service = request.GET.get("service", "all")
    q = (request.GET.get("q") or "").strip()
    try:
        limit = int(request.GET.get("limit", "200"))
        limit = max(1, min(limit, 1000))
    except Exception:
        limit = 200

    rows, errors = [], []

    # Instagram（モデル名の差異に強い取得）
    if service in ("all", "instagram"):
        try:
            IgEvent = django_apps.get_model("ig", "IGWebhookEvent")  # ← 正式名
        except Exception as e:
            IgEvent = None
            errors.append(f"Instagram 読み込み失敗: {e}")
        if IgEvent:
            try:
                for ev in IgEvent.objects.order_by("-id")[:limit]:
                    dt  = _dt_of(ev)
                    pl  = _payload_of(ev)
                    pretty, flat = _pretty_and_text(pl)
                    if q and q not in flat:
                        continue
                    rows.append({
                        "src": "instagram",
                        "pk": ev.pk,
                        "dt": dt,
                        "summary": _summary_of(ev, flat),
                        "pretty": pretty,
                    })
            except Exception as e:
                errors.append(f"Instagram 読み込み失敗: {e}")

    # Threads
    if service in ("all", "threads"):
        try:
            ThEvent = django_apps.get_model("th", "THWebhookEvent")  # ← 正式名
        except Exception as e:
            ThEvent = None
            errors.append(f"Threads 読み込み失敗: {e}")
        if ThEvent:
            try:
                for ev in ThEvent.objects.order_by("-id")[:limit]:
                    dt  = _dt_of(ev)
                    pl  = _payload_of(ev)
                    pretty, flat = _pretty_and_text(pl)
                    if q and q not in flat:
                        continue
                    rows.append({
                        "src": "threads",
                        "pk": ev.pk,
                        "dt": dt,
                        "summary": _summary_of(ev, flat),
                        "pretty": pretty,
                    })
            except Exception as e:
                errors.append(f"Threads 読み込み失敗: {e}")

    # 受信時刻の降順
    def _cmp(a, b):
        ad, bd = a["dt"], b["dt"]
        if ad and bd:
            return -1 if ad > bd else (1 if ad < bd else 0)
        if ad and not bd: return -1
        if bd and not ad: return 1
        return 0
    rows.sort(key=cmp_to_key(_cmp))

    ctx = {"service": service, "q": q, "limit": limit, "rows": rows, "errors": errors}
    return render(request, "admin/console/webhook_events.html", ctx)

@staff_member_required
def webhook_replay(request, src: str, pk: int):
    """
    保存済み Webhook イベントを「実エンドポイントと同じビュー関数」で再処理する。
    - src: 'ig' or 'th'
    - pk:   対象イベントの PK
    """
    if src not in ("ig", "th"):
        messages.error(request, f"未知のサービス指定: {src}")
        return HttpResponseRedirect(reverse("console:webhook_events"))

    # モデル import
    ev = None
    try:
        if src == "ig":
            from ig.models import IGWebhookEvent as Ev
        else:
            from th.models import THWebhookEvent as Ev
        ev = Ev.objects.get(pk=pk)
    except Exception as e:
        messages.error(request, f"イベント取得に失敗: {e}")
        return HttpResponseRedirect(reverse("console:webhook_events"))

    body = _pick_payload_bytes(ev)

    # 送信先ビュー（既存の本番ルートと同一）
    if not social_views:
        messages.error(request, "social.views の読み込みに失敗しました。URL へ直接 POST する実装へ切替が必要です。")
        return HttpResponseRedirect(reverse("console:webhook_events"))

    view = social_views.webhook_instagram if src == "ig" else social_views.webhook_threads
    path = "/webhook/instagram/" if src == "ig" else "/webhook/threads/"

    rf = RequestFactory()
    headers = _sig_headers(src, body)
    # content_type は application/json 固定
    req = rf.post(path, data=body, content_type="application/json", **headers)
    # ビューの中で user / META を見る可能性に備えて最低限持たせる
    req.user = getattr(request, "user", None)

    # 実呼び出し
    try:
        resp = view(req)
        code = getattr(resp, "status_code", None)
        messages.success(request, f"再処理を実行しました（status={code}）。イベントID={pk}, サービス={src.upper()}")
        logger.info("Console Replay: src=%s pk=%s status=%s user=%s", src, pk, code, getattr(request.user, "username", "?"))
    except Exception as e:
        messages.error(request, f"再処理中に例外が発生しました: {e}")
        logger.exception("Console Replay failed: src=%s pk=%s", src, pk)

    # 一覧へ戻る（直前の検索条件がある場合はそのまま戻す）
    back = request.GET.get("back")
    if back:
        try:
            return HttpResponseRedirect(back)
        except Exception:
            pass
    return HttpResponseRedirect(reverse("console:webhook_events"))

@staff_member_required
def help_guide(request):
    """
    iメイト / SNS連携の初回セットアップガイド（MVP）
    - Instagram アカウント連携の流れ
    - 自動返信（パッケージ/ルール）の作成ポイント
    - 動作確認（接続テスト / Webhookテスト / ログ）
    """
    return render(request, "admin/console/help_guide.html")

def _has_value(k: str) -> bool:
    v = os.environ.get(k, "")
    return bool(str(v).strip())

def _import_first(mod_names):
    for mod in mod_names:
        try:
            return import_module(mod)
        except Exception:
            continue
    return None

def _find_model(candidates):
    """
    social.models / sns_core.models から候補名のどれかを探す。
    見つからなければ None
    """
    mod = _import_first(["social.models", "sns_core.models"])
    if not mod:
        return None
    for name in candidates:
        if hasattr(mod, name):
            return getattr(mod, name)
    return None

def _admin_add_url(model_cls):
    try:
        return reverse(f"admin:{model_cls._meta.app_label}_{model_cls._meta.model_name}_add")
    except Exception:
        return None

@staff_member_required
def setup_env(request):
    """
    ① 環境変数チェック
    """
    must = {k: _has_value(k) for k in REQUIRED_ENV}
    opt  = {k: _has_value(k) for k in RECOMMENDED_ENV}
    all_ok = all(must.values())

    if request.GET.get("next") == "templates" and all_ok:
        return HttpResponseRedirect(reverse("console:setup_templates"))

    ctx = {
        "must": must,
        "opt": opt,
        "all_ok": all_ok,
    }
    return render(request, "admin/console/setup_env.html", ctx)

# ---- テンプレ作成（安全にベストエフォート） ----
TEMPLATE_MODEL_CANDIDATES = ["AutoReplyTemplate", "DMTemplate", "ReplyTemplate", "MessageTemplate"]

def _create_template_best_effort(name: str, body: str):
    """
    返信テンプレ用モデルを探し、作成を試みる。
    - 必要最低限（name/title, text/body/message/content）のみセット
    - 失敗しても例外を外へ投げず、(ok, msg, obj_or_none) で返す
    """
    Model = _find_model(TEMPLATE_MODEL_CANDIDATES)
    if not Model:
        return (False, "テンプレートモデルが見つかりません（social/sns_core）", None)

    fields = {f.name for f in Model._meta.get_fields() if hasattr(f, "attname")}
    name_field = "name" if "name" in fields else ("title" if "title" in fields else None)
    text_field = None
    for cand in ["text", "body", "message", "content", "template_text"]:
        if cand in fields:
            text_field = cand
            break
    if not name_field or not text_field:
        return (False, f"必須項目が不明（name/title or text系が見つからない）: {Model.__name__}", None)

    # 既存チェック（name/title があれば）
    exists_qs = None
    try:
        exists_qs = Model.objects.filter(**{name_field: name})
    except Exception:
        exists_qs = None

    if exists_qs is not None and exists_qs.exists():
        return (True, f"既存テンプレートを使用: {name}", exists_qs.first())

    try:
        with transaction.atomic():
            obj = Model()
            setattr(obj, name_field, name)
            setattr(obj, text_field, body)
            obj.save()
        return (True, f"テンプレート作成: {name}", obj)
    except IntegrityError as e:
        return (False, f"DB制約で作成失敗: {e}", None)
    except Exception as e:
        return (False, f"作成失敗: {e}", None)

@staff_member_required
def setup_templates(request):
    """
    ② 返信テンプレ雛形の作成
    """
    created = []
    errors  = []
    Model = _find_model(TEMPLATE_MODEL_CANDIDATES)
    admin_add = _admin_add_url(Model) if Model else None

    if request.method == "POST":
        logger.info("Console Setup Wizard: create templates by user=%s", getattr(request.user, "username", "?"))
        plans = [
            ("無料鑑定 初回返信", "ご連絡ありがとうございます。無料鑑定をご希望の場合は、以下をお知らせください：\n1) お名前 2) 生年月日 3) ご相談内容（200文字程度）"),
            ("営業時間外 受信", "営業時間外のため、折り返しご連絡いたします。しばらくお待ちください。"),
        ]
        for name, body in plans:
            ok, msg, obj = _create_template_best_effort(name, body)
            (created if ok else errors).append(msg)

        if not errors:
            messages.success(request, "返信テンプレ雛形の作成が完了しました。")
            return HttpResponseRedirect(reverse("console:setup_rules"))
        else:
            messages.warning(request, "一部作成できませんでした。管理画面からの作成をご検討ください。")

    ctx = {
        "model_found": bool(Model),
        "admin_add_url": admin_add,
        "created": created,
        "errors": errors,
    }
    return render(request, "admin/console/setup_templates.html", ctx)

# ---- 自動返信ルール作成（ベストエフォート） ----
RULE_MODEL_CANDIDATES = ["AutoReplyRule", "ReplyRule", "DMReplyRule"]

def _create_rule_best_effort(keyword: str, template_obj):
    Rule = _find_model(RULE_MODEL_CANDIDATES)
    if not Rule or template_obj is None:
        return (False, "ルールモデルが見つからない、またはテンプレート未指定", None)

    fields = {f.name: f for f in Rule._meta.get_fields() if hasattr(f, "attname")}
    # キーワード項目推測
    kw_field = None
    for cand in ["keyword", "keywords", "pattern", "match_word"]:
        if cand in fields:
            kw_field = cand
            break
    # テンプレFK推測（ForeignKey でテンプレモデルを指す項目）
    tpl_field = None
    for name, f in fields.items():
        try:
            rel = getattr(f, "remote_field", None)
            if rel and rel.model and rel.model == template_obj.__class__:
                tpl_field = name
                break
        except Exception:
            pass

    name_field = "name" if "name" in fields else ("title" if "title" in fields else None)
    if not kw_field or not tpl_field:
        return (False, "必須項目（キーワード/テンプレ参照）が特定できず作成をスキップ", None)

    # 既存チェック（name or keyword で）
    try:
        q = Rule.objects.all()
        if name_field:
            q = q.filter(**{name_field: f"自動作成: {keyword}"})
        elif kw_field:
            q = q.filter(**{kw_field: keyword})
        if q.exists():
            return (True, "既存ルールを使用", q.first())
    except Exception:
        pass

    try:
        with transaction.atomic():
            obj = Rule()
            if name_field:
                setattr(obj, name_field, f"自動作成: {keyword}")
            setattr(obj, kw_field, keyword)
            setattr(obj, tpl_field, template_obj)
            obj.save()
        return (True, f"ルール作成: {keyword}", obj)
    except IntegrityError as e:
        return (False, f"DB制約で作成失敗: {e}", None)
    except Exception as e:
        return (False, f"作成失敗: {e}", None)

@staff_member_required
def setup_rules(request):
    """
    ③ 自動返信ルール作成
    - ②で作った「無料鑑定 初回返信」を使って「無料鑑定希望」キーワードのルールを作成
    """
    Template = _find_model(TEMPLATE_MODEL_CANDIDATES)
    Rule = _find_model(RULE_MODEL_CANDIDATES)
    template_obj = None
    created = []
    errors  = []
    admin_rule_add = _admin_add_url(Rule) if Rule else None
    admin_tpl_changelist = None
    if Template:
        try:
            admin_tpl_changelist = reverse(f"admin:{Template._meta.app_label}_{Template._meta.model_name}_changelist")
        except Exception:
            pass

    # 既存テンプレ検索
    if Template:
        try:
            template_obj = Template.objects.filter(name="無料鑑定 初回返信").first() or \
                           Template.objects.filter(title="無料鑑定 初回返信").first()
        except Exception:
            template_obj = None

    if request.method == "POST":
        logger.info("Console Setup Wizard: create rule by user=%s", getattr(request.user, "username", "?"))
        ok, msg, _obj = _create_rule_best_effort("無料鑑定希望", template_obj)
        (created if ok else errors).append(msg)
        if not errors:
            messages.success(request, "自動返信ルールの作成が完了しました。")
            return HttpResponseRedirect(reverse("console:index"))
        else:
            messages.warning(request, "自動作成に失敗した項目があります。管理画面からの作成をご検討ください。")

    ctx = {
        "template_found": bool(Template),
        "rule_found": bool(Rule),
        "template_obj": template_obj,
        "admin_rule_add_url": admin_rule_add,
        "admin_tpl_changelist_url": admin_tpl_changelist,
        "created": created,
        "errors": errors,
    }
    return render(request, "admin/console/setup_rules.html", ctx)

def _extract_vars(text: str):
    return sorted(set(_VAR_RE.findall(text or "")))

def _sample_json(service: str = "common") -> str:
    """テンプレUIで表示する差し込みサンプルJSONを生成"""
    return json.dumps(
        _default_context(service),
        ensure_ascii=False,
        indent=2,
        cls=DjangoJSONEncoder,  # ← これで datetime/date/Decimal/UUID などOK
    )

def _default_context(service: str):
    base = {
        "brand_name": "SNS運用",
        "user_name": "田中さま",
        "account_name": "buyers_official",
        "now": timezone.now(),
        "post_url": "https://example.com/post/123",
        "help_url": "https://example.com/help",
    }
    if service == "ig":
        base.update({"service": "Instagram", "dm_link": "https://instagram.com/direct/inbox/"})
    elif service == "th":
        base.update({"service": "Threads", "threads_link": "https://www.threads.net/"})
    else:
        base.update({"service": "共通"})
    return base

@staff_member_required
def tpl_list(request):
    q = request.GET.get("q", "").strip()
    service = request.GET.get("service", "")
    qs = MessageTemplate.objects.all()
    if service in ("common", "ig", "th"):
        qs = qs.filter(service=service)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(key__icontains=q) | Q(description__icontains=q))
    ctx = {"items": qs, "q": q, "service": service, "title": "返信テンプレート"}
    return render(request, "admin/console/tpl_list.html", ctx)

@staff_member_required
def tpl_new(request):
    if request.method == "POST":
        form = MessageTemplateForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "テンプレートを作成しました。")
            return redirect("console:tpl_edit", pk=obj.pk)
    else:
        form = MessageTemplateForm(initial={"service": "common"})
    return render(request, "admin/console/tpl_form.html", {
        "form": form, "mode": "new", "sample_json": _sample_json(_default_context("common"))
    })

@staff_member_required
def tpl_edit(request, pk: int):
    obj = get_object_or_404(MessageTemplate, pk=pk)
    if request.method == "POST":
        if "delete" in request.POST:
            return redirect("console:tpl_delete", pk=obj.pk)
        form = MessageTemplateForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "テンプレートを更新しました。")
            return redirect("console:tpl_edit", pk=obj.pk)
    else:
        form = MessageTemplateForm(instance=obj)
    return render(request, "admin/console/tpl_form.html", {
        "form": form, "mode": "edit", "obj": obj,
        "sample_json": _sample_json(_default_context(obj.service))
    })

@staff_member_required
def tpl_delete(request, pk: int):
    obj = get_object_or_404(MessageTemplate, pk=pk)
    if request.method == "POST":
        name = str(obj)
        obj.delete()
        messages.success(request, f"削除しました: {name}")
        return redirect("console:tpl_list")
    return render(request, "admin/console/confirm_delete.html", {"obj": obj, "back": "console:tpl_list"})

@staff_member_required
def tpl_export(request):
    data = []
    for t in MessageTemplate.objects.all().order_by("id"):
        data.append({
            "service": getattr(t, "service", ""),
            "name": getattr(t, "name", ""),
            "key": getattr(t, "key", ""),
            "description": getattr(t, "description", ""),
            "content": getattr(t, "content", ""),     # ← ここ
            "is_active": getattr(t, "is_active", True),
        })
    js = _sample_json({"templates": data})
    resp = HttpResponse(js, content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = 'attachment; filename="message_templates.json"'
    return resp

@staff_member_required
def tpl_import(request):
    if request.method == "POST" and request.FILES.get("file"):
        raw = request.FILES["file"].read().decode("utf-8")
        payload = json.loads(raw)
        items = payload.get("templates", [])
        cnt = 0
        for it in items:
            obj, created = MessageTemplate.objects.get_or_create(
                key=it.get("key") or None,
                defaults={
                    "service": it.get("service") or "common",
                    "name": it.get("name") or "",
                    "description": it.get("description") or "",
                    "content": it.get("content") or "",     # ← ここ
                    "is_active": it.get("is_active", True),
                }
            )
            if not created:
                obj.service = it.get("service") or obj.service
                obj.name = it.get("name") or obj.name
                obj.description = it.get("description") or obj.description
                if "content" in it:    # ← ここ
                    obj.content = it["content"]
                if "is_active" in it:
                    obj.is_active = it["is_active"]
                obj.save()
            cnt += 1
        messages.success(request, f"テンプレートを {cnt} 件インポートしました。")
        return redirect("console:tpl_list")
    return render(request, "admin/console/tpl_import.html", {"title": "返信テンプレートのインポート"})

@staff_member_required
@require_POST
def tpl_preview_api(request):
    service = request.POST.get("service", "common")
    content = request.POST.get("content", "")   # ← body→content
    ctx = _sample_ctx(service)
    rendered = _render_tokens(content, ctx)
    return JsonResponse({"ok": True, "rendered": rendered})
    
TOKEN_RE = re.compile(r"\[\[([a-zA-Z_][\w\.]*)\]\]")

def _sample_ctx(service: str):
    base = {
        "shop_name": "SNS運用",
        "support_hours": "10:00-18:00",
        "support_email": "support@example.com",
        "now": timezone.now().strftime("%Y/%m/%d %H:%M"),
    }
    if service == "ig":
        base.update({
            "account": {"username": "buyers_ig"},
            "user": {"username": "sample_ig_user"},
            "post": {"link": "https://ig.me/p/ABCD1234"},
        })
    elif service == "th":
        base.update({
            "account": {"username": "buyers_th"},
            "user": {"username": "sample_th_user"},
            "post": {"link": "https://threads.net/t/abcd"},
        })
    return base

def _render_tokens(text: str, ctx: dict) -> str:
    # [[a.b]] → ctx["a"]["b"] を辿る。無ければそのまま残す
    def repl(m):
        path = m.group(1).split(".")
        cur = ctx
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return m.group(0)  # 未解決は残す
        return str(cur)
    return TOKEN_RE.sub(repl, text or "")

TOKEN_SQUARE = re.compile(r"\[\[([a-zA-Z_][\w\.]*)\]\]")
TOKEN_JINJA  = re.compile(r"\{\{\s*([a-zA-Z_][\w\.]*)\s*\}\}")

def _resolve_path(ctx: dict, path: str):
    cur = ctx
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur

def _render_tokens(text: str, ctx: dict) -> str:
    def repl_square(m):
        val = _resolve_path(ctx, m.group(1))
        return str(val) if val is not None else m.group(0)
    def repl_jinja(m):
        val = _resolve_path(ctx, m.group(1))
        return str(val) if val is not None else m.group(0)
    out = TOKEN_SQUARE.sub(repl_square, text or "")
    out = TOKEN_JINJA.sub(repl_jinja, out)
    return out
