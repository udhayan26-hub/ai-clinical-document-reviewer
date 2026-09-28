def test_create_analysis_from_text_returns_pending(client):
    response = client.post("/api/v1/analyses", data={"text": "Patient reports mild headache."})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["document"]["source_type"] == "TEXT"
    assert body["report_available"] is False


def test_create_analysis_with_no_input_is_rejected(client):
    response = client.post("/api/v1/analyses", data={})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_INPUT"


def test_create_analysis_with_both_text_and_file_is_rejected(client):
    response = client.post(
        "/api/v1/analyses",
        data={"text": "some text"},
        files={"file": ("note.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_create_analysis_with_unsupported_file_type_is_rejected(client):
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("note.exe", b"not a document", "application/x-msdownload")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_create_analysis_with_pdf_file_is_accepted(client):
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("note.pdf", b"%PDF-1.4 fake pdf bytes", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["document"]["source_type"] == "PDF"


def test_get_analysis_by_id(client):
    created = client.post("/api/v1/analyses", data={"text": "Patient is stable."}).json()

    response = client.get(f"/api/v1/analyses/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_analysis_returns_404(client):
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_list_analyses_returns_pagination_metadata(client):
    client.post("/api/v1/analyses", data={"text": "First note."})
    client.post("/api/v1/analyses", data={"text": "Second note."})

    response = client.get("/api/v1/analyses", params={"page": 1, "page_size": 20})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == 2
    assert len(body["items"]) == 2


def test_report_not_ready_before_completion(client):
    created = client.post("/api/v1/analyses", data={"text": "Patient note."}).json()

    response = client.get(f"/api/v1/analyses/{created['id']}/report")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REPORT_NOT_READY"
