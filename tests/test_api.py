import asyncio
from fastapi.testclient import TestClient
from api.app import app
from database.connection import init_db

def test_fastapi_endpoints():
    asyncio.run(init_db())
    client = TestClient(app)

    # 1. Test Static & Root
    resp_root = client.get("/")
    assert resp_root.status_code == 200
    assert "КАИ 5108" in resp_root.text

    # 2. Test Manifest
    resp_manifest = client.get("/manifest.json")
    assert resp_manifest.status_code == 200
    assert "КАИ Ассистент 5108" in resp_manifest.json()["name"]

    # 3. Test /api/stats
    resp_stats = client.get("/api/stats")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert "total_tasks" in stats
    assert "done_tasks" in stats
    assert "progress_percent" in stats
    print(f"Stats OK: {stats}")

    # 4. Test /api/subjects
    resp_subjs = client.get("/api/subjects")
    assert resp_subjs.status_code == 200
    subjs = resp_subjs.json()
    assert isinstance(subjs, list)
    assert len(subjs) > 0
    print(f"Subjects count: {len(subjs)}")

    # 5. Test /api/tasks
    resp_tasks = client.get("/api/tasks?status=all")
    assert resp_tasks.status_code == 200
    tasks = resp_tasks.json()
    assert isinstance(tasks, list)
    assert len(tasks) > 0
    first_task = tasks[0]
    print(f"Tasks count: {len(tasks)}, First task: {first_task['title']}")

    # 6. Test /api/tasks/{id}/toggle
    t_id = first_task["id"]
    orig_status = first_task["status"]
    resp_toggle = client.post(f"/api/tasks/{t_id}/toggle")
    assert resp_toggle.status_code == 200
    toggled = resp_toggle.json()
    assert toggled["status"] != orig_status

    # Toggle back to original status
    resp_toggle_back = client.post(f"/api/tasks/{t_id}/toggle")
    assert resp_toggle_back.status_code == 200
    assert resp_toggle_back.json()["status"] == orig_status
    print("Task toggle test OK!")

    # 7. Test /api/schedule
    resp_sched = client.get("/api/schedule?day=2&week=чет")
    assert resp_sched.status_code == 200
    sched = resp_sched.json()
    assert sched["day"] == 2
    assert "lessons" in sched
    print(f"Schedule OK: {len(sched['lessons'])} lessons for Tuesday (even)")

    # 8. Test /api/schedule/week
    resp_week = client.get("/api/schedule/week?week=чет")
    assert resp_week.status_code == 200
    week_data = resp_week.json()
    assert "days" in week_data
    assert "2" in week_data["days"]
    print("Schedule week OK!")

    print("ALL API ENDPOINT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_fastapi_endpoints()
