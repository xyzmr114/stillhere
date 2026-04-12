from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _mock_session(user_return=None, insert_return=None, escalation_return=None, contacts_return=None, confirmations_return=None):
    mock = MagicMock()
    call_count = [0]
    results_map = []

    def side_effect(*args, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(results_map):
            return results_map[idx]
        r = MagicMock()
        r.mappings.return_value.first.return_value = user_return
        r.mappings.return_value.all.return_value = contacts_return or []
        r.first.return_value = insert_return or ("esc-id-1",)
        return r

    mock.execute.side_effect = side_effect

    def add_result(first_val=None, mappings_first=None, mappings_all=None):
        r = MagicMock()
        if first_val is not None:
            r.first.return_value = first_val
        if mappings_first is not None:
            r.mappings.return_value.first.return_value = mappings_first
        if mappings_all is not None:
            r.mappings.return_value.all.return_value = mappings_all
        results_map.append(r)
        return r

    mock._add = add_result
    return mock


def test_demo_checkin_step():
    from main import app
    mock_db = _mock_session()
    mock_db._add(mappings_first={"id": "demo-uid-1", "name": "Alice (Demo)"})

    with patch("routes.demo.SessionLocal", return_value=mock_db), \
         patch("routes.demo.log_checkin"), \
         patch("routes.demo.log_audit_event"):
        client = TestClient(app)
        resp = client.post("/api/demo/step/checkin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == "checkin"
        assert data["user"] == "Alice"


def test_demo_miss_checkin_step():
    from main import app
    mock_db = _mock_session()
    mock_db._add(mappings_first={"id": "demo-uid-1"})
    mock_db._add(first_val=("esc-id-1",))

    with patch("routes.demo.SessionLocal", return_value=mock_db):
        client = TestClient(app)
        resp = client.post("/api/demo/step/miss-checkin")
        assert resp.status_code == 200
        data = resp.json()
        assert data["step"] == "miss_checkin"
        assert "escalation_id" in data


def test_demo_state():
    from main import app
    mock_db = MagicMock()
    user_result = MagicMock()
    user_result.mappings.return_value.first.return_value = {"id": "demo-uid-1", "name": "Alice (Demo)"}
    checkin_result = MagicMock()
    checkin_result.first.return_value = None
    esc_result = MagicMock()
    esc_result.mappings.return_value.first.return_value = None
    mock_db.execute.side_effect = [user_result, checkin_result, esc_result]

    with patch("routes.demo.SessionLocal", return_value=mock_db):
        client = TestClient(app)
        resp = client.get("/api/demo/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["seeded"] is True
        assert data["active_escalation"] is False


def test_demo_full_walkthrough():
    from main import app
    client = TestClient(app)

    with patch("routes.demo.SessionLocal") as mock_sl, \
         patch("routes.demo.log_audit_event"), \
         patch("routes.demo.log_checkin"):
        def make_db(*args, **kwargs):
            m = MagicMock()
            r_user = MagicMock()
            r_user.mappings.return_value.first.return_value = {"id": "demo-uid-1"}
            r_esc = MagicMock()
            r_esc.mappings.return_value.first.return_value = {"id": "esc-1"}
            r_insert = MagicMock()
            r_insert.first.return_value = ("esc-1",)
            r_contacts = MagicMock()
            r_contacts.mappings.return_value.all.return_value = []
            r_contacts.mappings.return_value.first.return_value = {"id": "c1"}
            r_cc = MagicMock()
            r_cc.mappings.return_value.first.return_value = {"id": "cc-1", "contact_id": "c1"}
            r_ck = MagicMock()
            r_ck.first.return_value = None
            r_none = MagicMock()
            r_none.mappings.return_value.first.return_value = None

            m._results = [r_user, r_insert, r_esc, r_contacts, r_cc, r_ck, r_none]
            m._idx = [0]

            def next_result(*a, **kw):
                i = m._idx[0]
                m._idx[0] += 1
                if i < len(m._results):
                    return m._results[i]
                r = MagicMock()
                r.mappings.return_value.first.return_value = {"id": "x"}
                r.first.return_value = ("x",)
                r.mappings.return_value.all.return_value = []
                return r

            m.execute.side_effect = next_result
            return m

        mock_sl.side_effect = make_db

        resp = client.post("/api/demo/step/send-prompt")
        assert resp.status_code == 200
        assert resp.json()["step"] == "send_prompt"

        resp = client.post("/api/demo/step/miss-checkin")
        assert resp.status_code == 200
        assert resp.json()["step"] == "miss_checkin"

        resp = client.post("/api/demo/step/grace-expire")
        assert resp.status_code == 200
        assert resp.json()["step"] == "grace_expire"

        resp = client.post("/api/demo/step/contact-confirm")
        assert resp.status_code == 200
        assert resp.json()["step"] == "contact_confirm"

        resp = client.post("/api/demo/step/user-confirm")
        assert resp.status_code == 200
        assert resp.json()["step"] == "user_confirm"
