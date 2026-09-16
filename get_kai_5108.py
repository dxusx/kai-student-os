import json
import urllib3
import requests

# Отключаем предупреждения об SSL (сертификаты Минцифры)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# Актуальный адрес публичного расписания КАИ
SCHEDULE_URL = "https://kai.ru/web/studentu/raspisanie1"

PORTLET_IDS = [
    "pubSchedule_WAR_publicSchedule10",
    "pubStudentSchedule_WAR_publicStudentSchedule10",
]


def fetch_group_and_schedule(group_name="5108"):
    for portlet_id in PORTLET_IDS:
        print(f"Пробуем portlet_id: {portlet_id}...")
        params = {
            "p_p_id": portlet_id,
            "p_p_lifecycle": "2",
            "p_p_resource_id": "getGroupsURL",
            "query": group_name,
        }

        try:
            res = requests.get(
                SCHEDULE_URL,
                params=params,
                headers=HEADERS,
                verify=False,
                timeout=10,
            )
            print(f"Статус ответа: {res.status_code}")

            if res.status_code != 200:
                continue

            groups = res.json()
            print(f"Найдено совпадений: {len(groups)}")

            group_id = None
            for g in groups:
                if str(g.get("group", "")).strip() == group_name:
                    group_id = str(g.get("id"))
                    break

            if not group_id and groups:
                group_id = str(groups[0].get("id"))

            if group_id:
                print(
                    f"\n НАЙДЕН РЕАЛЬНЫЙ ID ГРУППЫ {group_name}: {group_id}"
                )

                # Запрашиваем саму сетку пар
                post_params = {
                    "p_p_id": portlet_id,
                    "p_p_lifecycle": "2",
                    "p_p_resource_id": "schedule",
                }
                sched_res = requests.post(
                    SCHEDULE_URL,
                    params=post_params,
                    data={"groupId": group_id},
                    headers=HEADERS,
                    verify=False,
                    timeout=15,
                )

                schedule_data = sched_res.json()
                with open(
                    "real_schedule_5108.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(schedule_data, f, ensure_ascii=False, indent=2)

                print(
                    " Настоящее расписание сохранено в real_schedule_5108.json!"
                )
                return True
        except Exception as e:
            print(f"Ошибка с portlet {portlet_id}: {e}")

    return False


if __name__ == "__main__":
    if not fetch_group_and_schedule("5108"):
        print(
            "\n Не удалось получить данные. Проверь доступность сайта kai.ru."
        )