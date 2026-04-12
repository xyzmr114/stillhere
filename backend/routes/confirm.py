import math

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

from config import settings
from db import get_session, get_contact_confirmation_by_token, confirm_contact, count_contact_confirmations, is_escalation_resolved, get_escalation_by_id, user_confirm_escalation, get_user, cancel_escalation, log_audit_event
from dependencies import get_current_user

router = APIRouter(tags=["confirm"])

_BASE_STYLE = """
body{margin:0;padding:0;background:#0f0f1a;color:#eee;
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{text-align:center;padding:40px 32px;max-width:480px;width:100%;
animation:fadeIn .5s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.icon{font-size:64px;margin-bottom:24px}
h1{font-size:28px;font-weight:700;margin:0 0 12px}
p{font-size:16px;line-height:1.6;margin:0 0 40px;opacity:.8}
.brand{font-size:13px;opacity:.4;letter-spacing:1px}
"""

_SHIELD_RED = (
    '<svg width="64" height="64" viewBox="0 0 24 24" fill="none" '
    'stroke="#e94560" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 '
    '8 10 8 10z"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" '
    'y1="9" x2="15" y2="15"/></svg>'
)

_SHIELD_BLUE = (
    '<svg width="64" height="64" viewBox="0 0 24 24" fill="none" '
    'stroke="#5bc0de" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round"><circle cx="12" cy="12" r="10"/>'
    '<line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" '
    'x2="12.01" y2="16"/></svg>'
)

_SHIELD_GREEN = (
    '<svg width="64" height="64" viewBox="0 0 24 24" fill="none" '
    'stroke="#4ecca3" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 '
    '8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>'
)


