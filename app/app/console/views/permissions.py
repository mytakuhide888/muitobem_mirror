# app/console/views/permissions.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from ig.models import InstagramBusinessAccount
from sns_core.models import MetaUserToken
from ..permissions_map import REQUIRED

@staff_member_required
def permissions_check(request):
    rows = []
    for acc in InstagramBusinessAccount.objects.all():
        granted = set((acc.permissions or {}).get("granted", []))
        for key, rule in REQUIRED.items():
            need = set(rule["scopes"])
            ok = need.issubset(granted)
            rows.append({
                "account": acc,
                "feature": key,
                "need": sorted(need),
                "granted": sorted(granted),
                "ok": ok,
                "missing": sorted(need - granted),
            })
    return render(request, "admin/console/permissions.html", {"rows": rows})
