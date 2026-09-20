"""
Comprehensive Service Worker and CacheStorage Security Test.
Validates:
1. Authenticate User A
2. Request protected API (/api/tasks, /api/schedule)
3. Inspect browser CacheStorage keys and cached requests
4. Assert protected API responses are strictly absent from CacheStorage
5. Logout User A
6. Authenticate User B
7. Go offline
8. Request protected API (/api/tasks)
9. Assert that User B receives NO data from User A
10. Verify IndexedDB user-keyed isolation between User A and User B
"""

import time
from playwright.sync_api import Page, expect
from tests.qa.test_env import BASE_URL, get_alice_token, get_bob_token

def test_sw_cache_storage_and_offline_isolation(page: Page):
    alice_token = get_alice_token()
    bob_token = get_bob_token()

    # Step 1: Authenticate User A (Alice)
    page.goto(BASE_URL)
    page.evaluate("(token) => localStorage.setItem('kai_app_auth_token', token)", alice_token)
    page.reload()
    page.wait_for_load_state("networkidle")

    # Step 2: Request protected API while online
    alice_tasks = page.evaluate("""async () => {
        const res = await apiFetch('/api/tasks');
        return await res.json();
    }""")
    assert isinstance(alice_tasks, list)
    assert len(alice_tasks) > 0, "Alice should have tasks"
    alice_task_titles = [t["title"] for t in alice_tasks]

    # Let any async cache operations settle
    page.wait_for_timeout(500)

    # Step 3: Inspect CacheStorage
    cached_requests = page.evaluate("""async () => {
        const keys = await window.caches.keys();
        const urls = [];
        for (const k of keys) {
            const cache = await window.caches.open(k);
            const reqs = await cache.keys();
            for (const r of reqs) {
                urls.push(r.url);
            }
        }
        return urls;
    }""")

    # Step 4: Assert protected API responses are absent from CacheStorage
    for url in cached_requests:
        assert "/api/" not in url, f"Security violation: API endpoint cached in CacheStorage: {url}"
        assert "/auth/" not in url, f"Security violation: Auth endpoint cached in CacheStorage: {url}"
        assert "/files/" not in url, f"Security violation: File endpoint cached in CacheStorage: {url}"

    # Step 5: Logout User A
    page.evaluate("() => clearAuthToken()")

    # Step 6: Authenticate User B (Bob)
    page.evaluate("(token) => setAuthToken(token)", bob_token)

    # Step 7: Simulate offline mode
    page.context.set_offline(True)

    # Step 8: Request same API (/api/tasks) while offline as User B
    # Since Bob has not loaded tasks online in this session, he must not get Alice's cached tasks
    bob_offline_tasks = page.evaluate("""async () => {
        try {
            await loadTasksData();
            return state.tasks;
        } catch (e) {
            return [];
        }
    }""")

    # Step 9: Assert no Alice data is visible to Bob
    for task in (bob_offline_tasks or []):
        assert task.get("title") not in alice_task_titles, (
            f"Cross-user data leak: Bob accessed Alice's task '{task.get('title')}' in offline mode"
        )

    # Step 10: Check IndexedDB user keying
    idb_keys = page.evaluate("""async () => {
        const db = await openIDB();
        if (!db) return [];
        return new Promise((resolve) => {
            const tx = db.transaction('user_data', 'readonly');
            const store = tx.objectStore('user_data');
            const req = store.getAllKeys();
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => resolve([]);
        });
    }""")

    # Verify keys are partitioned by user identifier
    for key in idb_keys:
        assert ":" in str(key), f"Key {key} is not properly partitioned by user"
        assert str(key).startswith("user_") or str(key).startswith("token_")

    # Restore online state
    page.context.set_offline(False)
    print("   [PASS] Service Worker CacheStorage & IndexedDB multi-user isolation verified.")
