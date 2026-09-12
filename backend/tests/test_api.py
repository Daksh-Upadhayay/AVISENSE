from app.ml.cmapss import RAW_COLUMNS, SENSOR_INFO, load_test
from tests.conftest import ALICE, BOB, auth


def test_health_and_model_card_are_public(client):
    assert client.get("/api/health").json()["status"] == "ok"
    card = client.get("/api/model").json()
    assert set(card["metrics"]["per_dataset"]) == {"FD001", "FD002", "FD003", "FD004"}
    assert card["policy"]["horizon"] == 30


def test_engine_routes_require_a_valid_session(client):
    assert client.get("/api/engines").status_code == 401
    assert client.get("/api/engines", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_demo_fleet_replays_nasa_engines_with_ground_truth(client):
    r = client.post("/api/fleet/demo", json={"size": 4}, headers=auth())
    assert r.status_code == 201
    fleet = r.json()
    assert len(fleet) == 4
    assert {e["engine_id"][:5] for e in fleet} == {"FD001", "FD002", "FD003", "FD004"}
    assert all(e["health"]["status"] in {"healthy", "watch", "critical"} for e in fleet)

    engine = fleet[0]
    detail = client.get(f"/api/engines/{engine['id']}", headers=auth()).json()
    a = detail["analysis"]
    replay = engine["metadata"]["replay"]
    assert a["cycles_observed"] == replay["cursor"]
    assert a["rul_low"] <= a["rul"] <= a["rul_high"]
    last = a["trajectory"][-1]
    assert last["true_rul"] == replay["final_rul"] + replay["length"] - replay["cursor"]
    assert len(detail["assessments"]) == 1


def test_replay_advances_history_and_records_assessments(client, repo):
    engine = client.post("/api/fleet/demo", json={"size": 1}, headers=auth()).json()[0]
    start = engine["metadata"]["replay"]["cursor"]
    r = client.post(f"/api/engines/{engine['id']}/replay?steps=5", headers=auth())
    assert r.status_code == 200
    body = r.json()
    assert body["analysis"]["cycle"] == start + 5
    assert body["engine"]["metadata"]["replay"]["cursor"] == start + 5
    assert len(repo.telemetry[engine["id"]]) == start + 5
    assert len(body["assessments"]) == 2

    # Replaying past the end of the record stops at the last available cycle.
    length = engine["metadata"]["replay"]["length"]
    r = client.post(f"/api/engines/{engine['id']}/replay?steps=100", headers=auth())
    r = client.post(f"/api/engines/{engine['id']}/replay?steps=100", headers=auth())
    r = client.post(f"/api/engines/{engine['id']}/replay?steps=100", headers=auth())
    assert r.json()["analysis"]["cycle"] == length


def test_users_cannot_see_each_others_engines(client):
    engine = client.post("/api/engines", json={"engine_id": "ENG-1"}, headers=auth(ALICE)).json()
    assert client.get(f"/api/engines/{engine['id']}", headers=auth(BOB)).status_code == 404
    assert client.post(f"/api/engines/{engine['id']}/assess", headers=auth(BOB)).status_code == 404
    assert client.get("/api/engines", headers=auth(BOB)).json() == []


def test_duplicate_engine_names_are_rejected(client):
    client.post("/api/engines", json={"engine_id": "ENG-1"}, headers=auth())
    assert client.post("/api/engines", json={"engine_id": "ENG-1"}, headers=auth()).status_code == 409


def _nasa_text(dataset="FD001", units=(1, 2)):
    df = load_test(dataset)
    rows = df[df["unit"].isin(units)][list(RAW_COLUMNS)]
    return rows.to_csv(sep=" ", header=False, index=False).encode()


def test_upload_nasa_file_needs_unit_when_it_has_several(client):
    engine = client.post("/api/engines", json={"engine_id": "ENG-2"}, headers=auth()).json()
    url = f"/api/engines/{engine['id']}/upload"
    r = client.post(url, files={"file": ("test.txt", _nasa_text())}, headers=auth())
    assert r.status_code == 400
    assert "Choose which unit" in r.json()["detail"]

    r = client.post(url, files={"file": ("test.txt", _nasa_text())}, data={"unit": "2"}, headers=auth())
    assert r.status_code == 200, r.text
    n = int((load_test("FD001")["unit"] == 2).sum())
    assert r.json()["analysis"]["cycles_observed"] == n

    # Appending cycles that already exist is refused; replace works.
    r = client.post(url, files={"file": ("test.txt", _nasa_text())}, data={"unit": "2"}, headers=auth())
    assert r.status_code == 400
    r = client.post(url, files={"file": ("t.txt", _nasa_text())}, data={"unit": "1", "replace": "true"}, headers=auth())
    assert r.status_code == 200


def test_upload_csv_with_symbol_headers(client):
    df = load_test("FD003")
    one = df[df["unit"] == 3]
    renamed = one.rename(columns={k: v["symbol"] for k, v in SENSOR_INFO.items()})
    content = renamed.drop(columns=["unit", "rul"]).to_csv(index=False).encode()
    engine = client.post("/api/engines", json={"engine_id": "ENG-3"}, headers=auth()).json()
    r = client.post(f"/api/engines/{engine['id']}/upload", files={"file": ("e.csv", content)}, headers=auth())
    assert r.status_code == 200, r.text
    assert r.json()["engine"]["health"]["cycle"] == int(one["cycle"].max())


def test_upload_rejects_bad_files(client):
    engine = client.post("/api/engines", json={"engine_id": "ENG-4"}, headers=auth()).json()
    url = f"/api/engines/{engine['id']}/upload"
    bad = [
        b"",
        b"cycle,sensor_2\n1,642.1\n",
        b"1 2 3\n",
        b"cycle,setting_1,setting_2,setting_3," + ",".join(f"sensor_{i}" for i in range(1, 22)).encode() + b"\n1,a,b,c\n",
    ]
    for content in bad:
        r = client.post(url, files={"file": ("x.csv", content)}, headers=auth())
        assert r.status_code == 400, content


def test_json_readings_append(client):
    df = load_test("FD002")
    one = df[df["unit"] == 7].drop(columns=["unit", "rul"])
    engine = client.post("/api/engines", json={"engine_id": "ENG-5"}, headers=auth()).json()
    url = f"/api/engines/{engine['id']}/readings"
    first, rest = one.iloc[:40], one.iloc[40:]
    r = client.post(url, json={"readings": first.to_dict("records")}, headers=auth())
    assert r.status_code == 200, r.text
    r = client.post(url, json={"readings": rest.to_dict("records")}, headers=auth())
    assert r.json()["analysis"]["cycles_observed"] == len(one)


def test_replay_engines_do_not_accept_uploads(client):
    engine = client.post("/api/fleet/demo", json={"size": 1}, headers=auth()).json()[0]
    r = client.post(f"/api/engines/{engine['id']}/upload", files={"file": ("t.txt", _nasa_text(units=(1,)))}, headers=auth())
    assert r.status_code == 400


def test_assess_without_history_is_a_clear_error(client):
    engine = client.post("/api/engines", json={"engine_id": "ENG-6"}, headers=auth()).json()
    r = client.post(f"/api/engines/{engine['id']}/assess", headers=auth())
    assert r.status_code == 400
    detail = client.get(f"/api/engines/{engine['id']}", headers=auth()).json()
    assert detail["analysis"] is None


def test_invalid_engine_id_is_422_not_500(client):
    assert client.get("/api/engines/not-a-uuid", headers=auth()).status_code == 422
