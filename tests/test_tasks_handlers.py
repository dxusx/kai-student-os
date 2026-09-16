import asyncio
from database.connection import init_db, async_session
from database.models import Subject, Task
from database.crud import update_task_status
from bot.handlers.tasks import build_subjects_menu, build_subject_tasks_view, build_subject_done_tasks_view

async def test_tasks_handlers():
    await init_db()

    async with async_session() as session:
        subj = Subject(name="Тестовая Дисциплина", teacher="Иванов И.И.")
        session.add(subj)
        await session.flush()

        task1 = Task(subject_id=subj.id, title="Тест Лаба 1", task_type="лабораторная", status="todo", source="kai")
        task2 = Task(subject_id=subj.id, title="Тест Лаба 2", task_type="лабораторная", status="done", source="kai")
        session.add_all([task1, task2])
        await session.commit()
        s_id, t1_id, t2_id = subj.id, task1.id, task2.id

    text, kb = await build_subjects_menu()
    assert "Тестовая Дисциплина" in text or (kb and any("Тестовая Дисциплина" in b.text for row in kb.inline_keyboard for b in row))

    text_todo, kb_todo = await build_subject_tasks_view(s_id, page=1)
    assert "Тест Лаба 1" in text_todo
    assert any("Показать сданные работы" in b.text for row in kb_todo.inline_keyboard for b in row)

    text_done, kb_done = await build_subject_done_tasks_view(s_id, page=1)
    assert "Тест Лаба 2" in text_done
    assert any("Вернуть в долги" in b.text for row in kb_done.inline_keyboard for b in row)
    assert any("Назад к несданным" in b.text for row in kb_done.inline_keyboard for b in row)

    async with async_session() as session:
        await update_task_status(session, t1_id, status="done")
        await update_task_status(session, t2_id, status="todo")

    async with async_session() as session:
        t1 = await session.get(Task, t1_id)
        t2 = await session.get(Task, t2_id)
        s = await session.get(Subject, s_id)
        if t1:
            await session.delete(t1)
        if t2:
            await session.delete(t2)
        if s:
            await session.delete(s)
        await session.commit()

    print("Task handler UI view tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(test_tasks_handlers())