def _page(icon: str, heading: str, heading_color: str, subtext: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Still Here — {heading}</title>
<style>{_BASE_STYLE}</style></head>
<body><div class="card">
<div class="icon">{icon}</div>
<h1 style="color:{heading_color}">{heading}</h1>
<p>{subtext}</p>
<div class="brand">STILL HERE</div>
</div></body></html>"""


def _confirm_page(contact_name: str, user_name: str, token: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Still Here — Confirm Safety</title>
<style>{_BASE_STYLE}</style></head>
<body><div class="card" id="main-card">
<div class="icon">{_SHIELD_BLUE}</div>
<h1 style="color:#5bc0de">{contact_name}, we need your help</h1>
<p>{user_name} missed their daily check-in. We want to make sure they're okay.</p>

<div id="step1">
<h2 style="font-size:18px;margin:20px 0 10px">Step 1: Did you actually reach out to them?</h2>
<p style="font-size:14px;opacity:.7">Please call, text, or visit before confirming.</p>
<button onclick="showStep2()" style="display:block;width:100%;padding:14px;margin:8px 0;background:#4ecca3;color:#0f0f1a;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer">Yes, I contacted them</button>
<button onclick="showGuidance()" style="display:block;width:100%;padding:14px;margin:8px 0;background:transparent;color:#eee;border:1px solid #555;border-radius:8px;font-size:16px;cursor:pointer">I haven't yet</button>
</div>

<div id="guidance" style="display:none">
<h2 style="font-size:18px;margin:20px 0 10px">Try these steps first:</h2>
<ul style="text-align:left;font-size:14px;line-height:2;opacity:.8">
<li>Call or text their phone</li>
<li>Check their social media for recent activity</li>
<li>Reach out to mutual friends or family</li>
<li>Visit their home if possible</li>
</ul>
<button onclick="showStep2()" style="display:block;width:100%;padding:14px;margin:16px 0;background:#4ecca3;color:#0f0f1a;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer">Okay, I contacted them</button>
</div>

<div id="step2" style="display:none">
<h2 style="font-size:18px;margin:20px 0 10px">Step 2: Is {user_name} safe?</h2>
<button onclick="confirmSafe()" style="display:block;width:100%;padding:14px;margin:8px 0;background:#4ecca3;color:#0f0f1a;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer">Yes, they're safe</button>
<button onclick="cantReach()" style="display:block;width:100%;padding:14px;margin:8px 0;background:#e94560;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer">No, I can't reach them</button>
</div>

<div id="result" style="display:none"></div>
</div>
<script>
function showStep2(){{document.getElementById('step1').style.display='none';document.getElementById('guidance').style.display='none';document.getElementById('step2').style.display='block'}}
function showGuidance(){{document.getElementById('step1').style.display='none';document.getElementById('guidance').style.display='block'}}
function confirmSafe(){{fetch('/confirm/{token}/confirm',{{method:'POST'}}).then(r=>r.json()).then(d=>{{document.getElementById('step2').style.display='none';document.getElementById('result').style.display='block';document.getElementById('result').innerHTML='<div class="icon">{_SHIELD_GREEN}</div><h1 style="color:#4ecca3">Thank You, {contact_name}</h1><p>'+d.message+'</p><div class="brand">STILL HERE</div>'}})}}
function cantReach(){{fetch('/confirm/{token}/cant-reach',{{method:'POST'}}).then(r=>r.json()).then(d=>{{document.getElementById('step2').style.display='none';document.getElementById('result').style.display='block';document.getElementById('result').innerHTML='<div class="icon">{_SHIELD_RED}</div><h1 style="color:#e94560">Noted</h1><p>'+d.message+'</p><div class="brand">STILL HERE</div>'}})}}
</script></body></html>"""


_BRIEF_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Still Here — Contact Action Guide</title>
<style>body{margin:0;padding:0;background:#0f0f1a;color:#eee;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:20px}
.container{max-width:600px;margin:0 auto;padding:20px 0}
h1{font-size:24px;color:#5bc0de;margin:0 0 8px}
h2{font-size:18px;color:#4ecca3;margin:24px 0 8px}
p{font-size:15px;line-height:1.7;opacity:.85;margin:0 0 12px}
.step{background:#1a1a2e;border-radius:8px;padding:16px;margin:8px 0}
.step-num{display:inline-block;background:#4ecca3;color:#0f0f1a;width:28px;height:28px;border-radius:50%;text-align:center;line-height:28px;font-weight:700;margin-right:8px}
.warning{background:#2a1a1a;border-left:3px solid #e94560;padding:12px 16px;border-radius:0 8px 8px 0;margin:12px 0}
.brand{font-size:12px;opacity:.3;letter-spacing:1px;text-align:center;margin-top:40px}
</style></head>
<body><div class="container">
<h1>What to do when you get a Still Here alert</h1>
<p>You received this alert because someone who listed you as an emergency contact missed their daily check-in. Here's what to do:</p>

<h2>Step-by-step guide</h2>
<div class="step"><span class="step-num">1</span><strong>Don't panic.</strong> Most missed check-ins are false alarms — dead battery, forgot, phone on silent.</div>
<div class="step"><span class="step-num">2</span><strong>Try to reach them.</strong> Call, text, check social media, message mutual friends.</div>
<div class="step"><span class="step-num">3</span><strong>Confirm on the link.</strong> Only confirm they're safe if you've actually reached them.</div>
<div class="step"><span class="step-num">4</span><strong>Wait.</strong> Other contacts are also being alerted. If a majority confirms they're safe, the alert resolves.</div>

<div class="warning">
<strong>When to call 911 yourself:</strong> If you have genuine reason to believe they are in danger — not just because they missed a check-in. This app does not replace your judgment.
</div>

<h2>What happens if no one confirms?</h2>
<p>If contacts can't confirm safety within 48 hours, a non-emergency welfare check may be requested. This is NOT 911 — it's a non-emergency dispatch line.</p>

<h2>Who else was contacted?</h2>
<p>All emergency contacts on file receive the same alert simultaneously. You can coordinate with other contacts.</p>

<div class="brand">STILL HERE — Safety check-in app</div>
</div></body></html>"""


@router.get("/brief", response_class=HTMLResponse)
def contact_brief():
    return HTMLResponse(_BRIEF_PAGE)


@router.get("/confirm/{token}", response_class=HTMLResponse)
def confirm_page(token: str, db=Depends(get_session)):
    cc = get_contact_confirmation_by_token(db, token)
    if not cc:
        return HTMLResponse(
            _page(_SHIELD_RED, "Link Not Found", "#e94560", "This confirmation link is invalid or has expired."),
            status_code=404,
        )
    escalation_event_id = cc["escalation_event_id"]
    if is_escalation_resolved(db, escalation_event_id):
        return HTMLResponse(_page(_SHIELD_BLUE, "Already Resolved", "#5bc0de", "This escalation has already been resolved."))
    if cc.get("confirmed_at"):
        return HTMLResponse(_page(_SHIELD_BLUE, "Already Confirmed", "#5bc0de", "You've already confirmed. Thank you!"))
    escalation = get_escalation_by_id(db, escalation_event_id)
    user = get_user(db, str(escalation["user_id"])) if escalation else None
    user_name = user.get("name", "the user") if user else "the user"
    contact_name = cc["contact_name"]
    return HTMLResponse(_confirm_page(contact_name, user_name, token))


@router.post("/confirm/{token}/confirm")
def do_confirm(token: str, db=Depends(get_session)):
    cc = get_contact_confirmation_by_token(db, token)
    if not cc:
        raise HTTPException(status_code=404, detail="Not found")
    escalation_event_id = cc["escalation_event_id"]
    if is_escalation_resolved(db, escalation_event_id):
        return {"status": "already_resolved"}
    if cc.get("confirmed_at"):
        return {"status": "already_confirmed"}
    confirm_contact(db, token)
    escalation = get_escalation_by_id(db, escalation_event_id)
    if escalation:
        log_audit_event(db, str(escalation["user_id"]), "contact_confirmed", {"contact_name": cc["contact_name"]})
    confirmed_count, total_count = count_contact_confirmations(db, escalation_event_id)
    majority = math.ceil(total_count / 2)
    if confirmed_count >= majority:
        return {"status": "confirmed", "majority": True, "message": "Majority reached. Waiting for user to confirm."}
    return {"status": "confirmed", "majority": False, "message": "Recorded. Waiting for other contacts."}


@router.post("/confirm/{token}/cant-reach")
def cant_reach(token: str, db=Depends(get_session)):
    cc = get_contact_confirmation_by_token(db, token)
    if not cc:
        raise HTTPException(status_code=404, detail="Not found")
    escalation_event_id = cc["escalation_event_id"]
    escalation = get_escalation_by_id(db, escalation_event_id)
    if escalation:
        log_audit_event(db, str(escalation["user_id"]), "contact_cant_reach", {"contact_name": cc["contact_name"]})
    return {"status": "noted", "message": "We've noted that you can't reach them."}


@router.post("/confirm-user/{escalation_id}")
def confirm_user(escalation_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    escalation = get_escalation_by_id(db, escalation_id)
    if not escalation or str(escalation["user_id"]) != str(user["id"]):
        return JSONResponse({"status": "error", "message": "Forbidden"}, status_code=403)

    if escalation["resolved"]:
        return JSONResponse({"status": "error", "message": "Already confirmed"})

    confirmed_count, total_count = count_contact_confirmations(db, escalation_id)
    majority = math.ceil(total_count / 2)
    if confirmed_count < majority:
        return JSONResponse({"status": "error", "message": "Contacts haven't confirmed yet"})

    user_confirm_escalation(db, escalation_id, str(user["id"]))
    return JSONResponse({"status": "confirmed", "message": "Still Here ✓ Escalation resolved."})


@router.post("/escalation/{escalation_id}/cancel")
def cancel_escalation_endpoint(escalation_id: str, user=Depends(get_current_user), db=Depends(get_session)):
    from db import cancel_escalation as _cancel
    uid = str(user["id"])
    result = _cancel(db, escalation_id, uid)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Escalation not found")
    if result == "forbidden":
        raise HTTPException(status_code=403, detail="Not your escalation")
    if result == "already_resolved":
        return {"status": "already_resolved", "message": "Already resolved"}
    from services.push_svc import send_push
    user_row = db.execute(
        text("SELECT name, device_token FROM users WHERE id::text = :uid"),
        {"uid": uid},
    ).mappings().first()
    u = dict(user_row) if user_row else {}
    if u.get("device_token"):
        send_push(u["device_token"], "Escalation Cancelled", "False alarm — you're all good.", settings.base_url)
    return {"status": "cancelled", "message": "Escalation cancelled"}
